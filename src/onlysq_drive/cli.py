from __future__ import annotations

import argparse
import json
import os
import shutil
import subprocess
import sys
from pathlib import Path

from .autostart import DEFAULT_TASK_NAME, autostart_log_path, install_autostart_task, uninstall_autostart_task
from .clipboard import copy_text
from .cloud_client import CloudClient
from .config import AppConfig
from .drive_icon import install_drive_icon, uninstall_drive_icon
from .index_db import IndexDB
from .mount import run_mount
from .paths import cache_dir, config_path, db_path, ensure_base_dirs, local_dir, roaming_dir
from .shell_integration import install_copy_link_menu, uninstall_copy_link_menu
from .vpaths import normalize_virtual_path


def positive_int(value: str) -> int:
    parsed = int(value)
    if parsed < 1:
        raise argparse.ArgumentTypeError("must be >= 1")
    return parsed




def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(prog="onlysq-drive")
    sub = parser.add_subparsers(dest="command", required=True)

    init_p = sub.add_parser("init", help="Create config and local data directories")
    init_p.add_argument("--mount", default=None, help="Drive letter, for example O:")
    init_p.add_argument("--label", default=None, help="Explorer volume label")

    sub.add_parser("doctor", help="Check local prerequisites")
    sub.add_parser("mount", help="Mount the configured virtual drive")
    sub.add_parser("stats", help="Show local index statistics")

    ls_p = sub.add_parser("ls", help="List indexed files")
    ls_p.add_argument("path", nargs="?", default="/", help="Virtual path or mounted path")

    info_p = sub.add_parser("info", help="Show details for one file or folder")
    info_p.add_argument("path", help="Virtual path or mounted path")

    copy_p = sub.add_parser("copy-link", help="Copy the public URL of a file to clipboard")
    copy_p.add_argument("path", help="Virtual path or mounted path")

    shell_copy = sub.add_parser("shell-copy-link", help=argparse.SUPPRESS)
    shell_copy.add_argument("path")

    pull_p = sub.add_parser("pull", help="Download one indexed file to a local destination")
    pull_p.add_argument("path", help="Virtual path or mounted path")
    pull_p.add_argument("destination", help="Local destination file")

    rm_p = sub.add_parser("rm", help="Delete one indexed file or empty directory")
    rm_p.add_argument("path", help="Virtual path or mounted path")

    cfg_p = sub.add_parser("config", help="Show or change configuration")
    cfg_sub = cfg_p.add_subparsers(dest="config_command", required=True)
    cfg_sub.add_parser("show", help="Print current config as JSON")
    cfg_set = cfg_sub.add_parser("set", help="Set one config key")
    cfg_set.add_argument("key")
    cfg_set.add_argument("value")

    ctx_install = sub.add_parser("install-context-menu", help="Add Explorer context menu entry")
    ctx_install.add_argument("--exe", default=None, help="Path to onlysq-drive.exe if auto-detect is wrong")
    sub.add_parser("uninstall-context-menu", help="Remove Explorer context menu entry")

    purge = sub.add_parser("purge", help="Delete local config/index/cache")
    purge.add_argument("--yes", action="store_true", help="Do not ask for confirmation")

    autostart_install = sub.add_parser("install-autostart", help="Create a hidden autostart task at user logon")
    autostart_install.add_argument("--task-name", default=DEFAULT_TASK_NAME, help="Scheduled task name")

    autostart_uninstall = sub.add_parser("uninstall-autostart", help="Remove the autostart task")
    autostart_uninstall.add_argument("--task-name", default=DEFAULT_TASK_NAME, help="Scheduled task name")

    icon_install = sub.add_parser("install-drive-icon", help="Assign a custom Explorer icon to the mounted drive")
    icon_install.add_argument("icon_path", help="Path to .ico file or icon resource")
    icon_install.add_argument("--label", default=None, help="Optional custom drive label in Explorer")

    sub.add_parser("uninstall-drive-icon", help="Remove the custom Explorer drive icon")

    setup = sub.add_parser("setup", help="One-time setup: init, context menu, optional icon, autostart")
    setup.add_argument("--mount", default=None, help="Drive letter, for example O:")
    setup.add_argument("--label", default=None, help="Explorer volume label")
    setup.add_argument("--icon", dest="icon_path", default=None, help="Path to .ico file for the drive")
    setup.add_argument("--task-name", default=DEFAULT_TASK_NAME, help="Scheduled task name")

    bootstrap = sub.add_parser("bootstrap", help="Try to install WinFsp with winget or chocolatey")
    bootstrap.add_argument("--non-interactive", action="store_true")

    return parser.parse_args(argv)

