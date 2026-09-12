"""把前端靜態檔部署到 S3，並以 CloudFront 對外提供 HTTPS。

    python -m infra.deploy_web --stage dev
    python -m infra.deploy_web --stage dev --api-url https://xxx.lambda-url.us-west-2.on.aws/

流程皆為 create-or-update，重複執行安全：
    1. 建立／重用私有 S3 bucket（不開放公開存取）
    2. 建立／重用 CloudFront distribution，以 OAC 讀取 bucket
    3. 設定 SPA 路由（403/404 皆導回 index.html）
    4. 上傳 web/dist 並依檔型設定 Content-Type 與快取策略
    5. 建立 invalidation 讓改動立即生效
"""
import argparse
import json
import logging
import mimetypes
import os
import subprocess
import time
from pathlib import Path
from typing import Dict, Optional, Tuple

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
logger = logging.getLogger("infra.deploy_web")

REPO_ROOT = Path(__file__).resolve().parent.parent
WEB_DIR = REPO_ROOT / "web"
DIST_DIR = WEB_DIR / "dist"

# index.html 不快取，其餘帶 hash 的資源長快取
NO_CACHE = "no-cache, no-store, must-revalidate"
LONG_CACHE = "public, max-age=31536000, immutable"


# ---------------------------------------------------------
# 前端建置
# ---------------------------------------------------------
def build_frontend(api_url: Optional[str]) -> None:
    """執行 npm run build，並把 API 位址編譯進 bundle。

    Vite 只從 .env 檔載入 VITE_* 變數，單純 export 環境變數不會進入
    import.meta.env（實測 Vite 5.4 如此），因此改為建置前寫入
    .env.production.local（優先度最高），建置後立即移除。
    """
    env_file = WEB_DIR / ".env.production.local"
    if api_url:
        base = api_url.rstrip("/") + "/api"
        env_file.write_text(f"VITE_API_BASE_URL={base}\n", encoding="utf-8")
        logger.info("前端 API 位址：%s", base)
    else:
        logger.warning("未提供 --api-url，前端將以相對路徑 /api 呼叫（S3 上沒有 proxy，線上會失敗）")

    logger.info("建置前端 ...")
    try:
        result = subprocess.run(
            "npm run build", cwd=WEB_DIR, shell=True, capture_output=True, text=True
        )
        if result.returncode != 0:
            logger.error("前端建置失敗：\n%s", (result.stdout + result.stderr)[-3000:])
            raise RuntimeError("npm run build 失敗")
    finally:
        if env_file.exists():
            env_file.unlink()

    if api_url:
        bundles = list((DIST_DIR / "assets").glob("*.js"))
        baked = any(api_url.split("//")[-1].split("/")[0] in b.read_text(errors="ignore") for b in bundles)
        if not baked:
            raise RuntimeError("建置產物未包含 API 位址，請檢查 VITE_API_BASE_URL 注入是否生效")
        logger.info("已確認 API 位址編譯進 bundle")
    logger.info("前端建置完成")


# ---------------------------------------------------------
# S3
# ---------------------------------------------------------
def ensure_bucket(session, bucket: str, stage: str) -> None:
    s3 = session.client("s3")
    region = session.region_name
    try:
        s3.head_bucket(Bucket=bucket)
        logger.info("重用既有 bucket %s", bucket)
        return
    except ClientError as e:
        if client_error_code(e) not in {"404", "NoSuchBucket", "NotFound"}:
            raise

    logger.info("建立 bucket %s ...", bucket)
    kwargs = {"Bucket": bucket}
    if region != "us-east-1":
        kwargs["CreateBucketConfiguration"] = {"LocationConstraint": region}
    s3.create_bucket(**kwargs)
    s3.put_public_access_block(
        Bucket=bucket,
        PublicAccessBlockConfiguration={
            "BlockPublicAcls": True,
            "IgnorePublicAcls": True,
            "BlockPublicPolicy": True,
            "RestrictPublicBuckets": True,
        },
    )
    s3.put_bucket_tagging(
        Bucket=bucket,
        Tagging={"TagSet": [{"Key": k, "Value": str(v)} for k, v in tags(stage).items()]},
    )


