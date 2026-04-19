from __future__ import annotations

import platform

IS_WINDOWS = platform.system() == "Windows"

if IS_WINDOWS:
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

else:
    """File-manager context menu integration for Linux desktop environments."""

    import shutil
    import stat
    import sys
    from pathlib import Path

    NAUTILUS_SCRIPT_DIR = Path.home() / ".local" / "share" / "nautilus" / "scripts"
    CAJA_SCRIPT_DIR = Path.home() / ".config" / "caja" / "scripts"
    NEMO_ACTION_DIR = Path.home() / ".local" / "share" / "nemo" / "actions"
    KDE_SERVICE_MENU_DIR = Path.home() / ".local" / "share" / "kio" / "servicemenus"

    SCRIPT_NAME = "OnlySQ - Copy public link"
    NEMO_ACTION_FILE = "onlysq-copy-link.nemo_action"
    KDE_SERVICE_MENU_FILE = "onlysq-copy-link.desktop"


    def _find_executable() -> str:
        exe = shutil.which("onlysq-drive")
        if exe:
            return exe
        return str(Path(sys.argv[0]).resolve())


    def _nautilus_script_content(executable: str) -> str:
        return f"""#!/bin/bash
# OnlySQ Drive: copy public link for the selected file
while IFS= read -r file; do
    \"{executable}\" shell-copy-link \"$file\"
    break

done <<< \"$NAUTILUS_SCRIPT_SELECTED_FILE_PATHS\"
"""


    def _nemo_action_content(executable: str) -> str:
        return f"""[Nemo Action]
Name=OnlySQ: Copy public link
Comment=Copy OnlySQ Cloud public link to clipboard
Exec={executable} shell-copy-link %f
Icon-Name=edit-copy
Selection=s
Extensions=any;
"""


    def _kde_service_menu_content(executable: str) -> str:
        return f"""[Desktop Entry]
Type=Service
X-KDE-ServiceTypes=KonqPopupMenu/Plugin
MimeType=all/allfiles;
Actions=onlysq_copy_link

[Desktop Action onlysq_copy_link]
Name=OnlySQ: Copy public link
Icon=edit-copy
Exec={executable} shell-copy-link %f
"""


    def _install_script(directory: Path, name: str, content: str) -> None:
        directory.mkdir(parents=True, exist_ok=True)
        path = directory / name
        path.write_text(content, encoding="utf-8")
        path.chmod(path.stat().st_mode | stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH)


    def _remove_file(directory: Path, name: str) -> None:
        path = directory / name
        if path.exists():
            path.unlink()


    def install_copy_link_menu(executable: str | None = None) -> None:
        exe = executable or _find_executable()
        _install_script(NAUTILUS_SCRIPT_DIR, SCRIPT_NAME, _nautilus_script_content(exe))
        _install_script(CAJA_SCRIPT_DIR, SCRIPT_NAME, _nautilus_script_content(exe))
        NEMO_ACTION_DIR.mkdir(parents=True, exist_ok=True)
        (NEMO_ACTION_DIR / NEMO_ACTION_FILE).write_text(
            _nemo_action_content(exe), encoding="utf-8"
        )
        KDE_SERVICE_MENU_DIR.mkdir(parents=True, exist_ok=True)
        (KDE_SERVICE_MENU_DIR / KDE_SERVICE_MENU_FILE).write_text(
            _kde_service_menu_content(exe), encoding="utf-8"
        )


    def uninstall_copy_link_menu() -> None:
        _remove_file(NAUTILUS_SCRIPT_DIR, SCRIPT_NAME)
        _remove_file(CAJA_SCRIPT_DIR, SCRIPT_NAME)
        _remove_file(NEMO_ACTION_DIR, NEMO_ACTION_FILE)
        _remove_file(KDE_SERVICE_MENU_DIR, KDE_SERVICE_MENU_FILE)
