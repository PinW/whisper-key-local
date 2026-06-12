import logging
import sys
import threading

_APP_TITLE = "Whisper Key"
_STATIC_SECONDS = 60.0
_DEFAULTS = {
    "idle":       "",
    "recording":  [["🔴", 1.5], ["⠀⠀", 1.0]],
    "processing": "",
}


def _compose_title(prefix) -> str:
    prefix = str(prefix)
    return f"{prefix} {_APP_TITLE}" if prefix else _APP_TITLE


class TerminalTitle:
    def __init__(self, frames_config: dict = None):
        self.logger = logging.getLogger(__name__)
        try:
            self._enabled = sys.stdout is not None and sys.stdout.isatty()
        except (ValueError, OSError):
            self._enabled = False
        self._frames = self._parse_frames(frames_config)
        self._state = "idle"
        self._frame_index = 0
        self._lock = threading.Lock()
        self._tick = threading.Event()
        self._stop = threading.Event()
        self._thread = None
        if self._enabled:
            self._emit(self._frames["idle"][0][0])

    def _parse_frames(self, frames_config: dict) -> dict:
        if not isinstance(frames_config, dict):
            frames_config = {}
        frames = {}
        for state, default_value in _DEFAULTS.items():
            value = frames_config.get(state, default_value)
            frames[state] = self._parse_state(state, value, default_value)
        return frames

    def _parse_state(self, state: str, value, default_value) -> list:
        if value is None or isinstance(value, (str, int, float)):
            return [(_compose_title(value if value is not None else ""), _STATIC_SECONDS)]
        parsed = []
        if isinstance(value, list):
            for entry in value:
                try:
                    prefix, seconds = entry
                    seconds = float(seconds)
                    if seconds > 0:
                        parsed.append((_compose_title(prefix), seconds))
                except (TypeError, ValueError):
                    pass
        if parsed:
            return parsed
        self.logger.warning(f"Invalid terminal_title frames for '{state}', using default")
        return self._parse_state(state, default_value, default_value)

    def start(self):
        if not self._enabled:
            return
        self._thread = threading.Thread(target=self._animation_loop, daemon=True, name="TerminalTitle")
        self._thread.start()

    def update_state(self, new_state: str):
        if not self._enabled:
            return
        with self._lock:
            if new_state == self._state:
                return
            self._state = new_state
            self._frame_index = 0
        self._tick.set()

    def stop(self):
        if not self._enabled:
            return
        self._stop.set()
        self._tick.set()
        if self._thread:
            self._thread.join(timeout=1.0)
        self._emit("")

    def _animation_loop(self):
        while not self._stop.is_set():
            with self._lock:
                frames = self._frames.get(self._state, self._frames["idle"])
                title, interval = frames[self._frame_index % len(frames)]
                self._frame_index += 1
            self._emit(title)
            self._tick.wait(timeout=interval)
            self._tick.clear()

    def _emit(self, title: str):
        try:
            sys.stdout.write(f"\033]0;{title}\007")
            sys.stdout.flush()
        except (ValueError, OSError):
            self._stop.set()
