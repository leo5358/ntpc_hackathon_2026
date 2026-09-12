"""把 FastAPI 應用部署為 AWS Lambda，並以 API Gateway REST API 對外提供服務。

    python -m infra.deploy_api --stage dev
    python -m infra.deploy_api --stage prod --output-url-file api_url.txt

流程皆為 create-or-update，重複執行安全：
    1. 建立／重用 Lambda 執行角色（含 Bedrock InvokeModel 權限）
    2. 以 manylinux wheel 打包 api/ + pipeline/ + 精簡相依為 zip
    3. 建立或更新 Lambda 函式
    4. 建立／更新 REST API（{proxy+} 代理整合）並部署到 stage

對外出口選用 REST API 而非 Lambda Function URL，原因有二：
    - 本專案使用的 AWS Workshop 帳號在服務層阻擋 Function URL，
      即使 resource policy 正確、AuthType 為 NONE 或 AWS_IAM 皆回 403
    - REST API 的 resource policy 原生支援 aws:SourceIp 白名單，
      正好滿足「只開放指定 IP」的需求（清單見 config.yaml 的 security.allowed_ips）
"""
import argparse
import json
import logging
import os
import shutil
import subprocess
import sys
import tempfile
import time
import zipfile
from pathlib import Path
from typing import Optional

from botocore.exceptions import ClientError

from infra.aws_common import (
    allowed_ips,
    caller_identity,
    client_error_code,
    get_session,
    is_not_found,
    resource_names,
    tags,
)

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("infra.deploy_api")

REPO_ROOT = Path(__file__).resolve().parent.parent

# Lambda runtime 與打包目標平台；與 requirements-lambda.txt 搭配
PYTHON_VERSION = "3.12"
LAMBDA_RUNTIME = f"python{PYTHON_VERSION}"
LAMBDA_HANDLER = "api.handler.handler"
LAMBDA_TIMEOUT = 60
LAMBDA_MEMORY = 1024

# 打包時要進 zip 的專案目錄與檔案
INCLUDE_PATHS = ["api", "pipeline", "config.yaml"]
EXCLUDE_PATTERNS = {"__pycache__", ".pytest_cache", ".DS_Store"}

TRUST_POLICY = {
    "Version": "2012-10-17",
    "Statement": [
        {
            "Effect": "Allow",
            "Principal": {"Service": "lambda.amazonaws.com"},
            "Action": "sts:AssumeRole",
        }
    ],
}

# 輿情分析需要呼叫 Bedrock；分數檔日後放 S3 時也需要讀取權限
INLINE_POLICY = {
    "Version": "2012-10-17",
    "Statement": [
        {
            "Effect": "Allow",
            "Action": ["bedrock:InvokeModel", "bedrock:InvokeModelWithResponseStream"],
            "Resource": "*",
        },
        {
            "Effect": "Allow",
            "Action": ["s3:GetObject", "s3:ListBucket"],
            "Resource": "*",
        },
    ],
}


def rest_api_policy(ip_allowlist: list) -> dict:
    """REST API resource policy：白名單以外的來源 IP 一律拒絕。

    白名單為空時只保留 Allow，等同不設限制。
    """
    statements = [
        {
            "Effect": "Allow",
            "Principal": "*",
            "Action": "execute-api:Invoke",
            "Resource": "execute-api:/*/*/*",
        }
    ]
    if ip_allowlist:
        statements.append(
            {
                "Effect": "Deny",
                "Principal": "*",
                "Action": "execute-api:Invoke",
                "Resource": "execute-api:/*/*/*",
                "Condition": {"NotIpAddress": {"aws:SourceIp": ip_allowlist}},
            }
        )
    return {"Version": "2012-10-17", "Statement": statements}