def _load_config() -> AppConfig:
    ensure_base_dirs()
    return AppConfig.load()


def _resolve_virtual_path(raw_path: str, config: AppConfig) -> str:
    path = str(raw_path).strip().strip('"')
    if len(path) >= 2 and path[1] == ":":
        drive = path[:2].upper()
        if drive != config.mount_drive:
            raise SystemExit(f"Path {path!r} is not on mounted drive {config.mount_drive}")
        return normalize_virtual_path(path[2:])
    return normalize_virtual_path(path)


def cmd_init(args: argparse.Namespace) -> int:
    cfg = _load_config()
    changed = False
    if args.mount:
        cfg.mountpoint = args.mount
        changed = True
    if args.label:
        cfg.volume_label = args.label
        changed = True
    if changed:
        cfg.save()
    IndexDB().close()
    print(f"Config: {config_path()}")
    print(f"Index DB: {db_path()}")
    print(f"Cache dir: {cache_dir()}")
    return 0


def cmd_doctor(args: argparse.Namespace) -> int:
    cfg = _load_config()
    pyver = sys.version.split()[0]
    print(f"Python: {pyver}")
    print(f"Platform: {sys.platform}")
    if sys.version_info >= (3, 13):
        print("Note: use Python 3.10-3.12 for now; winfspy wheels are not reliably available for 3.13.")
    print(f"Config: {config_path()}")
    print(f"Mount drive: {cfg.mount_drive}")
    winfsp_ok = False
    try:
        import winfspy
        winfsp_ok = True
    except Exception as exc:
        print(f"winfspy import: FAIL ({exc})")
    else:
        print("winfspy import: OK")
    probable_dir = Path(os.environ.get("ProgramFiles", r"C:\Program Files")) / "WinFsp"
    print(f"WinFsp dir exists: {'YES' if probable_dir.exists() else 'NO'} ({probable_dir})")
    if not winfsp_ok:
        print("Hint: run `onlysq-drive bootstrap` or install WinFsp manually first.")
    return 0


def cmd_mount(args: argparse.Namespace) -> int:
    cfg = _load_config()
    return run_mount(cfg)


def cmd_stats(args: argparse.Namespace) -> int:
    db = IndexDB()
    try:
        entries = list(db.iter_entries())
        files = [e for e in entries if e.kind == "file"]
        dirs = [e for e in entries if e.kind == "dir"]
        dirty = [e for e in files if e.dirty]
        print(f"Files: {len(files)}")
        print(f"Directories: {max(0, len(dirs) - 1)}")
        print(f"Total size: {db.total_file_size()} bytes")
        print(f"Dirty files: {len(dirty)}")
    finally:
        db.close()
    return 0


def cmd_ls(args: argparse.Namespace) -> int:
    cfg = _load_config()
    db = IndexDB()
    try:
        target = _resolve_virtual_path(args.path, cfg)
        for item in db.list_children(target):
            marker = "d" if item.kind == "dir" else "f"
            print(f"{marker}\t{item.size}\t{item.path}")
    finally:
        db.close()
    return 0


