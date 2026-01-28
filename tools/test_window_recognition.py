#!/usr/bin/env python3

import ctypes
import os
import sys

import win32con
import win32gui
import win32api
import win32process

DWMWA_CLOAKED = 14
win_dll = getattr(ctypes, "WinDLL", None)
dwmapi = win_dll("dwmapi") if win_dll else None


def is_windows():
    return sys.platform == "win32"


def is_cloaked(hwnd):
    if dwmapi is None:
        return False
    cloaked = ctypes.c_int(0)
    dwmapi.DwmGetWindowAttribute(
        hwnd,
        DWMWA_CLOAKED,
        ctypes.byref(cloaked),
        ctypes.sizeof(cloaked),
    )
    return cloaked.value != 0


def get_exe_name(pid):
    try:
        handle = win32api.OpenProcess(
            win32con.PROCESS_QUERY_INFORMATION | win32con.PROCESS_VM_READ,
            False,
            pid,
        )
    except Exception:
        return "unknown"
    try:
        path = win32process.GetModuleFileNameEx(handle, 0)
        return os.path.basename(path) if path else "unknown"
    except Exception:
        return "unknown"
    finally:
        win32api.CloseHandle(handle)


def get_active_window():
    hwnd = win32gui.GetForegroundWindow()
    title = win32gui.GetWindowText(hwnd)
    _, pid = win32process.GetWindowThreadProcessId(hwnd)
    return {
        "hwnd": hwnd,
        "title": title,
        "pid": pid,
        "exe": get_exe_name(pid),
        "class": win32gui.GetClassName(hwnd),
        "iconic": win32gui.IsIconic(hwnd),
    }


def list_open_windows():
    windows = []

    def callback(hwnd, _):
        if not win32gui.IsWindowVisible(hwnd):
            return True
        if is_cloaked(hwnd):
            return True
        title = win32gui.GetWindowText(hwnd)
        if not title:
            return True
        exstyle = win32gui.GetWindowLong(hwnd, win32con.GWL_EXSTYLE)
        if exstyle & win32con.WS_EX_TOOLWINDOW:
            return True

        _, pid = win32process.GetWindowThreadProcessId(hwnd)
        windows.append({
            "hwnd": hwnd,
            "title": title,
            "pid": pid,
            "exe": get_exe_name(pid),
            "class": win32gui.GetClassName(hwnd),
            "iconic": win32gui.IsIconic(hwnd),
        })
        return True

    win32gui.EnumWindows(callback, None)
    return windows


def switch_to_window(hwnd):
    if win32gui.IsIconic(hwnd):
        win32gui.ShowWindow(hwnd, win32con.SW_RESTORE)

    foreground = win32gui.GetForegroundWindow()
    if foreground == hwnd:
        return True

    foreground_thread, _ = win32process.GetWindowThreadProcessId(foreground)
    target_thread, _ = win32process.GetWindowThreadProcessId(hwnd)

    if foreground_thread != target_thread:
        win32process.AttachThreadInput(target_thread, foreground_thread, True)
        win32gui.BringWindowToTop(hwnd)
        win32gui.SetForegroundWindow(hwnd)
        win32process.AttachThreadInput(target_thread, foreground_thread, False)
    else:
        win32gui.BringWindowToTop(hwnd)
        win32gui.SetForegroundWindow(hwnd)

    return win32gui.GetForegroundWindow() == hwnd


def print_window(label, info):
    print(label)
    print(f"  title: {info['title']}")
    print(f"  exe: {info['exe']}")
    print(f"  pid: {info['pid']}")
    print(f"  class: {info['class']}")
    print(f"  minimized: {info['iconic']}")
    print(f"  hwnd: {info['hwnd']}")


def prompt_window_index(total):
    prompt = f"\nSelect window number (1-{total}, Enter to skip): "
    value = input(prompt).strip()
    if not value:
        return None
    if not value.isdigit():
        return -1
    index = int(value)
    if index < 1 or index > total:
        return -1
    return index - 1


def main():
    if not is_windows():
        print("This tool only runs on Windows.")
        return 1

    active = get_active_window()
    print("Active window")
    print_window("", active)
    print("\nOpen windows")
    windows = list_open_windows()
    print(f"  count: {len(windows)}")
    for idx, info in enumerate(windows, start=1):
        print_window(f"{idx}.", info)

    if not windows:
        return 0

    selection = prompt_window_index(len(windows))
    if selection is None:
        return 0
    if selection == -1:
        print("Invalid selection.")
        return 1

    target = windows[selection]
    success = switch_to_window(target["hwnd"])
    if success:
        print("Switched to window.")
        return 0
    print("Failed to switch to window.")
    return 1

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