# ---------------------------------------------------------
# IAM
# ---------------------------------------------------------
def ensure_execution_role(session, role_name: str, stage: str) -> str:
    """建立或重用 Lambda 執行角色，回傳 ARN。"""
    iam = session.client("iam")
    try:
        role = iam.get_role(RoleName=role_name)["Role"]
        logger.info("重用既有執行角色 %s", role_name)
    except ClientError as e:
        if not is_not_found(e):
            raise
        logger.info("建立執行角色 %s ...", role_name)
        role = iam.create_role(
            RoleName=role_name,
            AssumeRolePolicyDocument=json.dumps(TRUST_POLICY),
            Description="Execution role for Smart Watchdog FastAPI Lambda",
            Tags=[{"Key": k, "Value": str(v)} for k, v in tags(stage).items()],
        )["Role"]
        # IAM 角色建立後需要數秒才能被 Lambda 服務信任
        time.sleep(10)

    iam.attach_role_policy(
        RoleName=role_name,
        PolicyArn="arn:aws:iam::aws:policy/service-role/AWSLambdaBasicExecutionRole",
    )
    iam.put_role_policy(
        RoleName=role_name,
        PolicyName=f"{role_name}-inline",
        PolicyDocument=json.dumps(INLINE_POLICY),
    )
    return role["Arn"]


# ---------------------------------------------------------
# 打包
# ---------------------------------------------------------
def build_package(work_dir: Path) -> Path:
    """安裝相依並打包成 zip，回傳 zip 路徑。

    以 --platform manylinux2014_x86_64 取得 Lambda 相容的 wheel，
    因此在 Windows/WSL/CI 上打包結果都一致。
    """
    pkg_dir = work_dir / "package"
    pkg_dir.mkdir(parents=True, exist_ok=True)

    req = REPO_ROOT / "requirements-lambda.txt"
    logger.info("安裝 Lambda 相依（%s，目標 %s）...", req.name, LAMBDA_RUNTIME)
    result = subprocess.run(
        [
            sys.executable, "-m", "pip", "install",
            "-r", str(req),
            "--target", str(pkg_dir),
            "--platform", "manylinux2014_x86_64",
            "--implementation", "cp",
            "--python-version", PYTHON_VERSION,
            "--only-binary=:all:",
            "--upgrade",
            "--quiet",
        ],
        capture_output=True,
        text=True,
    )
    if result.returncode != 0:
        logger.error("pip install 失敗：\n%s", result.stderr[-2000:])
        raise RuntimeError("Lambda 相依安裝失敗")

    for rel in INCLUDE_PATHS:
        src = REPO_ROOT / rel
        if not src.exists():
            logger.warning("略過不存在的路徑 %s", rel)
            continue
        dst = pkg_dir / rel
        if src.is_dir():
            shutil.copytree(
                src, dst,
                dirs_exist_ok=True,
                ignore=shutil.ignore_patterns(*EXCLUDE_PATTERNS),
            )
        else:
            shutil.copy2(src, dst)

    zip_path = work_dir / "lambda.zip"
    logger.info("壓縮部署包 ...")
    with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED, compresslevel=9) as zf:
        for path in sorted(pkg_dir.rglob("*")):
            if path.is_file() and not any(p in EXCLUDE_PATTERNS for p in path.parts):
                zf.write(path, path.relative_to(pkg_dir))

    size_mb = zip_path.stat().st_size / 1024 / 1024
    logger.info("部署包大小：%.1f MB（Lambda 直接上傳上限 50MB）", size_mb)
    if size_mb > 50:
        raise RuntimeError(f"部署包 {size_mb:.1f}MB 超過 Lambda 直接上傳上限，需改走 S3 或容器映像")
    return zip_path


