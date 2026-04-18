from __future__ import annotations

import os
from pathlib import Path

APP_NAME = "OnlySQDrive"


def roaming_dir() -> Path:
    base = os.environ.get("APPDATA")
    if base:
        return Path(base) / APP_NAME
    return Path.home() / "AppData" / "Roaming" / APP_NAME


def local_dir() -> Path:
    base = os.environ.get("LOCALAPPDATA")
    if base:
        return Path(base) / APP_NAME
    return Path.home() / "AppData" / "Local" / APP_NAME


def config_path() -> Path:
    return roaming_dir() / "config.json"


def db_path() -> Path:
    return roaming_dir() / "index.sqlite3"


def cache_dir() -> Path:
    return local_dir() / "cache"


def logs_dir() -> Path:
    return local_dir() / "logs"


def ensure_base_dirs() -> None:
    roaming_dir().mkdir(parents=True, exist_ok=True)
    local_dir().mkdir(parents=True, exist_ok=True)
    cache_dir().mkdir(parents=True, exist_ok=True)
    logs_dir().mkdir(parents=True, exist_ok=True)
