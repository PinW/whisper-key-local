"""
Helper script to show which PortAudio DLL sounddevice is actually using.

Usage:
    python documentation/temp/show_portaudio_dll.py
"""

from __future__ import annotations

import ctypes
import ctypes.util
import os
import sys
from pathlib import Path


def _ensure_sounddevice_loaded() -> None:
    """Call a cheap API so sounddevice eagerly loads PortAudio."""
    import sounddevice as sd  # type: ignore

    try:
        sd.query_devices()  # forces the shared library to load
    except Exception as exc:  # pragma: no cover - informational only
        print(f"sounddevice.query_devices() raised: {exc}")


def _path_from_sounddevice() -> Path | None:
    """Ask sounddevice's internal cffi handle for the DLL path."""
    import sounddevice as sd  # type: ignore

    lib = getattr(sd, "_lib", None)
    lib_name = getattr(lib, "_name", None)
    if isinstance(lib_name, str):
        candidate = Path(lib_name)
        if candidate.exists():
            return candidate
    return None


def _path_from_kernel32() -> Path | None:
    """Fallback: query Windows loader for the module path."""
    if os.name != "nt":
        return None

    kernel32 = ctypes.windll.kernel32
    kernel32.GetModuleHandleW.restype = ctypes.c_void_p
    handle = kernel32.GetModuleHandleW("portaudio.dll")
    if not handle:
        return None

    buffer = ctypes.create_unicode_buffer(260)
    if not kernel32.GetModuleFileNameW(handle, buffer, len(buffer)):
        return None
    candidate = Path(buffer.value)
    return candidate if candidate.exists() else None


def _path_from_ctypes_find() -> Path | None:
    """Last resort: ask ctypes where it would load PortAudio from."""
    name = ctypes.util.find_library("portaudio")
    if not name:
        return None
    candidate = Path(name)
    return candidate if candidate.exists() else None


def main() -> int:
    try:
        _ensure_sounddevice_loaded()
    except OSError as exc:
        print(f"✗ sounddevice could not load PortAudio: {exc}")
        return 1

    for resolver in (_path_from_sounddevice, _path_from_kernel32, _path_from_ctypes_find):
        try:
            path = resolver()
        except Exception as exc:  # pragma: no cover - diagnostics only
            print(f"{resolver.__name__} failed: {exc}")
            continue
        if path:
            print(f"✓ PortAudio loaded from: {path}")
            print(f"   (directory: {path.parent})")
            return 0

    print("✗ Unable to determine which PortAudio DLL is loaded.")
    print("  - Ensure sounddevice is installed and can query devices")
    print("  - Check PATH ordering with:  $env:PATH -split ';'")
    print("  - Use 'where portaudio.dll' to see all candidates Windows can find")
    return 1


if __name__ == "__main__":
    sys.exit(main())

