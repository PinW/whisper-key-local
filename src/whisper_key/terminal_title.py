import sys
import threading

_FRAMES = {
    "idle":       [("🎤 Whisper Key", 60.0)],
    "recording":  [("🔴 Whisper Key", 1.0), ("   Whisper Key", 0.35)],
    "processing": [("•∙∙ Whisper Key", 0.2), ("∙•∙ Whisper Key", 0.2), ("∙∙• Whisper Key", 0.2), ("∙•∙ Whisper Key", 0.2)],
}


class TerminalTitle:
    def __init__(self):
        try:
            self._enabled = sys.stdout is not None and sys.stdout.isatty()
        except (ValueError, OSError):
            self._enabled = False
        self._state = "idle"
        self._frame_index = 0
        self._lock = threading.Lock()
        self._tick = threading.Event()
        self._stop = threading.Event()
        self._thread = None
        if self._enabled:
            self._emit(_FRAMES["idle"][0][0])

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
                frames = _FRAMES.get(self._state, _FRAMES["idle"])
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
