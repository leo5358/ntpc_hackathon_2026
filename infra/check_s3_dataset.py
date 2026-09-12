"""Quickly verify private S3 source access, optionally downloading the ZIP."""
import argparse
import logging
import os
import sys
import zipfile
from urllib.parse import unquote, urlparse

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")


def _human_size(size: int) -> str:
    value = float(size)
    for unit in ("B", "KiB", "MiB", "GiB", "TiB"):
        if value < 1024 or unit == "TiB":
            return f"{value:.2f} {unit}"
        value /= 1024
    return f"{value:.2f} TiB"


def main() -> None:
    parser = argparse.ArgumentParser(description="Verify the configured private S3 dataset")
    parser.add_argument("--download", action="store_true", help="download and validate the complete ZIP")
    args = parser.parse_args()
    try:
        from dotenv import load_dotenv
        import boto3

        load_dotenv(".env")
        uri = os.getenv("S3_DATASET_URI", "").strip()
        parsed = urlparse(uri)
        if parsed.scheme != "s3" or not parsed.netloc or not parsed.path.lstrip("/"):
            raise ValueError("S3_DATASET_URI 必須是完整的 s3://bucket/object.zip")
        key = unquote(parsed.path.lstrip("/"))
        profile = os.getenv("AWS_PROFILE")
        region = os.getenv("AWS_REGION") or os.getenv("AWS_DEFAULT_REGION")
        session = boto3.Session(profile_name=profile, region_name=region) if profile else boto3.Session(region_name=region)
        metadata = session.client("s3").head_object(Bucket=parsed.netloc, Key=key)
        print(
            "S3 private dataset 存取成功："
            f"{_human_size(metadata['ContentLength'])}、"
            f"{metadata.get('ContentType', 'unknown')}、"
            f"加密={metadata.get('ServerSideEncryption', 'none')}"
        )

        if args.download:
            # Import triggers the complete download and local ZIP validation.
            from ml.pipeline.config import DATASET_ZIP

            if not DATASET_ZIP.exists() or not zipfile.is_zipfile(DATASET_ZIP):
                raise ValueError("找不到有效的 dataset ZIP")
            with zipfile.ZipFile(DATASET_ZIP) as archive:
                file_count = sum(not info.is_dir() for info in archive.infolist())
            print(f"完整 ZIP 驗證成功：共 {file_count:,} 個檔案")
    except Exception as exc:
        print(f"S3 private dataset 驗證失敗：{exc}")
        sys.exit(1)


if __name__ == "__main__":
    main()
