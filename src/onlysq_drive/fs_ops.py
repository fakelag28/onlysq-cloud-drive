from __future__ import annotations

import logging
import threading
from dataclasses import dataclass
from functools import wraps
from pathlib import Path
from typing import Any

from winfspy import (
    BaseFileSystemOperations,
    CREATE_FILE_CREATE_OPTIONS,
    FILE_ATTRIBUTE,
    NTStatusAccessDenied,
    NTStatusDirectoryNotEmpty,
    NTStatusEndOfFile,
    NTStatusMediaWriteProtected,
    NTStatusNotADirectory,
    NTStatusObjectNameCollision,
    NTStatusObjectNameNotFound,
)
from winfspy.plumbing.security_descriptor import SecurityDescriptor
from winfspy.plumbing.win32_filetime import filetime_now

from .cloud_client import CloudClient
from .index_db import EntryRecord, IndexDB
from .vpaths import basename, join_virtual_path, normalize_virtual_path, parent_path


DEFAULT_SD = "O:BAG:BAD:P(A;;FA;;;SY)(A;;FA;;;BA)(A;;FA;;;WD)"
FSP_CLEANUP_DELETE = 0x01
FSP_CLEANUP_SET_ALLOCATION_SIZE = 0x02
FSP_CLEANUP_SET_ARCHIVE_BIT = 0x10
FSP_CLEANUP_SET_LAST_ACCESS_TIME = 0x20
FSP_CLEANUP_SET_LAST_WRITE_TIME = 0x40
FSP_CLEANUP_SET_CHANGE_TIME = 0x80


def operation(fn):
    name = fn.__name__

    @wraps(fn)
    def wrapper(self, *args, **kwargs):
        head = args[0] if args else None
        tail = args[1:] if args else ()
        try:
            with self._thread_lock:
                result = fn(self, *args, **kwargs)
        except Exception as exc:
            logging.info(" NOK | %s | %r | %r | %r", name, head, tail, exc)
            raise
        else:
            logging.info(" OK! | %s | %r | %r | %r", name, head, tail, result)
            return result

    return wrapper


@dataclass(slots=True)
class BaseEntryObj:
    path: str
    attributes: int
    security_descriptor: SecurityDescriptor
    creation_time: int
    last_access_time: int
    last_write_time: int
    change_time: int
    file_size: int
    cache_path: Path | None = None
    remote_id: str | None = None
    owner_key: str | None = None
    public_url: str | None = None
    dirty: bool = False
    allocation_size: int = 0
    index_number: int = 0

    @property
    def file_name(self) -> str:
        if self.path == "/":
            return "\\"
        return self.path.replace("/", "\\")

    @property
    def name(self) -> str:
        return basename(self.path)

    def get_file_info(self) -> dict[str, Any]:
        return {
            "file_attributes": self.attributes,
            "allocation_size": self.allocation_size,
            "file_size": self.file_size,
            "creation_time": self.creation_time,
            "last_access_time": self.last_access_time,
            "last_write_time": self.last_write_time,
            "change_time": self.change_time,
            "index_number": self.index_number,
        }


