from __future__ import annotations

import sys
import winreg
from pathlib import Path

REG_ROOT = r"Software\Classes\*\shell\OnlySQDrive.CopyLink"


def _command_value(executable: str) -> str:
    return f'"{executable}" shell-copy-link "%1"'


def install_copy_link_menu(executable: str | None = None) -> None:
    exe = executable or str(Path(sys.argv[0]).resolve())
    with winreg.CreateKey(winreg.HKEY_CURRENT_USER, REG_ROOT) as key:
        winreg.SetValueEx(key, "MUIVerb", 0, winreg.REG_SZ, "OnlySQ: Copy public link")
        winreg.SetValueEx(key, "Icon", 0, winreg.REG_SZ, exe)
    with winreg.CreateKey(winreg.HKEY_CURRENT_USER, REG_ROOT + r"\command") as key:
        winreg.SetValueEx(key, "", 0, winreg.REG_SZ, _command_value(exe))


def uninstall_copy_link_menu() -> None:
    _delete_tree(winreg.HKEY_CURRENT_USER, REG_ROOT)


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
