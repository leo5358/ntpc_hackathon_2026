"""Lambda 冷啟動時從私有 S3 取得模型評分檔。

部署包只含 api/、pipeline/ 與 config.yaml（見 infra/deploy_api.py 的 INCLUDE_PATHS），
不含 ml/，因此線上沒有 pipeline 產出的評分檔。若不補這一段，API 會退回少數手寫示範
機構，排行與全市報告在線上就沒有任何高風險機構。

評分檔由第三方資料衍生，只在團隊內部與私有 S3 流通（見 NOTICE.md），因此不放進
repo 也不打包進 Lambda，改為執行時下載。
"""
import logging
import os
from pathlib import Path
from typing import Optional

from api.config import load_config

logger = logging.getLogger("api.services.score_cache")

# 只有這幾個檔案會被下載；缺少 preschools.json 僅代表沒有座標與行政區，不影響評分
OBJECT_NAMES = ("risk_scores_latest.csv", "penalties_all.csv", "preschools.json")
REQUIRED = "risk_scores_latest.csv"

# Lambda 只有 /tmp 可寫
DEFAULT_CACHE_DIR = Path(os.getenv("SCORE_CACHE_DIR", "/tmp/ntpc_scores"))


def _s3_client(region: str, profile: Optional[str]):
    """建立 S3 client；具名 profile 失敗時退回預設憑證鏈（Lambda 走的是後者）。"""
    import boto3

    if profile:
        try:
            return boto3.Session(profile_name=profile, region_name=region).client("s3")
        except Exception as e:
            logger.debug("S3 profile '%s' unavailable: %s", profile, e)
    return boto3.Session(region_name=region).client("s3")


def hydrate(cache_dir: Path = DEFAULT_CACHE_DIR) -> Optional[Path]:
    """下載評分檔到本機目錄，成功回傳該目錄，否則 None（呼叫端維持現狀即可）。

    Bucket 取自環境變數 SCORES_BUCKET，其次 config.yaml 的 aws.bucket_name；
    前綴取自 SCORES_PREFIX，其次 config.yaml 的 aws.s3_prefixes.scores。
    """
    cfg = load_config()
    aws_cfg = cfg.get("aws", {})
    bucket = os.getenv("SCORES_BUCKET") or aws_cfg.get("bucket_name")
    if not bucket:
        logger.info("No scores bucket configured; serving whatever was loaded at import.")
        return None

    prefix = os.getenv("SCORES_PREFIX") or aws_cfg.get("s3_prefixes", {}).get("scores", "scores/")
    region = os.getenv("AWS_REGION") or os.getenv("AWS_DEFAULT_REGION") or aws_cfg.get("region", "us-west-2")
    profile = os.getenv("AWS_PROFILE") or aws_cfg.get("profile_name")

    try:
        client = _s3_client(region, profile)
    except Exception as e:
        logger.warning("Cannot create S3 client (%s); keeping local data.", e)
        return None

    cache_dir.mkdir(parents=True, exist_ok=True)
    fetched = []
    for name in OBJECT_NAMES:
        key = f"{prefix.rstrip('/')}/{name}"
        try:
            client.download_file(bucket, key, str(cache_dir / name))
            fetched.append(name)
        except Exception as e:
            level = logger.warning if name == REQUIRED else logger.info
            level("s3://%s/%s not fetched: %s", bucket, key, e)

    if REQUIRED not in fetched:
        return None
    logger.info("Fetched %s from s3://%s/%s", ", ".join(fetched), bucket, prefix)
    return cache_dir
