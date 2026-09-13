"""Resolve the competition archive from a local path or a private S3 object."""
import hashlib
import os
import tempfile
import zipfile
from functools import lru_cache
from pathlib import Path
from urllib.parse import urlsplit

from .config import CACHE_DIR, DATASET_ZIP

DEFAULT_S3_URI = "s3://demo-20260912/E_教育局-資料集.zip"


@lru_cache(maxsize=1)
def dataset_path() -> Path:
    """Prefer explicit local configuration; download S3 once into a local cache.

    AWS_PROFILE is optional. Without it boto3 uses its default credential chain,
    including environment credentials and IAM roles. No credentials are stored.
    """
    if os.environ.get("DATASET_ZIP"):
        if not DATASET_ZIP.is_file():
            raise FileNotFoundError(f"DATASET_ZIP does not exist: {DATASET_ZIP}")
        return DATASET_ZIP
    uri = os.environ.get("DATASET_S3_URI")
    if not uri and DATASET_ZIP.is_file():
        return DATASET_ZIP
    uri = uri or DEFAULT_S3_URI
    parsed = urlsplit(uri)
    if parsed.scheme != "s3" or not parsed.netloc or not parsed.path.lstrip("/") or parsed.query or parsed.fragment:
        raise ValueError("DATASET_S3_URI must be s3://bucket/key (literal, not URL-encoded)")
    cache = CACHE_DIR / "datasets" / hashlib.sha256(uri.encode("utf-8")).hexdigest()[:16]
    cache.mkdir(parents=True, exist_ok=True)
    target = cache / "dataset.zip"
    if target.is_file() and zipfile.is_zipfile(target):
        return target

    import boto3

    session = boto3.Session(
        profile_name=os.environ.get("AWS_PROFILE") or None,
        region_name=os.environ.get("AWS_REGION") or os.environ.get("AWS_DEFAULT_REGION") or None,
    )
    client = session.client("s3")
    fd, temporary = tempfile.mkstemp(dir=cache, suffix=".part")
    os.close(fd)
    partial = Path(temporary)
    try:
        client.download_file(parsed.netloc, parsed.path.lstrip("/"), str(partial))
        if not zipfile.is_zipfile(partial):
            raise ValueError(f"S3 object is not a ZIP archive: {uri}")
        partial.replace(target)
    finally:
        partial.unlink(missing_ok=True)
    return target


if __name__ == "__main__":
    archive = dataset_path()
    with zipfile.ZipFile(archive) as zf:
        print(f"Dataset ready: {archive} ({len(zf.infolist())} entries)")