def cmd_info(args: argparse.Namespace) -> int:
    cfg = _load_config()
    db = IndexDB()
    try:
        target = _resolve_virtual_path(args.path, cfg)
        item = db.get_entry(target)
        if not item:
            raise SystemExit(f"Not found in local index: {target}")
        from dataclasses import asdict
        print(json.dumps(asdict(item), indent=2, ensure_ascii=False))
    finally:
        db.close()
    return 0


def cmd_copy_link(args: argparse.Namespace) -> int:
    cfg = _load_config()
    db = IndexDB()
    try:
        target = _resolve_virtual_path(args.path, cfg)
        item = db.get_entry(target)
        if not item:
            raise SystemExit(f"Not found in local index: {target}")
        if item.kind != "file":
            raise SystemExit("Only files have public links")
        if not item.public_url:
            raise SystemExit("File has no public URL yet. Save/sync it first.")
        copy_text(item.public_url)
        print(item.public_url)
    finally:
        db.close()
    return 0


def cmd_pull(args: argparse.Namespace) -> int:
    cfg = _load_config()
    db = IndexDB()
    try:
        target = _resolve_virtual_path(args.path, cfg)
        item = db.get_entry(target)
        if not item:
            raise SystemExit(f"Not found in local index: {target}")
        if item.kind != "file":
            raise SystemExit("Only files can be pulled")
        destination = Path(args.destination)
        destination.parent.mkdir(parents=True, exist_ok=True)
        cache_path = db.get_cache_abs_path(item.cache_relpath) if item.cache_relpath else None
        if cache_path and cache_path.exists():
            shutil.copy2(cache_path, destination)
        elif item.remote_id:
            CloudClient(cfg).download(item.remote_id, destination)
        else:
            raise SystemExit("File exists in index but has neither cache nor remote id")
        print(f"Saved to {destination}")
    finally:
        db.close()
    return 0


def cmd_rm(args: argparse.Namespace) -> int:
    cfg = _load_config()
    db = IndexDB()
    try:
        target = _resolve_virtual_path(args.path, cfg)
        item = db.get_entry(target)
        if not item:
            raise SystemExit(f"Not found in local index: {target}")
        if item.kind == "dir":
            children = db.list_children(target)
            if children:
                raise SystemExit("Directory is not empty")
            db.delete_path(target)
            print(f"Deleted directory {target}")
            return 0
        if item.remote_id and item.owner_key:
            CloudClient(cfg).delete(item.remote_id, item.owner_key)
        if item.cache_relpath:
            db.get_cache_abs_path(item.cache_relpath).unlink(missing_ok=True)
        db.delete_path(target)
        print(f"Deleted file {target}")
        return 0
    finally:
        db.close()


def cmd_config(args: argparse.Namespace) -> int:
    cfg = _load_config()
    if args.config_command == "show":
        from dataclasses import asdict
        print(json.dumps(asdict(cfg), indent=2, ensure_ascii=False))
        return 0
    if args.config_command == "set":
        cfg.set(args.key, args.value)
        cfg.save()
        print(f"Updated {args.key}")
        return 0
    raise SystemExit("Unknown config command")


def cmd_install_context_menu(args: argparse.Namespace) -> int:
    install_copy_link_menu(args.exe)
    print("Installed Explorer context menu entry.")
    return 0


def cmd_uninstall_context_menu(args: argparse.Namespace) -> int:
    uninstall_copy_link_menu()
    try:
        uninstall_autostart_task(DEFAULT_TASK_NAME)
    except Exception:
        pass
    try:
        uninstall_drive_icon(config=_load_config())
    except Exception:
        pass
    print("Removed Explorer context menu entry.")
    return 0


def cmd_purge(args: argparse.Namespace) -> int:
    if not args.yes:
        raise SystemExit("Refusing to purge without --yes")
    uninstall_copy_link_menu()
    try:
        uninstall_autostart_task(DEFAULT_TASK_NAME)
    except Exception:
        pass
    try:
        uninstall_drive_icon(config=_load_config())
    except Exception:
        pass
    if roaming_dir().exists():
        shutil.rmtree(roaming_dir(), ignore_errors=True)
    if local_dir().exists():
        shutil.rmtree(local_dir(), ignore_errors=True)
    print("Removed local config/index/cache.")
    return 0




