"""Filesystem locations. Override any of them with the environment variable of the same name."""
import os
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]  # the ml/ project directory inside the git repo


def _find_dataset() -> Path:
    """dataset.zip sits in the hackathon kit, somewhere above the code."""
    return next((d / "dataset.zip" for d in REPO.parents if (d / "dataset.zip").exists()), REPO.parent / "dataset.zip")


DATASET_ZIP = Path(os.environ.get("DATASET_ZIP") or _find_dataset())
CACHE_DIR = Path(os.environ.get("CACHE_DIR", Path.home() / ".cache" / "ntpc_hackathon"))
RAW_DIR = CACHE_DIR / "raw"  # PDFs extracted from dataset.zip — large, never committed
OUT_DIR = Path(os.environ.get("OUT_DIR", REPO / "data" / "processed"))
