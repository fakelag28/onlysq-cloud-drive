from __future__ import annotations

import json
import os
import platform
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

from .paths import config_path, ensure_base_dirs

IS_WINDOWS = platform.system() == "Windows"


def _default_mountpoint() -> str:
    if IS_WINDOWS:
        return "O:"

    user = os.environ.get("USER")
    if not user:
        try:
            user = os.getlogin()
        except OSError:
            user = Path.home().name
    media = f"/run/media/{user}"
    if os.path.isdir(media):
        return f"{media}/OnlySQCloud"
    return "~/OnlySQCloud"


@dataclass(slots=True)
class AppConfig:
    upload_url: str = "https://cloud.onlysq.ru/upload"
    download_url_template: str = "https://cloud.onlysq.ru/uploads/{file_id}"
    delete_url_template: str = "https://cloud.onlysq.ru/uploads/{file_id}"
    delete_auth_header: str = "Authorization"
    request_timeout: int = 120
    chunk_size: int = 1024 * 1024
    mountpoint: str = ""
    volume_label: str = "OnlySQ Cloud"
    debug: bool = False

    def __post_init__(self) -> None:
        if not self.mountpoint:
            self.mountpoint = _default_mountpoint()

    @classmethod
    def load(cls) -> "AppConfig":
        ensure_base_dirs()
        path = config_path()
        if not path.exists():
            cfg = cls()
            cfg.save()
            return cfg
        data = json.loads(path.read_text(encoding="utf-8"))
        return cls(**data)

    def save(self) -> None:
        ensure_base_dirs()
        config_path().write_text(
            json.dumps(asdict(self), ensure_ascii=False, indent=2),
            encoding="utf-8",
        )

    def set(self, key: str, value: Any) -> None:
        if not hasattr(self, key):
            raise KeyError(key)
        current = getattr(self, key)
        if isinstance(current, bool):
            value = str(value).strip().lower() in {"1", "true", "yes", "on"}
        elif isinstance(current, int) and not isinstance(current, bool):
            value = int(value)
        setattr(self, key, value)

    @property
    def mount_drive(self) -> str:
        mount = self.mountpoint.strip()
        if mount.endswith("\\"):
            mount = mount[:-1]
        if len(mount) == 1:
            mount = f"{mount}:"
        return mount.upper()

    @property
    def mount_path(self) -> Path:
        p = Path(self.mountpoint).expanduser()
        if not p.is_absolute():
            p = Path.cwd() / p
        return Path(os.path.normpath(str(p)))
