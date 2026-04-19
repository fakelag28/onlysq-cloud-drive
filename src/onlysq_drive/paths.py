from __future__ import annotations

import os
import platform
from pathlib import Path

IS_WINDOWS = platform.system() == "Windows"
APP_NAME = "OnlySQDrive" if IS_WINDOWS else "onlysq-drive"


def roaming_dir() -> Path:
    """Windows config/data directory (%APPDATA%/OnlySQDrive).

    On non-Windows platforms this aliases to config_dir() for compatibility.
    """
    if IS_WINDOWS:
        base = os.environ.get("APPDATA")
        if base:
            return Path(base) / APP_NAME
        return Path.home() / "AppData" / "Roaming" / APP_NAME
    return config_dir()


def local_dir() -> Path:
    """Windows local data directory (%LOCALAPPDATA%/OnlySQDrive).

    On non-Windows platforms this aliases to data_dir() for compatibility.
    """
    if IS_WINDOWS:
        base = os.environ.get("LOCALAPPDATA")
        if base:
            return Path(base) / APP_NAME
        return Path.home() / "AppData" / "Local" / APP_NAME
    return data_dir()


def config_dir() -> Path:
    if IS_WINDOWS:
        return roaming_dir()
    base = os.environ.get("XDG_CONFIG_HOME")
    if base:
        return Path(base) / APP_NAME
    return Path.home() / ".config" / APP_NAME


def data_dir() -> Path:
    if IS_WINDOWS:
        return local_dir()
    base = os.environ.get("XDG_DATA_HOME")
    if base:
        return Path(base) / APP_NAME
    return Path.home() / ".local" / "share" / APP_NAME


def cache_root() -> Path:
    if IS_WINDOWS:
        return local_dir()
    base = os.environ.get("XDG_CACHE_HOME")
    if base:
        return Path(base) / APP_NAME
    return Path.home() / ".cache" / APP_NAME


def config_path() -> Path:
    return config_dir() / "config.json"


def db_path() -> Path:
    if IS_WINDOWS:
        return roaming_dir() / "index.sqlite3"
    return data_dir() / "index.sqlite3"


def cache_dir() -> Path:
    if IS_WINDOWS:
        return local_dir() / "cache"
    return cache_root() / "files"


def logs_dir() -> Path:
    if IS_WINDOWS:
        return local_dir() / "logs"
    return data_dir() / "logs"


def ensure_base_dirs() -> None:
    if IS_WINDOWS:
        roaming_dir().mkdir(parents=True, exist_ok=True)
        local_dir().mkdir(parents=True, exist_ok=True)
    else:
        config_dir().mkdir(parents=True, exist_ok=True)
        data_dir().mkdir(parents=True, exist_ok=True)
        cache_root().mkdir(parents=True, exist_ok=True)
    cache_dir().mkdir(parents=True, exist_ok=True)
    logs_dir().mkdir(parents=True, exist_ok=True)