def sync_dist(session, bucket: str) -> int:
    """上傳 dist/ 內容，回傳上傳檔數。"""
    if not DIST_DIR.exists():
        raise RuntimeError(f"找不到 {DIST_DIR}，請先執行前端建置")

    s3 = session.client("s3")
    count = 0
    for path in sorted(DIST_DIR.rglob("*")):
        if not path.is_file():
            continue
        key = path.relative_to(DIST_DIR).as_posix()
        content_type = mimetypes.guess_type(path.name)[0] or "application/octet-stream"
        cache = NO_CACHE if key in {"index.html"} else LONG_CACHE
        s3.upload_file(
            str(path), bucket, key,
            ExtraArgs={"ContentType": content_type, "CacheControl": cache},
        )
        count += 1
    logger.info("已上傳 %d 個檔案至 s3://%s", count, bucket)
    return count


def put_bucket_policy_for_cloudfront(session, bucket: str, distribution_arn: str) -> None:
    """只允許指定的 CloudFront distribution 讀取，bucket 本身維持私有。"""
    policy = {
        "Version": "2012-10-17",
        "Statement": [
            {
                "Sid": "AllowCloudFrontServicePrincipalRead",
                "Effect": "Allow",
                "Principal": {"Service": "cloudfront.amazonaws.com"},
                "Action": "s3:GetObject",
                "Resource": f"arn:aws:s3:::{bucket}/*",
                "Condition": {"StringEquals": {"AWS:SourceArn": distribution_arn}},
            }
        ],
    }
    session.client("s3").put_bucket_policy(Bucket=bucket, Policy=json.dumps(policy))
    logger.info("已設定 bucket policy（僅允許本 distribution 讀取）")


# ---------------------------------------------------------
# WAF（CloudFront 的 IP 白名單；scope CLOUDFRONT 一律建在 us-east-1）
# ---------------------------------------------------------
def ensure_waf(session, ip_set_name: str, acl_name: str, ips: list) -> Optional[str]:
    """建立／更新 IPSet 與 WebACL，回傳 WebACL ARN；白名單為空時回傳 None。"""
    if not ips:
        logger.info("未設定 IP 白名單，CloudFront 不掛 WAF")
        return None

    waf = session.client("wafv2", region_name="us-east-1")
    scope = "CLOUDFRONT"

    # IPSet
    existing = next(
        (s for s in waf.list_ip_sets(Scope=scope, Limit=100).get("IPSets", []) if s["Name"] == ip_set_name),
        None,
    )
    if existing:
        detail = waf.get_ip_set(Name=ip_set_name, Scope=scope, Id=existing["Id"])
        waf.update_ip_set(
            Name=ip_set_name,
            Scope=scope,
            Id=existing["Id"],
            Addresses=ips,
            LockToken=detail["LockToken"],
        )
        ip_set_arn = detail["IPSet"]["ARN"]
        logger.info("更新既有 IPSet %s（%d 個位址）", ip_set_name, len(ips))
    else:
        created = waf.create_ip_set(
            Name=ip_set_name,
            Scope=scope,
            IPAddressVersion="IPV4",
            Addresses=ips,
            Description="Smart Watchdog allowed client IPs",
        )
        ip_set_arn = created["Summary"]["ARN"]
        logger.info("建立 IPSet %s（%d 個位址）", ip_set_name, len(ips))

    rules = [
        {
            "Name": "AllowListedIPs",
            "Priority": 0,
            "Action": {"Allow": {}},
            "Statement": {"IPSetReferenceStatement": {"ARN": ip_set_arn}},
            "VisibilityConfig": {
                "SampledRequestsEnabled": True,
                "CloudWatchMetricsEnabled": True,
                "MetricName": "AllowListedIPs",
            },
        }
    ]
    visibility = {
        "SampledRequestsEnabled": True,
        "CloudWatchMetricsEnabled": True,
        "MetricName": acl_name.replace("-", ""),
    }

    acl = next(
        (a for a in waf.list_web_acls(Scope=scope, Limit=100).get("WebACLs", []) if a["Name"] == acl_name),
        None,
    )
    if acl:
        detail = waf.get_web_acl(Name=acl_name, Scope=scope, Id=acl["Id"])
        waf.update_web_acl(
            Name=acl_name,
            Scope=scope,
            Id=acl["Id"],
            DefaultAction={"Block": {}},
            Rules=rules,
            VisibilityConfig=visibility,
            LockToken=detail["LockToken"],
        )
        logger.info("更新既有 WebACL %s（預設 Block，僅放行白名單）", acl_name)
        return detail["WebACL"]["ARN"]

    # 剛建立的 IPSet 需要數秒才會被 CreateWebACL 看見（WAFUnavailableEntityException）
    for attempt in range(6):
        try:
            created = waf.create_web_acl(
                Name=acl_name,
                Scope=scope,
                DefaultAction={"Block": {}},
                Rules=rules,
                VisibilityConfig=visibility,
                Description="Smart Watchdog web IP allowlist",
            )
            logger.info("建立 WebACL %s（預設 Block，僅放行白名單）", acl_name)
            return created["Summary"]["ARN"]
        except ClientError as e:
            if client_error_code(e) == "WAFUnavailableEntityException" and attempt < 5:
                wait = 5 * (attempt + 1)
                logger.info("IPSet 尚未同步，%d 秒後重試建立 WebACL ...", wait)
                time.sleep(wait)
                continue
            raise
    raise RuntimeError("WebACL 建立失敗")