class FileObj(BaseEntryObj):
    allocation_unit = 4096

    def ensure_cache(self, cloud: CloudClient) -> None:
        assert self.cache_path is not None
        if self.cache_path.exists():
            self.file_size = self.cache_path.stat().st_size
            self.allocation_size = self._round_allocation(self.file_size)
            return
        self.cache_path.parent.mkdir(parents=True, exist_ok=True)
        if self.remote_id:
            cloud.download(self.remote_id, self.cache_path)
        else:
            self.cache_path.touch()
        self.file_size = self.cache_path.stat().st_size
        self.allocation_size = self._round_allocation(self.file_size)

    def _round_allocation(self, size: int) -> int:
        units = (size + self.allocation_unit - 1) // self.allocation_unit if size else 0
        return units * self.allocation_unit

    def set_allocation_size(self, allocation_size: int, cloud: CloudClient) -> None:
        self.ensure_cache(cloud)
        with self.cache_path.open("r+b") as handle:
            handle.truncate(allocation_size)
        self.allocation_size = allocation_size
        self.file_size = min(self.file_size, allocation_size)
        self.dirty = True

    def set_file_size(self, file_size: int, cloud: CloudClient) -> None:
        self.ensure_cache(cloud)
        with self.cache_path.open("r+b") as handle:
            handle.truncate(file_size)
        self.file_size = file_size
        self.allocation_size = self._round_allocation(self.file_size)
        self.dirty = True

    def read(self, cloud: CloudClient, offset: int, length: int) -> bytes:
        self.ensure_cache(cloud)
        if offset >= self.file_size:
            raise NTStatusEndOfFile()
        with self.cache_path.open("rb") as handle:
            handle.seek(offset)
            data = handle.read(length)
        self.last_access_time = filetime_now()
        return data

    def write(self, cloud: CloudClient, buffer: bytes, offset: int, write_to_end_of_file: bool) -> int:
        self.ensure_cache(cloud)
        if write_to_end_of_file:
            offset = self.file_size
        self.cache_path.parent.mkdir(parents=True, exist_ok=True)
        with self.cache_path.open("r+b") as handle:
            handle.seek(offset)
            handle.write(buffer)
        self.file_size = self.cache_path.stat().st_size
        self.allocation_size = self._round_allocation(self.file_size)
        now = filetime_now()
        self.last_access_time = now
        self.last_write_time = now
        self.change_time = now
        self.dirty = True
        return len(buffer)

    def constrained_write(self, cloud: CloudClient, buffer: bytes, offset: int) -> int:
        self.ensure_cache(cloud)
        if offset >= self.file_size:
            return 0
        remaining = self.file_size - offset
        write_buf = buffer[:remaining]
        with self.cache_path.open("r+b") as handle:
            handle.seek(offset)
            handle.write(write_buf)
        now = filetime_now()
        self.last_access_time = now
        self.last_write_time = now
        self.change_time = now
        self.dirty = True
        return len(write_buf)


class FolderObj(BaseEntryObj):
    pass


@dataclass(slots=True)
class OpenedObj:
    file_obj: BaseEntryObj


