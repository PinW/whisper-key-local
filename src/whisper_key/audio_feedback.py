import logging
import os
import queue
import threading

from playsound3 import playsound

from .utils import resolve_asset_path


class AudioFeedback:
    def __init__(self, enabled=True, start_sound='', stop_sound='', cancel_sound=''):
        self.enabled = enabled
        self.logger = logging.getLogger(__name__)

        self.start_sound_path = resolve_asset_path(start_sound)
        self.stop_sound_path = resolve_asset_path(stop_sound)
        self.cancel_sound_path = resolve_asset_path(cancel_sound)

        self._sound_queue = queue.Queue()
        self._worker_thread = None
        self._stop_event = threading.Event()

        if not self.enabled:
            self.logger.info("Audio feedback disabled by configuration")
            print("   ✗ Audio feedback disabled")
        else:
            self._validate_sound_files()
            self._start_worker()
            print("   ✓ Audio feedback enabled...")

    def _validate_sound_files(self):
        if self.start_sound_path and not os.path.isfile(self.start_sound_path):
            self.logger.warning(f"Start sound file not found: {self.start_sound_path}")

        if self.stop_sound_path and not os.path.isfile(self.stop_sound_path):
            self.logger.warning(f"Stop sound file not found: {self.stop_sound_path}")

        if self.cancel_sound_path and not os.path.isfile(self.cancel_sound_path):
            self.logger.warning(f"Cancel sound file not found: {self.cancel_sound_path}")

    def _start_worker(self):
        self._worker_thread = threading.Thread(target=self._audio_worker, daemon=True)
        self._worker_thread.start()

    def _audio_worker(self):
        while not self._stop_event.is_set():
            try:
                file_path = self._sound_queue.get(timeout=0.5)
                if file_path is None:
                    break
                playsound(file_path, block=True)
            except queue.Empty:
                continue
            except Exception as e:
                self.logger.warning(f"Failed to play sound: {e}")

    def _play_sound_file_async(self, file_path: str):
        if file_path:
            self._sound_queue.put(file_path)

    def play_start_sound(self):
        if self.enabled:
            self._play_sound_file_async(self.start_sound_path)

    def play_stop_sound(self):
        if self.enabled:
            self._play_sound_file_async(self.stop_sound_path)

    def play_cancel_sound(self):
        if self.enabled:
            self._play_sound_file_async(self.cancel_sound_path)

    def shutdown(self):
        self._stop_event.set()
        self._sound_queue.put(None)
        if self._worker_thread and self._worker_thread.is_alive():
            self._worker_thread.join(timeout=2.0)