# ---------------------------------------------------------
# CloudFront
# ---------------------------------------------------------
def ensure_oac(session, name: str) -> str:
    """建立／重用 Origin Access Control，回傳其 Id。"""
    cf = session.client("cloudfront")
    paginator = cf.get_paginator("list_origin_access_controls") if cf.can_paginate("list_origin_access_controls") else None
    items = []
    if paginator:
        for page in paginator.paginate():
            items.extend(page.get("OriginAccessControlList", {}).get("Items", []))
    else:
        items = cf.list_origin_access_controls().get("OriginAccessControlList", {}).get("Items", [])

    for item in items:
        if item["Name"] == name:
            logger.info("重用既有 OAC %s", name)
            return item["Id"]

    logger.info("建立 OAC %s ...", name)
    return cf.create_origin_access_control(
        OriginAccessControlConfig={
            "Name": name,
            "Description": "Smart Watchdog web OAC",
            "SigningProtocol": "sigv4",
            "SigningBehavior": "always",
            "OriginAccessControlOriginType": "s3",
        }
    )["OriginAccessControl"]["Id"]


def _distribution_config(
    bucket: str, region: str, oac_id: str, comment: str, web_acl_arn: Optional[str] = None
) -> Dict:
    origin_domain = f"{bucket}.s3.{region}.amazonaws.com"
    config: Dict = {
        "CallerReference": f"{bucket}-{int(time.time())}",
        "Comment": comment,
        "Enabled": True,
        "DefaultRootObject": "index.html",
        "Origins": {
            "Quantity": 1,
            "Items": [
                {
                    "Id": "s3-origin",
                    "DomainName": origin_domain,
                    "OriginAccessControlId": oac_id,
                    "S3OriginConfig": {"OriginAccessIdentity": ""},
                }
            ],
        },
        "DefaultCacheBehavior": {
            "TargetOriginId": "s3-origin",
            "ViewerProtocolPolicy": "redirect-to-https",
            "AllowedMethods": {
                "Quantity": 2,
                "Items": ["GET", "HEAD"],
                "CachedMethods": {"Quantity": 2, "Items": ["GET", "HEAD"]},
            },
            "Compress": True,
            # CachingOptimized 受管快取政策
            "CachePolicyId": "658327ea-f89d-4fab-a63d-7e88639e58f6",
        },
        # SPA：react-router 的深層路徑在 S3 上不存在，一律回 index.html
        "CustomErrorResponses": {
            "Quantity": 2,
            "Items": [
                {
                    "ErrorCode": 403,
                    "ResponsePagePath": "/index.html",
                    "ResponseCode": "200",
                    "ErrorCachingMinTTL": 10,
                },
                {
                    "ErrorCode": 404,
                    "ResponsePagePath": "/index.html",
                    "ResponseCode": "200",
                    "ErrorCachingMinTTL": 10,
                },
            ],
        },
        "PriceClass": "PriceClass_100",
    }
    if web_acl_arn:
        config["WebACLId"] = web_acl_arn
    return config