# ---------------------------------------------------------
# Lambda
# ---------------------------------------------------------
def deploy_function(session, function_name: str, role_arn: str, zip_path: Path, stage: str) -> None:
    lam = session.client("lambda")
    payload = zip_path.read_bytes()
    env_vars = {
        "STAGE": stage,
        "BEDROCK_MODEL_ID": os.getenv(
            "BEDROCK_MODEL_ID", "us.anthropic.claude-haiku-4-5-20251001-v1:0"
        ),
    }
    # 部署包不含 ml/，評分檔於冷啟動時自 S3 取得（api/services/score_cache.py）
    if scores_bucket := os.getenv("SCORES_BUCKET"):
        env_vars["SCORES_BUCKET"] = scores_bucket
    if scores_prefix := os.getenv("SCORES_PREFIX"):
        env_vars["SCORES_PREFIX"] = scores_prefix

    try:
        lam.get_function(FunctionName=function_name)
        logger.info("更新既有函式 %s 的程式碼 ...", function_name)
        lam.update_function_code(FunctionName=function_name, ZipFile=payload, Publish=True)
        _wait_updated(lam, function_name)
        lam.update_function_configuration(
            FunctionName=function_name,
            Role=role_arn,
            Handler=LAMBDA_HANDLER,
            Runtime=LAMBDA_RUNTIME,
            Timeout=LAMBDA_TIMEOUT,
            MemorySize=LAMBDA_MEMORY,
            Environment={"Variables": env_vars},
        )
        _wait_updated(lam, function_name)
    except ClientError as e:
        if not is_not_found(e):
            raise
        logger.info("建立新函式 %s ...", function_name)
        _create_with_retry(lam, function_name, role_arn, payload, env_vars, stage)


def _create_with_retry(lam, function_name, role_arn, payload, env_vars, stage, attempts: int = 6):
    """新角色可能尚未在 Lambda 端生效，遇到就退避重試。"""
    for i in range(attempts):
        try:
            lam.create_function(
                FunctionName=function_name,
                Runtime=LAMBDA_RUNTIME,
                Role=role_arn,
                Handler=LAMBDA_HANDLER,
                Code={"ZipFile": payload},
                Timeout=LAMBDA_TIMEOUT,
                MemorySize=LAMBDA_MEMORY,
                Environment={"Variables": env_vars},
                Publish=True,
                Tags={k: str(v) for k, v in tags(stage).items()},
            )
            _wait_updated(lam, function_name)
            return
        except ClientError as e:
            if client_error_code(e) == "InvalidParameterValueException" and i < attempts - 1:
                logger.info("角色尚未生效，%d 秒後重試 ...", 5 * (i + 1))
                time.sleep(5 * (i + 1))
                continue
            raise


def _wait_updated(lam, function_name: str) -> None:
    lam.get_waiter("function_updated_v2").wait(FunctionName=function_name)


def remove_function_url(session, function_name: str) -> None:
    """清掉早期版本建立的 Function URL，避免留下無法使用的端點。"""
    lam = session.client("lambda")
    try:
        lam.delete_function_url_config(FunctionName=function_name)
        logger.info("已移除舊的 Function URL 設定")
    except ClientError as e:
        if not is_not_found(e):
            raise


# ---------------------------------------------------------
# API Gateway REST API
# ---------------------------------------------------------
def ensure_rest_api(session, api_name: str, function_name: str, stage: str, account_id: str) -> str:
    """建立／更新 REST API 代理整合並部署，回傳 invoke URL。"""
    apigw = session.client("apigateway")
    region = session.region_name
    policy = json.dumps(rest_api_policy(allowed_ips()))

    api_id = None
    for page in apigw.get_paginator("get_rest_apis").paginate():
        for item in page.get("items", []):
            if item["name"] == api_name:
                api_id = item["id"]
                break
        if api_id:
            break

    if api_id:
        logger.info("重用既有 REST API %s（%s）", api_name, api_id)
        apigw.update_rest_api(
            restApiId=api_id,
            patchOperations=[{"op": "replace", "path": "/policy", "value": policy}],
        )
    else:
        logger.info("建立 REST API %s ...", api_name)
        api_id = apigw.create_rest_api(
            name=api_name,
            description="Smart Watchdog FastAPI backend",
            endpointConfiguration={"types": ["REGIONAL"]},
            policy=policy,
            tags={k: str(v) for k, v in tags(stage).items()},
        )["id"]

    lambda_arn = session.client("lambda").get_function(FunctionName=function_name)["Configuration"][
        "FunctionArn"
    ]
    integration_uri = (
        f"arn:aws:apigateway:{region}:lambda:path/2015-03-31/functions/{lambda_arn}/invocations"
    )

    resources = {r["path"]: r for r in apigw.get_resources(restApiId=api_id)["items"]}
    root_id = resources["/"]["id"]

    proxy = resources.get("/{proxy+}")
    if proxy:
        proxy_id = proxy["id"]
    else:
        proxy_id = apigw.create_resource(restApiId=api_id, parentId=root_id, pathPart="{proxy+}")[
            "id"
        ]

    # 根路徑與 {proxy+} 都掛 ANY，讓 FastAPI 自行處理全部路由
    for resource_id in (root_id, proxy_id):
        _ensure_any_method(apigw, api_id, resource_id, integration_uri)

    # 允許 API Gateway 叫用 Lambda
    try:
        session.client("lambda").add_permission(
            FunctionName=function_name,
            StatementId=f"AllowApiGatewayInvoke-{stage}",
            Action="lambda:InvokeFunction",
            Principal="apigateway.amazonaws.com",
            SourceArn=f"arn:aws:execute-api:{region}:{account_id}:{api_id}/*/*/*",
        )
    except ClientError as e:
        if client_error_code(e) != "ResourceConflictException":
            raise

    # resource policy 與路由變更都需重新部署 stage 才生效
    apigw.create_deployment(restApiId=api_id, stageName=stage, description="infra.deploy_api")
    logger.info("已部署至 stage '%s'", stage)

    return f"https://{api_id}.execute-api.{region}.amazonaws.com/{stage}"