def cmd_install_autostart(args: argparse.Namespace) -> int:
    install_autostart_task(args.task_name)
    print(f"Installed autostart task: {args.task_name}")
    print(f"Autostart log: {autostart_log_path()}")
    return 0


def cmd_uninstall_autostart(args: argparse.Namespace) -> int:
    uninstall_autostart_task(args.task_name)
    print(f"Removed autostart task: {args.task_name}")
    return 0


def cmd_install_drive_icon(args: argparse.Namespace) -> int:
    cfg = _load_config()
    install_drive_icon(args.icon_path, args.label, config=cfg)
    print(f"Installed custom drive icon for {cfg.mount_drive}")
    return 0


def cmd_uninstall_drive_icon(args: argparse.Namespace) -> int:
    cfg = _load_config()
    uninstall_drive_icon(config=cfg)
    print(f"Removed custom drive icon for {cfg.mount_drive}")
    return 0


def cmd_setup(args: argparse.Namespace) -> int:
    cfg = _load_config()
    changed = False
    if args.mount:
        cfg.mountpoint = args.mount
        changed = True
    if args.label:
        cfg.volume_label = args.label
        changed = True
    if changed:
        cfg.save()
    install_copy_link_menu(None)
    if args.icon_path:
        install_drive_icon(args.icon_path, args.label, config=cfg)
    install_autostart_task(args.task_name)
    print(f"Setup complete for {cfg.mount_drive} ({cfg.volume_label}).")
    print("Features enabled: context menu, autostart task" + (", custom drive icon" if args.icon_path else ""))
    print(f"Autostart log: {autostart_log_path()}")
    return 0


def cmd_bootstrap(args: argparse.Namespace) -> int:
    if shutil.which("winget"):
        cmd = ["winget", "install", "-e", "--id", "WinFsp.WinFsp"]
        if args.non_interactive:
            cmd += ["--accept-package-agreements", "--accept-source-agreements"]
        print("Running:", " ".join(cmd))
        return subprocess.call(cmd)
    if shutil.which("choco"):
        cmd = ["choco", "install", "winfsp", "-y"]
        print("Running:", " ".join(cmd))
        return subprocess.call(cmd)
    raise SystemExit("Neither winget nor choco was found. Install WinFsp manually.")


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    command = args.command
    if command == "init":
        return cmd_init(args)
    if command == "doctor":
        return cmd_doctor(args)
    if command == "mount":
        return cmd_mount(args)
    if command == "stats":
        return cmd_stats(args)
    if command == "ls":
        return cmd_ls(args)
    if command == "info":
        return cmd_info(args)
    if command in {"copy-link", "shell-copy-link"}:
        return cmd_copy_link(args)
    if command == "pull":
        return cmd_pull(args)
    if command == "rm":
        return cmd_rm(args)
    if command == "config":
        return cmd_config(args)
    if command == "install-autostart":
        return cmd_install_autostart(args)
    if command == "uninstall-autostart":
        return cmd_uninstall_autostart(args)
    if command == "install-drive-icon":
        return cmd_install_drive_icon(args)
    if command == "uninstall-drive-icon":
        return cmd_uninstall_drive_icon(args)
    if command == "setup":
        return cmd_setup(args)
    if command == "install-context-menu":
        return cmd_install_context_menu(args)
    if command == "uninstall-context-menu":
        return cmd_uninstall_context_menu(args)
    if command == "purge":
        return cmd_purge(args)
    if command == "bootstrap":
        return cmd_bootstrap(args)
    raise SystemExit(f"Unknown command: {command}")


if __name__ == "__main__":
    raise SystemExit(main())
