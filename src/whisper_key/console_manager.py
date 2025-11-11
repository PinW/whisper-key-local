import win32console
import win32gui
import win32con
import win32process
import logging
import threading
import os


class ConsoleManager:
    def __init__(self, config: dict, is_executable_mode: bool = False):
        self.logger = logging.getLogger(__name__)
        self.config = config
        self.is_executable_mode = is_executable_mode
        self.console_handle = None
        self._lock = threading.Lock()

        try:
            self.console_handle = self.get_console_window()
            if self.console_handle:
                mode_name = "executable" if is_executable_mode else "CLI"
                self.logger.info(f"Console manager initialized in {mode_name} mode")
            else:
                self.logger.warning("No console window found")
        except Exception as e:
            self.logger.error(f"Failed to initialize console manager: {e}")

        if config.get('start_hidden', False) and is_executable_mode:
            import time
            time.sleep(2)
            self.hide_console()

    def get_console_window(self):
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

    def is_console_owned(self):
        if not self.console_handle:
            return False

        try:
            _, window_process_id = win32process.GetWindowThreadProcessId(self.console_handle)
            current_process_id = os.getpid()

            if window_process_id == current_process_id:
                self.logger.debug(f"Console window is owned by this process (PID: {current_process_id})")
                return True
            else:
                self.logger.debug(f"Console window owned by different process (PID: {window_process_id}, current: {current_process_id})")
                return False
        except Exception as e:
            self.logger.error(f"Failed to verify console ownership: {e}")
            return False

    def show_console(self):
        if not self.console_handle:
            self.logger.error("Cannot show console: no console window handle")
            return False

        with self._lock:
            try:
                if self.is_executable_mode:
                    win32gui.ShowWindow(self.console_handle, win32con.SW_RESTORE)
                    win32gui.SetForegroundWindow(self.console_handle)
                    self.logger.info("Console window shown and focused")
                else:
                    win32gui.SetWindowPos(
                        self.console_handle,
                        win32con.HWND_TOP,
                        0, 0, 0, 0,
                        win32con.SWP_NOSIZE | win32con.SWP_NOMOVE
                    )
                    self.logger.info("Terminal window brought to front")
                return True
            except Exception as e:
                self.logger.error(f"Failed to show/focus console: {e}")
                try:
                    win32gui.ShowWindow(self.console_handle, win32con.SW_RESTORE)
                    win32gui.SetForegroundWindow(self.console_handle)
                    self.logger.info("Console shown using fallback method")
                    return True
                except Exception as fallback_error:
                    self.logger.error(f"Fallback method also failed: {fallback_error}")
                    return False

    def hide_console(self):
        if not self.console_handle:
            self.logger.error("Cannot hide console: no console window handle")
            return False

        if not self.is_executable_mode:
            self.logger.warning("Cannot hide console in CLI mode")
            return False

        with self._lock:
            try:
                win32gui.ShowWindow(self.console_handle, win32con.SW_HIDE)
                self.logger.info("Console window hidden")
                return True
            except Exception as e:
                self.logger.error(f"Failed to hide console: {e}")
                return False

    def is_console_visible(self):
        if not self.console_handle:
            return False

        try:
            is_visible = win32gui.IsWindowVisible(self.console_handle)
            self.logger.debug(f"Console visibility state: {is_visible}")
            return is_visible
        except Exception as e:
            self.logger.error(f"Failed to check console visibility: {e}")
            return False
