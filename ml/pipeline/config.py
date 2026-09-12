"""Filesystem locations and optional private S3 dataset materialization."""
import os
import logging
import zipfile
from pathlib import Path
from urllib.parse import unquote, urlparse

from dotenv import load_dotenv

REPO = Path(__file__).resolve().parents[1]  # the ml/ project directory inside the git repo
PROJECT_ROOT = REPO.parent
load_dotenv(PROJECT_ROOT / ".env")
logger = logging.getLogger("ml.pipeline.config")

CACHE_DIR = Path(os.environ.get("CACHE_DIR", Path.home() / ".cache" / "ntpc_hackathon"))


def _download_s3_dataset(uri: str) -> Path:
    """Materialize one private S3 ZIP via boto3's standard credential chain."""
    parsed = urlparse(uri)
    if parsed.scheme != "s3" or not parsed.netloc or not parsed.path.lstrip("/"):
        raise ValueError("S3_DATASET_URI 必須是完整的 s3://bucket/object.zip")
    key = unquote(parsed.path.lstrip("/"))
    if not key.lower().endswith(".zip"):
        raise ValueError("S3_DATASET_URI 必須指向 ZIP 物件")

    target = CACHE_DIR / "dataset.zip"
    partial = target.with_suffix(".zip.part")
    refresh = os.getenv("S3_DATASET_REFRESH", "").lower() in {"1", "true", "yes"}
    if target.exists() and not refresh:
        return target

    import boto3  # Lazy: local DATASET_ZIP users do not need AWS dependencies.

    CACHE_DIR.mkdir(parents=True, exist_ok=True)
    region = os.getenv("AWS_REGION") or os.getenv("AWS_DEFAULT_REGION")
    profile = os.getenv("AWS_PROFILE")
    session = boto3.Session(profile_name=profile, region_name=region) if profile else boto3.Session(region_name=region)
    s3 = session.client("s3")
    try:
        metadata = s3.head_object(Bucket=parsed.netloc, Key=key)
        total = int(metadata["ContentLength"])
        etag = metadata.get("ETag")
        if refresh:
            target.unlink(missing_ok=True)
            partial.unlink(missing_ok=True)
        downloaded = partial.stat().st_size if partial.exists() else 0
        if downloaded > total:
            partial.unlink()
            downloaded = 0

        if downloaded < total:
            request = {"Bucket": parsed.netloc, "Key": key}
            if downloaded:
                request["Range"] = f"bytes={downloaded}-"
            if etag:
                request["IfMatch"] = etag
            response = s3.get_object(**request)
            mode = "ab" if downloaded else "wb"
            next_report = downloaded + 64 * 1024 * 1024
            with open(partial, mode) as output:
                for chunk in response["Body"].iter_chunks(chunk_size=8 * 1024 * 1024):
                    if not chunk:
                        continue
                    output.write(chunk)
                    downloaded += len(chunk)
                    if downloaded >= next_report:
                        logger.info("S3 dataset 下載進度 %.1f%%", downloaded / total * 100)
                        next_report = downloaded + 64 * 1024 * 1024
            response["Body"].close()
        if partial.stat().st_size != total:
            raise IOError(f"下載不完整：{partial.stat().st_size}/{total} bytes")
        if not zipfile.is_zipfile(partial):
            raise ValueError(f"下載內容不是有效 ZIP：{uri}")
        partial.replace(target)
    except Exception:
        # Preserve partial bytes so the next run can resume with an S3 Range GET.
        raise
    return target


def _find_dataset() -> Path:
    """dataset.zip sits in the hackathon kit, somewhere above the code."""
    s3_uri = os.getenv("S3_DATASET_URI", "").strip()
    if s3_uri:
        return _download_s3_dataset(s3_uri)
    return next((d / "dataset.zip" for d in REPO.parents if (d / "dataset.zip").exists()), REPO.parent / "dataset.zip")


DATASET_ZIP = Path(os.environ.get("DATASET_ZIP") or _find_dataset())
RAW_DIR = CACHE_DIR / "raw"  # PDFs extracted from dataset.zip — large, never committed
OUT_DIR = Path(os.environ.get("OUT_DIR", REPO / "data" / "processed"))
