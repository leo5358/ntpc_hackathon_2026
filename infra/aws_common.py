"""部署腳本共用的 AWS session、命名規則與小工具。

本機執行時從 .env 讀憑證；在 GitHub Actions 中則由 workflow 注入環境變數，
兩種情境走同一條 boto3 預設憑證鏈，不需要分支處理。
"""
import logging
import os
from typing import Any, Dict, Optional

import boto3
from botocore.exceptions import ClientError
from dotenv import load_dotenv

from api.config import load_config

logger = logging.getLogger("infra")

# 本機執行時載入 repo 根目錄的 .env；CI 上沒有這個檔，靜默略過
load_dotenv(os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), ".env"))

PROJECT = "smart-watchdog"


def resource_names(stage: str, account_id: str) -> Dict[str, str]:
    """各項 AWS 資源的命名規則；bucket 名稱加上 account id 以維持全域唯一。"""
    return {
        "function": f"{PROJECT}-api-{stage}",
        "role": f"{PROJECT}-api-role-{stage}",
        "rest_api": f"{PROJECT}-api-{stage}",
        "web_bucket": f"{PROJECT}-web-{stage}-{account_id}",
        "oac": f"{PROJECT}-oac-{stage}",
        "distribution_comment": f"{PROJECT} web {stage}",
        "ip_set": f"{PROJECT}-allowed-ips-{stage}",
        "web_acl": f"{PROJECT}-web-acl-{stage}",
    }


def allowed_ips() -> list:
    """config.yaml 的對外連線 IP 白名單（CIDR 字串清單）；未設定時回傳空清單。"""
    ips = load_config().get("security", {}).get("allowed_ips") or []
    normalized = []
    for ip in ips:
        ip = str(ip).strip()
        if ip:
            normalized.append(ip if "/" in ip else f"{ip}/32")
    return normalized


def get_session(region: Optional[str] = None, profile: Optional[str] = None) -> boto3.Session:
    """建立 boto3 session：明確參數 > 環境變數 > config.yaml。"""
    cfg = load_config().get("aws", {})
    target_region = (
        region
        or os.getenv("AWS_DEFAULT_REGION")
        or os.getenv("AWS_REGION")
        or cfg.get("region", "us-west-2")
    )
    target_profile = profile or os.getenv("AWS_PROFILE")

    if target_profile:
        try:
            return boto3.Session(profile_name=target_profile, region_name=target_region)
        except Exception as e:
            logger.debug("Profile '%s' 不可用（%s），改用預設憑證鏈", target_profile, e)
    return boto3.Session(region_name=target_region)


def caller_identity(session: boto3.Session) -> Dict[str, str]:
    ident = session.client("sts").get_caller_identity()
    logger.info("AWS 身分：%s（帳號 %s，區域 %s）", ident["Arn"], ident["Account"], session.region_name)
    return ident


def client_error_code(e: ClientError) -> str:
    return e.response.get("Error", {}).get("Code", "")


def is_not_found(e: ClientError) -> bool:
    return client_error_code(e) in {
        "ResourceNotFoundException",
        "NotFoundException",  # API Gateway
        "NoSuchEntity",
        "NoSuchBucket",
        "404",
        "NotFound",
        "NoSuchDistribution",
        "WAFNonexistentItemException",
    }


def tags(stage: str) -> Dict[str, Any]:
    return {"Project": PROJECT, "Stage": stage, "ManagedBy": "infra-scripts"}
