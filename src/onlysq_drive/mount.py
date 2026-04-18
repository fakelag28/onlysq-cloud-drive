from __future__ import annotations

import logging
import signal
import sys
import threading
from pathlib import Path

from winfspy import FileSystem, enable_debug_log
from winfspy.plumbing.win32_filetime import filetime_now

from .cloud_client import CloudClient
from .config import AppConfig
from .fs_ops import OnlySQFileSystemOperations
from .index_db import IndexDB


class MountedDrive:
    def __init__(self, config: AppConfig) -> None:
        self.config = config
        self.db = IndexDB()
        self.cloud = CloudClient(config)
        self.operations = OnlySQFileSystemOperations(self.db, self.cloud, config.volume_label)
        mountpoint = Path(config.mount_drive)
        is_drive = mountpoint.parent == mountpoint
        reject_irp_prior_to_transact0 = not is_drive
        self.fs = FileSystem(
            str(mountpoint),
            self.operations,
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
            file_system_name=config.volume_label,
            prefix="",
            debug=config.debug,
            reject_irp_prior_to_transact0=reject_irp_prior_to_transact0,
        )

    def start(self) -> None:
        if self.config.debug:
            enable_debug_log()
        logging.basicConfig(stream=sys.stdout, level=logging.INFO)
        self.fs.start()

    def stop(self) -> None:
        try:
            self.fs.stop()
        finally:
            self.db.close()


def run_mount(config: AppConfig) -> int:
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
