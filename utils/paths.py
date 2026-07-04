from __future__ import annotations

import os
from pathlib import Path
import sys


PROJECT_ROOT = Path(__file__).resolve().parents[1]
APP_NAME = "Music Lyriz"


def _data_root() -> Path:
    if getattr(sys, "frozen", False):
        local_app_data = os.environ.get("LOCALAPPDATA")
        if local_app_data:
            return Path(local_app_data) / APP_NAME
        return Path.home() / "AppData" / "Local" / APP_NAME
    return PROJECT_ROOT


DATA_ROOT = _data_root()
CONFIG_DIR = DATA_ROOT / "config"
CACHE_DIR = DATA_ROOT / "cache"
LOGS_DIR = DATA_ROOT / "logs"
DATABASE_DIR = DATA_ROOT / "database"
