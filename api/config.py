"""Configuration loader for backend API."""
from pathlib import Path
from typing import Any, Dict
import yaml

CONFIG_PATH = Path(__file__).resolve().parent.parent / "config.yaml"


def load_config() -> Dict[str, Any]:
    """Load config.yaml if available, else return defaults."""
    if CONFIG_PATH.exists():
        with open(CONFIG_PATH, "r", encoding="utf-8") as f:
            return yaml.safe_load(f) or {}
    return {
        "aws": {"region": "us-west-2", "profile_name": "workshop"},
        "model": {
            "weights": {
                "penalty": 0.45,
                "residual": 0.20,
                "isolation_forest": 0.15,
                "opinion": 0.10,
                "flags": 0.10,
            },
            "peer_groups": ["市立幼兒園", "非營利園"],
        },
        "api": {
            "cors_origins": ["*"],
        },
    }
