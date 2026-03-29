import ctypes
import ctypes.wintypes as wintypes
import os
import sys
import threading

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


class CONSOLE_SCREEN_BUFFER_INFOEX(ctypes.Structure):
    _fields_ = [
        ("cbSize", wintypes.ULONG),
        ("dwSize", COORD),
        ("dwCursorPosition", COORD),
        ("wAttributes", wintypes.WORD),
        ("srWindow", wintypes.SMALL_RECT),
        ("dwMaximumWindowSize", COORD),
        ("wPopupAttributes", wintypes.WORD),
        ("bFullscreenSupported", wintypes.BOOL),
        ("ColorTable", wintypes.DWORD * 16),
    ]


WINDOWS_TERMINAL_PALETTE = [
    0x0C0C0C,  # 0  Black
    0xC50F1F,  # 1  Dark Blue (stored as BGR: actually dark red)
    0x13A10E,  # 2  Dark Green
    0xC19C00,  # 3  Dark Cyan (actually dark yellow)
    0x0037DA,  # 4  Dark Red (actually dark blue)
    0x881798,  # 5  Dark Magenta
    0xF9F1A5,  # 6  Dark Yellow (actually bright cyan-ish)
    0xCCCCCC,  # 7  Gray
    0x767676,  # 8  Dark Gray
    0xE74856,  # 9  Blue (actually red)
    0x16C60C,  # 10 Green
    0xF9F1A5,  # 11 Cyan (actually bright yellow)
    0x3B78FF,  # 12 Red (actually blue)
    0xB4009E,  # 13 Magenta
    0x61D6D6,  # 14 Yellow (actually cyan)
    0xF2F2F2,  # 15 White
]


def _rgb_to_bgr(r, g, b):
    return b << 16 | g << 8 | r


CAMPBELL_PALETTE = [
    _rgb_to_bgr(12, 12, 12),       # 0  Black
    _rgb_to_bgr(197, 15, 31),      # 1  Dark Red
    _rgb_to_bgr(19, 161, 14),      # 2  Dark Green
    _rgb_to_bgr(193, 156, 0),      # 3  Dark Yellow
    _rgb_to_bgr(0, 55, 218),       # 4  Dark Blue
    _rgb_to_bgr(136, 23, 152),     # 5  Dark Magenta
    _rgb_to_bgr(58, 150, 221),     # 6  Dark Cyan
    _rgb_to_bgr(204, 204, 204),    # 7  Gray
    _rgb_to_bgr(118, 118, 118),    # 8  Dark Gray
    _rgb_to_bgr(231, 72, 86),      # 9  Red
    _rgb_to_bgr(22, 198, 12),      # 10 Green
    _rgb_to_bgr(249, 241, 165),    # 11 Yellow
    _rgb_to_bgr(59, 120, 255),     # 12 Blue
    _rgb_to_bgr(180, 0, 158),      # 13 Magenta
    _rgb_to_bgr(97, 214, 214),     # 14 Cyan
    _rgb_to_bgr(242, 242, 242),    # 15 White
]


def _get_hwnd():
    global _hwnd
    if _hwnd is None:
        _hwnd = kernel32.GetConsoleWindow()
    return _hwnd


def _set_icon():
    hwnd = _get_hwnd()
    exe_path = os.environ.get("PYAPP", "")
    if not hwnd or not exe_path:
        return
    WM_SETICON = 0x0080
    ICON_SMALL = 0
    ICON_BIG = 1
    shell32 = ctypes.windll.shell32
    icon_handle = shell32.ExtractIconW(0, exe_path, 0)
    if icon_handle and icon_handle != 1:
        user32.PostMessageW(hwnd, WM_SETICON, ICON_SMALL, icon_handle)
        user32.PostMessageW(hwnd, WM_SETICON, ICON_BIG, icon_handle)


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

    info = CONSOLE_SCREEN_BUFFER_INFOEX()
    info.cbSize = ctypes.sizeof(CONSOLE_SCREEN_BUFFER_INFOEX)
    kernel32.GetConsoleScreenBufferInfoEx(handle, ctypes.byref(info))
    for i, color in enumerate(CAMPBELL_PALETTE):
        info.ColorTable[i] = color
    info.srWindow.Bottom += 1
    info.srWindow.Right += 1
    kernel32.SetConsoleScreenBufferInfoEx(handle, ctypes.byref(info))


def setup():
    global _hwnd, _active
    if not os.environ.get("PYAPP"):
        return
    kernel32.AllocConsole()
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
        while True:
            if is_minimized():
                on_minimize()
            threading.Event().wait(0.2)

    thread = threading.Thread(target=_poll, daemon=True)
    thread.start()
