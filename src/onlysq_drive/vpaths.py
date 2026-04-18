from __future__ import annotations

from pathlib import PureWindowsPath


def normalize_virtual_path(path: str | PureWindowsPath | None) -> str:
    if path is None:
        return "/"
    if isinstance(path, PureWindowsPath):
        raw = str(path)
    else:
        raw = str(path)
    raw = raw.replace("\\", "/").strip()
    if not raw or raw == ".":
        return "/"
    if len(raw) >= 2 and raw[1] == ":":
        raw = raw[2:]
    if not raw.startswith("/"):
        raw = "/" + raw
    while "//" in raw:
        raw = raw.replace("//", "/")
    if raw != "/" and raw.endswith("/"):
        raw = raw[:-1]
    parts = []
    for part in raw.split("/"):
        if part in {"", "."}:
            continue
        if part == "..":
            if parts:
                parts.pop()
            continue
        parts.append(part)
    return "/" + "/".join(parts) if parts else "/"


def parent_path(path: str) -> str:
    path = normalize_virtual_path(path)
    if path == "/":
        return "/"
    head = path.rsplit("/", 1)[0]
    return head if head else "/"


def basename(path: str) -> str:
    path = normalize_virtual_path(path)
    if path == "/":
        return ""
    return path.rsplit("/", 1)[-1]


def join_virtual_path(parent: str, child_name: str) -> str:
    parent = normalize_virtual_path(parent)
    child_name = child_name.replace("\\", "/").strip("/")
    if parent == "/":
        return normalize_virtual_path(f"/{child_name}")
    return normalize_virtual_path(f"{parent}/{child_name}")


def virtual_to_windows_path(path: str) -> str:
    path = normalize_virtual_path(path)
    return str(PureWindowsPath(path))
