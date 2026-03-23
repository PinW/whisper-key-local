import ctypes
import ctypes.wintypes as wintypes
from dataclasses import dataclass

user32 = ctypes.windll.user32

MONITOR_DEFAULTTONEAREST = 2
MONITORINFOF_PRIMARY = 1

MonitorEnumProc = ctypes.WINFUNCTYPE(
    wintypes.BOOL, wintypes.HMONITOR, wintypes.HDC,
    ctypes.POINTER(wintypes.RECT), wintypes.LPARAM,
)


class MONITORINFOEXW(ctypes.Structure):
    _fields_ = [
        ("cbSize", wintypes.DWORD),
        ("rcMonitor", wintypes.RECT),
        ("rcWork", wintypes.RECT),
        ("dwFlags", wintypes.DWORD),
        ("szDevice", wintypes.WCHAR * 32),
    ]


@dataclass
class MonitorInfo:
    index: int
    name: str
    x: int
    y: int
    width: int
    height: int
    work_x: int
    work_y: int
    work_width: int
    work_height: int
    is_primary: bool


def _info_from_hmonitor(hmonitor, index=0):
    info = MONITORINFOEXW()
    info.cbSize = ctypes.sizeof(MONITORINFOEXW)
    user32.GetMonitorInfoW(hmonitor, ctypes.byref(info))
    rm = info.rcMonitor
    rw = info.rcWork
    return MonitorInfo(
        index=index,
        name=info.szDevice,
        x=rm.left, y=rm.top,
        width=rm.right - rm.left, height=rm.bottom - rm.top,
        work_x=rw.left, work_y=rw.top,
        work_width=rw.right - rw.left, work_height=rw.bottom - rw.top,
        is_primary=bool(info.dwFlags & MONITORINFOF_PRIMARY),
    )


def enumerate_monitors():
    handles = []

    def callback(hmonitor, hdc, rect, data):
        handles.append(hmonitor)
        return True

    proc = MonitorEnumProc(callback)
    user32.EnumDisplayMonitors(None, None, proc, 0)

    monitors = [_info_from_hmonitor(h, i) for i, h in enumerate(handles)]
    monitors.sort(key=lambda m: (m.x, m.y))
    for i, m in enumerate(monitors):
        m.index = i
    return monitors


def get_primary_monitor():
    for m in enumerate_monitors():
        if m.is_primary:
            return m
    monitors = enumerate_monitors()
    return monitors[0] if monitors else MonitorInfo(0, "", 0, 0, 1920, 1080, 0, 0, 1920, 1080, True)


def get_monitor_by_index(index):
    monitors = enumerate_monitors()
    if 0 <= index < len(monitors):
        return monitors[index]
    return get_primary_monitor()


def get_monitor_at_cursor():
    point = wintypes.POINT()
    user32.GetCursorPos(ctypes.byref(point))
    hmonitor = user32.MonitorFromPoint(point, MONITOR_DEFAULTTONEAREST)
    return _info_from_hmonitor(hmonitor)


def get_monitor_of_focused_window():
    hwnd = user32.GetForegroundWindow()
    if not hwnd:
        return get_monitor_at_cursor()
    hmonitor = user32.MonitorFromWindow(hwnd, MONITOR_DEFAULTTONEAREST)
    return _info_from_hmonitor(hmonitor)


def set_dpi_awareness():
    try:
        ctypes.windll.shcore.SetProcessDpiAwareness(2)
    except Exception:
        try:
            user32.SetProcessDPIAware()
        except Exception:
            pass
