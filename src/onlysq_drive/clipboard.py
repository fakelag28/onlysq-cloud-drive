from __future__ import annotations

import ctypes
from ctypes import wintypes


def copy_text(text: str) -> None:
    GMEM_MOVEABLE = 0x0002
    CF_UNICODETEXT = 13

    user32 = ctypes.WinDLL("user32", use_last_error=True)
    kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)

    user32.OpenClipboard.argtypes = [wintypes.HWND]
    user32.OpenClipboard.restype = wintypes.BOOL
    user32.EmptyClipboard.argtypes = []
    user32.EmptyClipboard.restype = wintypes.BOOL
    user32.SetClipboardData.argtypes = [wintypes.UINT, wintypes.HANDLE]
    user32.SetClipboardData.restype = wintypes.HANDLE
    user32.CloseClipboard.argtypes = []
    user32.CloseClipboard.restype = wintypes.BOOL

    kernel32.GlobalAlloc.argtypes = [wintypes.UINT, ctypes.c_size_t]
    kernel32.GlobalAlloc.restype = wintypes.HGLOBAL
    kernel32.GlobalLock.argtypes = [wintypes.HGLOBAL]
    kernel32.GlobalLock.restype = wintypes.LPVOID
    kernel32.GlobalUnlock.argtypes = [wintypes.HGLOBAL]
    kernel32.GlobalUnlock.restype = wintypes.BOOL

    data = text.encode("utf-16-le") + b"\x00\x00"
    h_global = kernel32.GlobalAlloc(GMEM_MOVEABLE, len(data))
    if not h_global:
        raise OSError("GlobalAlloc failed")

    locked = kernel32.GlobalLock(h_global)
    if not locked:
        raise OSError("GlobalLock failed")

    ctypes.memmove(locked, data, len(data))
    kernel32.GlobalUnlock(h_global)

    if not user32.OpenClipboard(None):
        raise OSError("OpenClipboard failed")
    try:
        if not user32.EmptyClipboard():
            raise OSError("EmptyClipboard failed")
        if not user32.SetClipboardData(CF_UNICODETEXT, h_global):
            raise OSError("SetClipboardData failed")
        h_global = None
    finally:
        user32.CloseClipboard()
