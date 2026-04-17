import ctypes
import ctypes.wintypes as wintypes
import os
import sys
import threading
import time

user32 = ctypes.windll.user32
kernel32 = ctypes.windll.kernel32

SW_HIDE = 0
SW_RESTORE = 9
STD_OUTPUT_HANDLE = -11
ENABLE_VIRTUAL_TERMINAL_PROCESSING = 0x0004
ENABLE_PROCESSED_OUTPUT = 0x0001

LF_FACESIZE = 32
FF_MODERN = 0x30
FIXED_PITCH = 0x01
TMPF_TRUETYPE = 0x04

_hwnd = None
_active = False


class COORD(ctypes.Structure):
    _fields_ = [("X", ctypes.c_short), ("Y", ctypes.c_short)]


class CONSOLE_FONT_INFOEX(ctypes.Structure):
    _fields_ = [
        ("cbSize", wintypes.ULONG),
        ("nFont", wintypes.DWORD),
        ("dwFontSize", COORD),
        ("FontFamily", ctypes.c_uint),
        ("FontWeight", ctypes.c_uint),
        ("FaceName", ctypes.c_wchar * LF_FACESIZE),
    ]


def _get_hwnd():
    global _hwnd
    if _hwnd is None:
        _hwnd = kernel32.GetConsoleWindow()
    return _hwnd


WM_SETICON = 0x0080
ICON_SMALL = 0
ICON_BIG = 1


def _set_icon():
    hwnd = _get_hwnd()
    exe_path = os.environ.get("PYAPP", "")
    if not hwnd or not exe_path:
        return
    shell32 = ctypes.windll.shell32
    icon_handle = shell32.ExtractIconW(0, exe_path, 0)
    if icon_handle and icon_handle != 1:
        user32.SendMessageW(hwnd, WM_SETICON, ICON_SMALL, icon_handle)
        user32.SendMessageW(hwnd, WM_SETICON, ICON_BIG, icon_handle)


def _configure_console():
    kernel32.SetConsoleTitleW("Whisper Key")
    _set_icon()

    handle = kernel32.GetStdHandle(STD_OUTPUT_HANDLE)

    mode = wintypes.DWORD()
    kernel32.GetConsoleMode(handle, ctypes.byref(mode))
    mode.value |= ENABLE_VIRTUAL_TERMINAL_PROCESSING | ENABLE_PROCESSED_OUTPUT
    kernel32.SetConsoleMode(handle, mode)

    font = CONSOLE_FONT_INFOEX()
    font.cbSize = ctypes.sizeof(CONSOLE_FONT_INFOEX)
    font.dwFontSize.X = 0
    font.dwFontSize.Y = 22
    font.FontFamily = FF_MODERN | FIXED_PITCH | TMPF_TRUETYPE
    font.FontWeight = 400
    font.FaceName = "Cascadia Mono"
    kernel32.SetCurrentConsoleFontEx(handle, False, ctypes.byref(font))


def setup():
    global _hwnd, _active
    if not os.environ.get("PYAPP"):
        return
    if not kernel32.AllocConsole():
        return
    _hwnd = None
    _get_hwnd()
    sys.stdout = open("CONOUT$", "w", encoding="utf-8", errors="replace")
    sys.stderr = open("CONOUT$", "w", encoding="utf-8", errors="replace")
    sys.stdin = open("CONIN$", "r")
    _configure_console()
    _active = True


def owns_console():
    return _active


def hide():
    hwnd = _get_hwnd()
    if hwnd:
        user32.ShowWindow(hwnd, SW_HIDE)


def show():
    hwnd = _get_hwnd()
    if hwnd:
        user32.ShowWindow(hwnd, SW_HIDE)
        user32.ShowWindow(hwnd, SW_RESTORE)
        user32.SetForegroundWindow(hwnd)


def is_minimized():
    hwnd = _get_hwnd()
    if not hwnd:
        return False
    return bool(user32.IsIconic(hwnd))


def start_minimize_monitor(on_minimize):
    def _poll():
        was_minimized = False
        while True:
            if is_minimized():
                if not was_minimized:
                    on_minimize()
                    was_minimized = True
            else:
                was_minimized = False
            time.sleep(0.2)

    thread = threading.Thread(target=_poll, daemon=True)
    thread.start()
