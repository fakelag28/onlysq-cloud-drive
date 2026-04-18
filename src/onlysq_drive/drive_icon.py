
from __future__ import annotations

import ctypes
import winreg
from pathlib import Path

from .config import AppConfig

SHCNE_ASSOCCHANGED = 0x08000000
SHCNF_IDLIST = 0x0000


def _refresh_shell() -> None:
    ctypes.windll.shell32.SHChangeNotify(SHCNE_ASSOCCHANGED, SHCNF_IDLIST, None, None)


def _drive_letter(config: AppConfig) -> str:
    return config.mount_drive[0].upper()


def _hklm_drive_root(letter: str) -> str:
    return fr"SOFTWARE\Microsoft\Windows\CurrentVersion\Explorer\DriveIcons\{letter}"


def install_drive_icon(icon_path: str, label: str | None = None, *, config: AppConfig | None = None) -> None:
    cfg = config or AppConfig.load()
    letter = _drive_letter(cfg)
    label = label or cfg.volume_label
    icon = str(Path(icon_path).expanduser().resolve())
    root = _hklm_drive_root(letter)
    with winreg.CreateKey(winreg.HKEY_LOCAL_MACHINE, root + r"\DefaultIcon") as key:
        winreg.SetValueEx(key, "", 0, winreg.REG_SZ, icon)
    with winreg.CreateKey(winreg.HKEY_LOCAL_MACHINE, root + r"\DefaultLabel") as key:
        winreg.SetValueEx(key, "", 0, winreg.REG_SZ, label)
    _refresh_shell()


def uninstall_drive_icon(*, config: AppConfig | None = None) -> None:
    cfg = config or AppConfig.load()
    letter = _drive_letter(cfg)
    base = _hklm_drive_root(letter)
    _delete_tree(winreg.HKEY_LOCAL_MACHINE, base)
    _refresh_shell()


def _delete_tree(root: int, subkey: str) -> None:
    try:
        with winreg.OpenKey(root, subkey, 0, winreg.KEY_READ | winreg.KEY_WRITE) as key:
            while True:
                try:
                    child = winreg.EnumKey(key, 0)
                except OSError:
                    break
                _delete_tree(root, subkey + "\\" + child)
    except FileNotFoundError:
        return
    winreg.DeleteKey(root, subkey)
