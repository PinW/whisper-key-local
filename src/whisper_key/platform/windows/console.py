import win32console
import win32gui
import win32con
import logging
import threading
import time

class ConsoleManager:
    def __init__(self, config: dict, is_executable_mode: bool = False):
        self.logger = logging.getLogger(__name__)
        self.config = config
        self.is_executable_mode = is_executable_mode
        self.console_handle = None
        self._lock = threading.Lock()

        try:
            self.console_handle = self._get_console_window()
        except Exception as e:
            self.logger.error(f"Failed to initialize console manager: {e}")

        self._hide_on_startup()

    def _get_console_window(self):
        try:
            handle = win32console.GetConsoleWindow()
            if handle:
                self.logger.debug(f"Console window handle: {handle}")
                return handle
            else:
                self.logger.warning("GetConsoleWindow returned null handle")
                return None
        except Exception as e:
            self.logger.error(f"Failed to get console window: {e}")
            return None

    def _hide_on_startup(self):
        if self.config.get('start_hidden', False) and self.is_executable_mode:
            time.sleep(2)
            self.hide_console()

    def show_console(self):
        with self._lock:
            try:
                win32gui.ShowWindow(self.console_handle, win32con.SW_HIDE)
                win32gui.ShowWindow(self.console_handle, win32con.SW_RESTORE)
                win32gui.SetForegroundWindow(self.console_handle)
                return True
            except Exception as e:
                self.logger.error(f"Failed to show/focus console: {e}")
                return False

    def hide_console(self):
        with self._lock:
            try:
                win32gui.ShowWindow(self.console_handle, win32con.SW_HIDE)
                return True
            except Exception as e:
                self.logger.error(f"Failed to hide console: {e}")
                return False