def _ensure_any_method(apigw, api_id: str, resource_id: str, integration_uri: str) -> None:
    try:
        apigw.get_method(restApiId=api_id, resourceId=resource_id, httpMethod="ANY")
    except ClientError as e:
        if not is_not_found(e):
            raise
        apigw.put_method(
            restApiId=api_id,
            resourceId=resource_id,
            httpMethod="ANY",
            authorizationType="NONE",
        )

    apigw.put_integration(
        restApiId=api_id,
        resourceId=resource_id,
        httpMethod="ANY",
        type="AWS_PROXY",
        integrationHttpMethod="POST",
        uri=integration_uri,
    )


# ---------------------------------------------------------
# 進入點
# ---------------------------------------------------------
def package_and_deploy_lambda(
    stage: str = "dev",
    profile: Optional[str] = None,
    region: Optional[str] = None,
    skip_build: bool = False,
) -> str:
    session = get_session(region=region, profile=profile)
    ident = caller_identity(session)
    names = resource_names(stage, ident["Account"])

    role_arn = ensure_execution_role(session, names["role"], stage)

    with tempfile.TemporaryDirectory(prefix="sw-lambda-") as tmp:
        zip_path = build_package(Path(tmp))
        if skip_build:
            logger.info("--skip-build 指定，僅輸出部署包路徑：%s", zip_path)
            return ""
        deploy_function(session, names["function"], role_arn, zip_path, stage)

    remove_function_url(session, names["function"])
    url = ensure_rest_api(session, names["rest_api"], names["function"], stage, ident["Account"])

    ips = allowed_ips()
    logger.info("後端已部署：%s", url)
    logger.info("IP 白名單：%s", ", ".join(ips) if ips else "（未設限）")
    return url


def main():
    parser = argparse.ArgumentParser(description="Deploy API to AWS Lambda Function URL")
    parser.add_argument("--stage", default="dev", help="Deployment stage (dev, staging, prod)")
    parser.add_argument("--profile", default=None, help="AWS CLI profile name")
    parser.add_argument("--region", default=None, help="AWS region")
    parser.add_argument("--output-url-file", default=None, help="把 Function URL 寫入指定檔案")
    parser.add_argument("--skip-build", action="store_true", help="只打包不部署（驗證打包流程用）")
    args = parser.parse_args()

    url = package_and_deploy_lambda(
        stage=args.stage, profile=args.profile, region=args.region, skip_build=args.skip_build
    )
    if args.output_url_file and url:
        Path(args.output_url_file).write_text(url, encoding="utf-8")

    # 供 GitHub Actions 以 $GITHUB_OUTPUT 取用
    gh_output = os.getenv("GITHUB_OUTPUT")
    if gh_output and url:
        with open(gh_output, "a", encoding="utf-8") as f:
            f.write(f"api_url={url}\n")

    print(f"API_URL={url}")


if __name__ == "__main__":
    main()