class OnlySQFileSystemOperations(BaseFileSystemOperations):
    def __init__(self, db: IndexDB, cloud: CloudClient, volume_label: str) -> None:
        super().__init__()
        if len(volume_label) > 31:
            raise ValueError("volume label must be <= 31 characters")
        self.db = db
        self.cloud = cloud
        self._thread_lock = threading.Lock()
        self._sd = SecurityDescriptor.from_string(DEFAULT_SD)
        self._entries: dict[str, BaseEntryObj] = {}
        self._volume_info = {
            "total_size": 1024 * 1024 * 1024 * 1024,
            "free_size": 1024 * 1024 * 1024 * 1024,
            "volume_label": volume_label,
        }
        self._ensure_root()
        self._load_from_db()

    def _ensure_root(self) -> None:
        now = filetime_now()
        self.db.ensure_root(
            ctime=now,
            atime=now,
            mtime=now,
            change_time=now,
            file_attributes=int(FILE_ATTRIBUTE.FILE_ATTRIBUTE_DIRECTORY),
        )

    def _load_from_db(self) -> None:
        self._entries.clear()
        for record in self.db.iter_entries():
            obj = self._record_to_obj(record)
            self._entries[record.path] = obj

    def _record_to_obj(self, record: EntryRecord) -> BaseEntryObj:
        kwargs = dict(
            path=record.path,
            attributes=record.file_attributes,
            security_descriptor=self._sd,
            creation_time=record.ctime,
            last_access_time=record.atime,
            last_write_time=record.mtime,
            change_time=record.change_time,
            file_size=record.size,
            cache_path=self.db.get_cache_abs_path(record.cache_relpath) if record.cache_relpath else None,
            remote_id=record.remote_id,
            owner_key=record.owner_key,
            public_url=record.public_url,
            dirty=record.dirty,
            allocation_size=record.size,
            index_number=0,
        )
        if record.kind == "dir":
            kwargs["cache_path"] = None
            kwargs["allocation_size"] = 0
            kwargs["file_size"] = 0
            return FolderObj(**kwargs)
        return FileObj(**kwargs)

    def _persist_obj(self, obj: BaseEntryObj) -> None:
        record = EntryRecord(
            path=obj.path,
            kind="dir" if isinstance(obj, FolderObj) else "file",
            size=obj.file_size,
            ctime=obj.creation_time,
            atime=obj.last_access_time,
            mtime=obj.last_write_time,
            change_time=obj.change_time,
            file_attributes=int(obj.attributes),
            cache_relpath=obj.cache_path.name if obj.cache_path else None,
            remote_id=obj.remote_id,
            owner_key=obj.owner_key,
            public_url=obj.public_url,
            dirty=obj.dirty,
        )
        self.db.update_entry(record)

    def _sync_file(self, file_obj: FileObj) -> None:
        file_obj.ensure_cache(self.cloud)
        if not file_obj.dirty and file_obj.remote_id:
            return
        old_remote_id = file_obj.remote_id
        old_owner_key = file_obj.owner_key
        uploaded = self.cloud.upload(file_obj.cache_path)
        file_obj.remote_id = uploaded.remote_id
        file_obj.public_url = uploaded.public_url
        file_obj.owner_key = uploaded.owner_key
        file_obj.file_size = file_obj.cache_path.stat().st_size
        file_obj.allocation_size = file_obj._round_allocation(file_obj.file_size)
        file_obj.dirty = False
        now = filetime_now()
        file_obj.last_access_time = now
        file_obj.last_write_time = now
        file_obj.change_time = now
        self.db.set_remote(
            file_obj.path,
            remote_id=file_obj.remote_id,
            owner_key=file_obj.owner_key,
            public_url=file_obj.public_url,
            size=file_obj.file_size,
            dirty=False,
            atime=file_obj.last_access_time,
            mtime=file_obj.last_write_time,
            change_time=file_obj.change_time,
        )
        if old_remote_id and old_owner_key and old_remote_id != file_obj.remote_id:
            try:
                self.cloud.delete(old_remote_id, old_owner_key)
            except Exception as exc:
                logging.warning("Failed to delete old remote object %s: %s", old_remote_id, exc)

    @operation
    def get_volume_info(self):
        used = self.db.total_file_size()
        self._volume_info["free_size"] = max(0, self._volume_info["total_size"] - used)
        return self._volume_info

    @operation
    def set_volume_label(self, volume_label):
        self._volume_info["volume_label"] = volume_label

    @operation
    def get_security_by_name(self, file_name):
        path = normalize_virtual_path(file_name)
        try:
            obj = self._entries[path]
        except KeyError:
            raise NTStatusObjectNameNotFound()
        return obj.attributes, obj.security_descriptor.handle, obj.security_descriptor.size

    @operation
    def create(
        self,
        file_name,
        create_options,
        granted_access,
        file_attributes,
        security_descriptor,
        allocation_size,
    ):
        path = normalize_virtual_path(file_name)
        parent = parent_path(path)
        parent_obj = self._entries.get(parent)
        if parent_obj is None:
            raise NTStatusObjectNameNotFound()
        if isinstance(parent_obj, FileObj):
            raise NTStatusNotADirectory()
        if path in self._entries:
            raise NTStatusObjectNameCollision()
        now = filetime_now()
        if create_options & CREATE_FILE_CREATE_OPTIONS.FILE_DIRECTORY_FILE:
            attrs = int(file_attributes) | int(FILE_ATTRIBUTE.FILE_ATTRIBUTE_DIRECTORY)
            obj = FolderObj(
                path=path,
                attributes=attrs,
                security_descriptor=security_descriptor,
                creation_time=now,
                last_access_time=now,
                last_write_time=now,
                change_time=now,
                file_size=0,
                allocation_size=0,
            )
            self.db.ensure_dir(
                path,
                ctime=now,
                atime=now,
                mtime=now,
                change_time=now,
                file_attributes=attrs,
            )
        else:
            attrs = int(file_attributes) | int(FILE_ATTRIBUTE.FILE_ATTRIBUTE_ARCHIVE)
            cache_relpath = self.db.generate_cache_relpath(basename(path) or "unnamed.bin")
            cache_path = self.db.get_cache_abs_path(cache_relpath)
            cache_path.parent.mkdir(parents=True, exist_ok=True)
            cache_path.touch()
            if allocation_size:
                with cache_path.open("r+b") as handle:
                    handle.truncate(allocation_size)
            obj = FileObj(
                path=path,
                attributes=attrs,
                security_descriptor=security_descriptor,
                creation_time=now,
                last_access_time=now,
                last_write_time=now,
                change_time=now,
                file_size=allocation_size,
                allocation_size=allocation_size,
                cache_path=cache_path,
                dirty=True,
            )
            self.db.create_file(
                path,
                ctime=now,
                atime=now,
                mtime=now,
                change_time=now,
                file_attributes=attrs,
                cache_relpath=cache_relpath,
                size=allocation_size,
                dirty=True,
            )
        self._entries[path] = obj
        return OpenedObj(obj)

    @operation
    def open(self, file_name, create_options, granted_access):
        path = normalize_virtual_path(file_name)
        try:
            return OpenedObj(self._entries[path])
        except KeyError:
            raise NTStatusObjectNameNotFound()

    @operation
    def close(self, file_context):
        obj = file_context.file_obj
        if isinstance(obj, FileObj) and (obj.dirty or not obj.remote_id):
            self._sync_file(obj)

    @operation
    def get_file_info(self, file_context):
        obj = file_context.file_obj
        if isinstance(obj, FileObj):
            obj.ensure_cache(self.cloud)
        return obj.get_file_info()

    @operation
    def get_security(self, file_context):
        return file_context.file_obj.security_descriptor

    @operation
    def set_security(self, file_context, security_information, modification_descriptor):
        obj = file_context.file_obj
        obj.security_descriptor = obj.security_descriptor.evolve(security_information, modification_descriptor)
        if obj.path != "/":
            self._persist_obj(obj)

    @operation
    def rename(self, file_context, file_name, new_file_name, replace_if_exists):
        old_path = normalize_virtual_path(file_name)
        new_path = normalize_virtual_path(new_file_name)
        obj = self._entries.get(old_path)
        if obj is None:
            raise NTStatusObjectNameNotFound()
        new_parent = self._entries.get(parent_path(new_path))
        if new_parent is None or isinstance(new_parent, FileObj):
            raise NTStatusNotADirectory()
        if new_path in self._entries:
            existing = self._entries[new_path]
            if not replace_if_exists:
                raise NTStatusObjectNameCollision()
            if isinstance(existing, FolderObj):
                raise NTStatusAccessDenied()
            if isinstance(existing, FileObj) and existing.remote_id and existing.owner_key:
                try:
                    self.cloud.delete(existing.remote_id, existing.owner_key)
                except Exception as exc:
                    logging.warning("Failed to delete replaced remote object %s: %s", existing.remote_id, exc)
            if isinstance(existing, FileObj) and existing.cache_path and existing.cache_path.exists():
                existing.cache_path.unlink(missing_ok=True)
            self._entries.pop(new_path, None)
            self.db.delete_path(new_path)
        affected = [p for p in self._entries if p == old_path or p.startswith(old_path + "/")]
        affected.sort(key=len)
        moved: dict[str, BaseEntryObj] = {}
        for current_path in affected:
            entry = self._entries.pop(current_path)
            target_path = new_path if current_path == old_path else new_path + current_path[len(old_path):]
            entry.path = target_path
            moved[target_path] = entry
        self._entries.update(moved)
        self.db.rename_subtree(old_path, new_path)

    @operation
    def set_basic_info(
        self,
        file_context,
        file_attributes,
        creation_time,
        last_access_time,
        last_write_time,
        change_time,
        file_info,
    ):
        obj = file_context.file_obj
        if file_attributes != FILE_ATTRIBUTE.INVALID_FILE_ATTRIBUTES:
            obj.attributes = int(file_attributes)
        if creation_time:
            obj.creation_time = creation_time
        if last_access_time:
            obj.last_access_time = last_access_time
        if last_write_time:
            obj.last_write_time = last_write_time
        if change_time:
            obj.change_time = change_time
        if obj.path != "/":
            self.db.set_times_and_attrs(
                obj.path,
                ctime=obj.creation_time,
                atime=obj.last_access_time,
                mtime=obj.last_write_time,
                change_time=obj.change_time,
                file_attributes=int(obj.attributes),
                size=obj.file_size,
            )
        return obj.get_file_info()

    @operation
    def set_file_size(self, file_context, new_size, set_allocation_size):
        obj = file_context.file_obj
        if not isinstance(obj, FileObj):
            raise NTStatusAccessDenied()
        if set_allocation_size:
            obj.set_allocation_size(new_size, self.cloud)
        else:
            obj.set_file_size(new_size, self.cloud)
        self.db.mark_dirty(
            obj.path,
            size=obj.file_size,
            atime=obj.last_access_time,
            mtime=obj.last_write_time,
            change_time=obj.change_time,
        )

    @operation
    def can_delete(self, file_context, file_name):
        path = normalize_virtual_path(file_name)
        obj = self._entries.get(path)
        if obj is None:
            raise NTStatusObjectNameNotFound()
        if isinstance(obj, FolderObj):
            for entry_path in self._entries:
                if parent_path(entry_path) == path:
                    raise NTStatusDirectoryNotEmpty()

    @operation
    def read_directory(self, file_context, marker):
        obj = file_context.file_obj
        if isinstance(obj, FileObj):
            raise NTStatusNotADirectory()
        entries: list[dict[str, Any]] = []
        if obj.path != "/":
            parent_obj = self._entries[parent_path(obj.path)]
            entries.append({"file_name": ".", **obj.get_file_info()})
            entries.append({"file_name": "..", **parent_obj.get_file_info()})
        for record in self.db.list_children(obj.path):
            child = self._entries[record.path]
            entries.append({"file_name": child.name, **child.get_file_info()})
        entries.sort(key=lambda item: str(item["file_name"]).lower())
        if marker is None:
            return entries
        for idx, entry in enumerate(entries):
            if entry["file_name"] == marker:
                return entries[idx + 1 :]
        return []

    @operation
    def get_dir_info_by_name(self, file_context, file_name):
        path = join_virtual_path(file_context.file_obj.path, file_name)
        obj = self._entries.get(path)
        if obj is None:
            raise NTStatusObjectNameNotFound()
        return {"file_name": obj.name, **obj.get_file_info()}

    @operation
    def read(self, file_context, offset, length):
        obj = file_context.file_obj
        if not isinstance(obj, FileObj):
            raise NTStatusAccessDenied()
        return obj.read(self.cloud, offset, length)

    @operation
    def write(self, file_context, buffer, offset, write_to_end_of_file, constrained_io):
        obj = file_context.file_obj
        if not isinstance(obj, FileObj):
            raise NTStatusAccessDenied()
        if constrained_io:
            written = obj.constrained_write(self.cloud, buffer, offset)
        else:
            written = obj.write(self.cloud, buffer, offset, write_to_end_of_file)
        self.db.mark_dirty(
            obj.path,
            size=obj.file_size,
            atime=obj.last_access_time,
            mtime=obj.last_write_time,
            change_time=obj.change_time,
        )
        return written

    @operation
    def cleanup(self, file_context, file_name, flags):
        obj = file_context.file_obj
        if flags & FSP_CLEANUP_DELETE:
            if isinstance(obj, FolderObj):
                for entry_path in self._entries:
                    if parent_path(entry_path) == obj.path:
                        raise NTStatusDirectoryNotEmpty()
            if isinstance(obj, FileObj) and obj.remote_id and obj.owner_key:
                self.cloud.delete(obj.remote_id, obj.owner_key)
            if isinstance(obj, FileObj) and obj.cache_path and obj.cache_path.exists():
                obj.cache_path.unlink(missing_ok=True)
            self._entries.pop(obj.path, None)
            if obj.path != "/":
                self.db.delete_path(obj.path)
            return
        if isinstance(obj, FileObj) and (obj.dirty or not obj.remote_id):
            self._sync_file(obj)
        if flags & FSP_CLEANUP_SET_ALLOCATION_SIZE and isinstance(obj, FileObj):
            obj.allocation_size = obj.file_size
        if flags & FSP_CLEANUP_SET_ARCHIVE_BIT and isinstance(obj, FileObj):
            obj.attributes |= int(FILE_ATTRIBUTE.FILE_ATTRIBUTE_ARCHIVE)
        now = filetime_now()
        if flags & FSP_CLEANUP_SET_LAST_ACCESS_TIME:
            obj.last_access_time = now
        if flags & FSP_CLEANUP_SET_LAST_WRITE_TIME:
            obj.last_write_time = now
        if flags & FSP_CLEANUP_SET_CHANGE_TIME:
            obj.change_time = now
        if obj.path != "/":
            self.db.set_times_and_attrs(
                obj.path,
                ctime=obj.creation_time,
                atime=obj.last_access_time,
                mtime=obj.last_write_time,
                change_time=obj.change_time,
                file_attributes=int(obj.attributes),
                size=obj.file_size,
            )

    @operation
    def overwrite(self, file_context, file_attributes, replace_file_attributes, allocation_size):
        obj = file_context.file_obj
        if not isinstance(obj, FileObj):
            raise NTStatusAccessDenied()
        file_attributes = int(file_attributes) | int(FILE_ATTRIBUTE.FILE_ATTRIBUTE_ARCHIVE)
        if replace_file_attributes:
            obj.attributes = file_attributes
        else:
            obj.attributes |= file_attributes
        obj.set_allocation_size(allocation_size, self.cloud)
        now = filetime_now()
        obj.last_access_time = now
        obj.last_write_time = now
        obj.change_time = now
        self.db.mark_dirty(
            obj.path,
            size=obj.file_size,
            atime=obj.last_access_time,
            mtime=obj.last_write_time,
            change_time=obj.change_time,
        )

    @operation
    def flush(self, file_context):
        obj = file_context.file_obj
        if isinstance(obj, FileObj) and (obj.dirty or not obj.remote_id):
            self._sync_file(obj)