def ensure_distribution(
    session, bucket: str, oac_id: str, comment: str, web_acl_arn: Optional[str] = None
) -> Tuple[str, str, str]:
    """建立／重用 distribution，回傳 (id, domain_name, arn)。

    既有 distribution 若尚未掛上（或掛錯）WebACL，會就地更新設定。
    """
    cf = session.client("cloudfront")
    for page in cf.get_paginator("list_distributions").paginate():
        for item in page.get("DistributionList", {}).get("Items", []) or []:
            if item.get("Comment") == comment:
                dist_id = item["Id"]
                logger.info("重用既有 CloudFront distribution %s", dist_id)
                if web_acl_arn and item.get("WebACLId") != web_acl_arn:
                    current = cf.get_distribution_config(Id=dist_id)
                    cfg = current["DistributionConfig"]
                    cfg["WebACLId"] = web_acl_arn
                    cf.update_distribution(
                        Id=dist_id, DistributionConfig=cfg, IfMatch=current["ETag"]
                    )
                    logger.info("已將 WebACL 掛到既有 distribution")
                return dist_id, item["DomainName"], item["ARN"]

    logger.info("建立 CloudFront distribution（首次建立需數分鐘生效）...")
    dist = cf.create_distribution(
        DistributionConfig=_distribution_config(
            bucket, session.region_name, oac_id, comment, web_acl_arn
        )
    )["Distribution"]
    return dist["Id"], dist["DomainName"], dist["ARN"]


def invalidate(session, distribution_id: str) -> None:
    session.client("cloudfront").create_invalidation(
        DistributionId=distribution_id,
        InvalidationBatch={
            "Paths": {"Quantity": 1, "Items": ["/*"]},
            "CallerReference": str(int(time.time())),
        },
    )
    logger.info("已建立 CloudFront invalidation（/*）")


# ---------------------------------------------------------
# 進入點
# ---------------------------------------------------------
def deploy_web(
    stage: str = "dev",
    api_url: Optional[str] = None,
    profile: Optional[str] = None,
    region: Optional[str] = None,
    skip_build: bool = False,
) -> str:
    session = get_session(region=region, profile=profile)
    ident = caller_identity(session)
    names = resource_names(stage, ident["Account"])
    bucket = names["web_bucket"]

    if not skip_build:
        build_frontend(api_url)

    ips = allowed_ips()
    ensure_bucket(session, bucket, stage)
    web_acl_arn = ensure_waf(session, names["ip_set"], names["web_acl"], ips)
    oac_id = ensure_oac(session, names["oac"])
    dist_id, domain, dist_arn = ensure_distribution(
        session, bucket, oac_id, names["distribution_comment"], web_acl_arn
    )
    put_bucket_policy_for_cloudfront(session, bucket, dist_arn)
    sync_dist(session, bucket)
    invalidate(session, dist_id)

    url = f"https://{domain}"
    logger.info("前端已部署：%s", url)
    logger.info("IP 白名單：%s", ", ".join(ips) if ips else "（未設限）")
    logger.info("（distribution 首次建立後需等待數分鐘完成佈署才會回應）")
    return url


def main():
    parser = argparse.ArgumentParser(description="Deploy frontend to S3 + CloudFront")
    parser.add_argument("--stage", default="dev")
    parser.add_argument("--api-url", default=os.getenv("API_URL"), help="Lambda Function URL")
    parser.add_argument("--profile", default=None)
    parser.add_argument("--region", default=None)
    parser.add_argument("--skip-build", action="store_true", help="沿用既有 web/dist，不重新建置")
    args = parser.parse_args()

    url = deploy_web(
        stage=args.stage,
        api_url=args.api_url,
        profile=args.profile,
        region=args.region,
        skip_build=args.skip_build,
    )

    gh_output = os.getenv("GITHUB_OUTPUT")
    if gh_output:
        with open(gh_output, "a", encoding="utf-8") as f:
            f.write(f"web_url={url}\n")

    print(f"WEB_URL={url}")


if __name__ == "__main__":
    main()
