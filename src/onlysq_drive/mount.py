from __future__ import annotations

import logging
import os
import platform
import signal
import subprocess
import sys
import threading
from pathlib import Path

from .cloud_client import CloudClient
from .config import AppConfig
from .index_db import IndexDB

IS_WINDOWS = platform.system() == "Windows"


def _resolve_mountpoint_str(raw: str) -> str:
    return os.path.normpath(os.path.expanduser(raw))


def _is_mountpoint_busy(path: str) -> bool:
    if IS_WINDOWS:
        return False
    try:
        with open("/proc/mounts", "r", encoding="utf-8") as f:
            for line in f:
                parts = line.split()
                if len(parts) >= 2 and parts[1] == path:
                    return True
    except OSError:
        pass
    return False


def _try_unmount_stale(path: str) -> bool:
    if IS_WINDOWS:
        return False
    for cmd in [
        ["fusermount3", "-u", path],
        ["fusermount3", "-uz", path],
        ["sudo", "umount", "-l", path],
    ]:
        try:
            result = subprocess.run(cmd, capture_output=True, timeout=5)
            if result.returncode == 0:
                return True
        except Exception:
            continue
    return False


class MountedDrive:
    def __init__(self, config: AppConfig) -> None:
        self.config = config
        self.db = IndexDB()
        self.cloud = CloudClient(config)
        self.fs = None
        self._close = None

        if IS_WINDOWS:
            self._init_windows()
        else:
            self._init_linux()

    def _init_windows(self) -> None:
        from winfspy import FileSystem
        from winfspy.plumbing.win32_filetime import filetime_now

        from .fs_ops import OnlySQFileSystemOperations

        operations = OnlySQFileSystemOperations(self.db, self.cloud, self.config.volume_label)
        mountpoint = Path(self.config.mount_drive)
        is_drive = mountpoint.parent == mountpoint
        reject_irp_prior_to_transact0 = not is_drive
        self.fs = FileSystem(
            str(mountpoint),
            operations,
            sector_size=512,
            sectors_per_allocation_unit=1,
            volume_creation_time=filetime_now(),
            volume_serial_number=0,
            file_info_timeout=1000,
            case_sensitive_search=1,
            case_preserved_names=1,
            unicode_on_disk=1,
            persistent_acls=1,
            post_cleanup_when_modified_only=1,
            um_file_context_is_user_context2=1,
            file_system_name=self.config.volume_label,
            prefix="",
            debug=self.config.debug,
            reject_irp_prior_to_transact0=reject_irp_prior_to_transact0,
        )
        self._close = self.db.close

    def _init_linux(self) -> None:
        import pyfuse3

        from .fs_ops_linux import OnlySQFuseOperations

        mountpoint_str = _resolve_mountpoint_str(self.config.mountpoint)
        if not os.path.isdir(mountpoint_str):
            raise RuntimeError(
                f"Mountpoint directory does not exist: {mountpoint_str}\n"
                f"Run 'onlysq-drive setup' first to create it."
            )

        operations = OnlySQFuseOperations(self.db, self.cloud, self.config.volume_label)
        fuse_options = set(pyfuse3.default_options)
        fuse_options.add("fsname=onlysq-drive")
        fuse_options.add("subtype=rclone")
        fuse_options.add("x-gvfs-show")
        fuse_options.discard("default_permissions")
        if self.config.debug:
            fuse_options.add("debug")

        pyfuse3.init(operations, mountpoint_str, fuse_options)

        def _close() -> None:
            pyfuse3.close(unmount=True)
            self.db.close()

        self._close = _close

    def start(self) -> None:
        logging.basicConfig(stream=sys.stdout, level=logging.INFO)
        if IS_WINDOWS:
            from winfspy import enable_debug_log

            if self.config.debug:
                enable_debug_log()
            self.fs.start()

    def stop(self) -> None:
        try:
            if IS_WINDOWS and self.fs is not None:
                self.fs.stop()
        finally:
            if self._close:
                self._close()


def _run_mount_windows(config: AppConfig) -> int:
    stop_event = threading.Event()
    mounted = MountedDrive(config)

    def _handler(signum, frame):
        stop_event.set()

    signal.signal(signal.SIGINT, _handler)
    if hasattr(signal, "SIGTERM"):
        signal.signal(signal.SIGTERM, _handler)

    mounted.start()
    print(f"Mounted {config.mount_drive} as {config.volume_label}. Press Ctrl+C to stop.")
    try:
        stop_event.wait()
        return 0
    finally:
        mounted.stop()
        print("Drive unmounted.")


def _run_mount_linux(config: AppConfig) -> int:
    import trio
    import pyfuse3

    logging.basicConfig(stream=sys.stdout, level=logging.INFO)
    mountpoint_str = _resolve_mountpoint_str(config.mountpoint)

    if _is_mountpoint_busy(mountpoint_str):
        logging.info("Mountpoint %s is busy, attempting fusermount3 -u ...", mountpoint_str)
        if _try_unmount_stale(mountpoint_str):
            logging.info("Stale mount cleaned up successfully.")
        else:
            print(
                f"Error: {mountpoint_str} is already mounted and cannot be unmounted.\n\n"
                f"Likely the systemd service is already running:\n"
                f"  systemctl --user status onlysq-drive\n\n"
                f"To stop it and mount manually:\n"
                f"  systemctl --user stop onlysq-drive\n"
                f"  onlysq-drive mount\n\n"
                f"To force-unmount:\n"
                f"  fusermount3 -u {mountpoint_str}",
                file=sys.stderr,
            )
            return 1

    mounted = MountedDrive(config)
    print(f"Mounted {mountpoint_str} as {config.volume_label}. Press Ctrl+C to stop.")

    async def _main() -> None:
        await pyfuse3.main()

    try:
        trio.run(_main)
    except KeyboardInterrupt:
        pass
    finally:
        mounted.stop()
        print("Drive unmounted.")
    return 0


def run_mount(config: AppConfig) -> int:
    if IS_WINDOWS:
        return _run_mount_windows(config)
    return _run_mount_linux(config)
