"""Selective extraction from dataset.zip. The archive is stored, not deflated, so this is a plain copy."""
import shutil
import zipfile
from functools import lru_cache
from pathlib import Path

from .config import DATASET_ZIP, RAW_DIR


def _decode(info: zipfile.ZipInfo) -> str:
    if info.flag_bits & 0x800:  # UTF-8 flag set: zipfile has already decoded the name
        return info.filename
    try:
        return info.filename.encode("cp437").decode("utf-8")
    except (UnicodeEncodeError, UnicodeDecodeError):
        return info.filename


@lru_cache(maxsize=1)
def members() -> dict[str, zipfile.ZipInfo]:
    """Decoded archive path -> ZipInfo, files only."""
    with zipfile.ZipFile(DATASET_ZIP) as zf:
        return {_decode(i): i for i in zf.infolist() if not i.is_dir()}


def extract(member: str) -> Path:
    """Copy one member (decoded path, e.g. '資料集/公校/…/112年決算書第五冊.pdf') into RAW_DIR."""
    target = RAW_DIR / Path(member).name
    if not target.exists():
        RAW_DIR.mkdir(parents=True, exist_ok=True)
        partial = target.with_suffix(".part")
        with zipfile.ZipFile(DATASET_ZIP) as zf, zf.open(members()[member]) as src, open(partial, "wb") as dst:
            shutil.copyfileobj(src, dst)
        partial.rename(target)
    return target
