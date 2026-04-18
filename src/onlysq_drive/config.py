from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

from .paths import config_path, ensure_base_dirs


@dataclass(slots=True)
class AppConfig:
    upload_url: str = "https://cloud.onlysq.ru/upload"
    file_base_url: str = "https://cloud.onlysq.ru/file"
    delete_base_url: str = "https://cloud.onlysq.ru/file"
    delete_method: str = "DELETE"
    delete_auth_header: str = "Authorization"
    request_timeout: int = 120
    chunk_size: int = 1024 * 1024
    mountpoint: str = "O:"
    volume_label: str = "OnlySQ Cloud"
    debug: bool = False

    @classmethod
    def load(cls) -> "AppConfig":
        ensure_base_dirs()
        path = config_path()
        if not path.exists():
            cfg = cls()
            cfg.save()
            return cfg
        data = json.loads(path.read_text(encoding="utf-8"))
        known: dict[str, Any] = {}
        for field_name in cls.__dataclass_fields__.keys():
            if field_name in data:
                known[field_name] = data[field_name]
        cfg = cls(**known)
        return cfg

    def save(self) -> Path:
        ensure_base_dirs()
        path = config_path()
        path.write_text(json.dumps(asdict(self), indent=2, ensure_ascii=False), encoding="utf-8")
        return path

    def set(self, key: str, value: Any) -> None:
        if key not in self.__dataclass_fields__:
            raise KeyError(f"Unknown config key: {key}")
        current = getattr(self, key)
        if isinstance(current, bool):
            if isinstance(value, str):
                value = value.strip().lower() in {"1", "true", "yes", "on"}
            else:
                value = bool(value)
        elif isinstance(current, int):
            value = int(value)
        else:
            value = str(value)
        setattr(self, key, value)

    @property
    def mount_drive(self) -> str:
        mount = self.mountpoint.strip()
        if mount.endswith("\\"):
            mount = mount[:-1]
        if len(mount) == 1:
            mount = f"{mount}:"
        return mount.upper()
