"""AWS Bedrock Connection & Claude Model Access Diagnostic Tool.

Usage:
    python -m infra.check_bedrock
"""
import json
import os
import sys
import time
from dotenv import load_dotenv
import boto3
from botocore.exceptions import ClientError, NoCredentialsError, PartialCredentialsError

load_dotenv()

from api.config import load_config


def run_diagnostics():
    print("=" * 60)
    print("🔍 AWS Bedrock 連線與 Claude 模型存取檢測工具")
    print("=" * 60)

    cfg = load_config()
    aws_cfg = cfg.get("aws", {})
    region = os.getenv("AWS_DEFAULT_REGION") or os.getenv("AWS_REGION") or aws_cfg.get("region", "us-west-2")
    profile = os.getenv("AWS_PROFILE") or aws_cfg.get("profile_name", "workshop")
    model_id = os.getenv("BEDROCK_MODEL_ID") or "us.anthropic.claude-haiku-4-5-20251001-v1:0"

    print(f"📌 目標區域 (Region):  {region}")
    print(f"📌 目標模型 (Model):   {model_id}")
    print(f"📌 優先設定檔 (Profile): {profile}")
    print("-" * 60)

    # 步驟 1: 建立 Session
    session = None
    try:
        session = boto3.Session(profile_name=profile, region_name=region)
        print(f"✅ 成功載入 AWS Profile: [{profile}]")
    except Exception:
        print(f"ℹ️ 未找到 Profile [{profile}]，使用預設環境變數/認證鏈...")
        session = boto3.Session(region_name=region)

    # 步驟 2: 驗證 STS 身份 (Caller Identity)
    print("\n[Step 1/3] 正在驗證 AWS 憑證 (STS GetCallerIdentity)...")
    try:
        sts = session.client("sts", region_name=region)
        identity = sts.get_caller_identity()
        print(f"  ✅ AWS 身分驗證成功！")
        print(f"     • 帳號 (Account): {identity.get('Account')}")
        print(f"     • 使用者/角色 (Arn): {identity.get('Arn')}")
    except (NoCredentialsError, PartialCredentialsError):
        print("  ❌ 失敗：找不到有效的 AWS 憑證。")
        print("     👉 請在專案根目錄建立 .env 並填入 AWS_ACCESS_KEY_ID / AWS_SECRET_ACCESS_KEY / AWS_SESSION_TOKEN")
        return False
    except ClientError as e:
        err_code = e.response["Error"]["Code"]
        err_msg = e.response["Error"]["Message"]
        print(f"  ❌ 失敗：AWS 憑證無效 [{err_code}]: {err_msg}")
        print("     👉 若為 Workshop Studio 短期憑證，可能已過期，請重新複製最新的 Session Token。")
        return False

    # 步驟 3: 初始化 Bedrock Runtime Client
    print("\n[Step 2/3] 正在初始化 Bedrock Runtime Client...")
    try:
        bedrock = session.client("bedrock-runtime", region_name=region)
        print("  ✅ Bedrock Runtime Client 初始化成功。")
    except Exception as e:
        print(f"  ❌ 初始化失敗: {e}")
        return False

    # 步驟 4: 測試呼叫 Claude 3 模型
    print(f"\n[Step 3/3] 正在發送測試請求至 Claude 模型 ({model_id})...")
    test_prompt = "請以繁體中文回覆這句話：「小小守護員已成功連線 AWS Bedrock！」"
    payload = {
        "anthropic_version": "bedrock-2023-05-31",
        "max_tokens": 100,
        "temperature": 0.1,
        "messages": [{"role": "user", "content": test_prompt}],
    }

    start_time = time.time()
    try:
        resp = bedrock.invoke_model(
            modelId=model_id,
            contentType="application/json",
            accept="application/json",
            body=json.dumps(payload),
        )
        latency = round(time.time() - start_time, 2)
        resp_body = json.loads(resp["body"].read().decode("utf-8"))
        reply = resp_body["content"][0]["text"].strip()
        print(f"  ✅ 模型推論成功！(耗時: {latency}s)")
        print(f"     💬 模型回覆: \"{reply}\"")
        print("\n" + "=" * 60)
        print("🎉 恭喜！AWS Bedrock 串接完全正常，輿情分析模組已可直接使用真實模型計算！")
        print("=" * 60)
        return True
    except ClientError as e:
        err_code = e.response["Error"]["Code"]
        err_msg = e.response["Error"]["Message"]
        print(f"  ❌ 調用模型失敗 [{err_code}]: {err_msg}")
        if "AccessDeniedException" in err_code or "ModelNotReadyException" in err_code:
            print("\n  👉 診斷建議：")
            print("     1. 請至 AWS Console -> Amazon Bedrock -> 左側選單「Model access」。")
            print("     2. 點擊「Modify model access」，勾選「Anthropic -> Claude 3 Haiku」並儲存啟用。")
            print(f"     3. 請確認區域已切換為 [{region}]。")
        return False
    except Exception as e:
        print(f"  ❌ 未知錯誤: {e}")
        return False


if __name__ == "__main__":
    success = run_diagnostics()
    sys.exit(0 if success else 1)
