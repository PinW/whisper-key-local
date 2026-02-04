import logging
import os
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

        if not self.enabled:
            self.logger.info("Audio feedback disabled by configuration")
            print("   ✗ Audio feedback disabled")
        else:
            self._validate_sound_files()
            print("   ✓ Audio feedback enabled...")

    def _validate_sound_files(self):
        if self.start_sound_path and not os.path.isfile(self.start_sound_path):
            self.logger.warning(f"Start sound file not found: {self.start_sound_path}")

        if self.stop_sound_path and not os.path.isfile(self.stop_sound_path):
            self.logger.warning(f"Stop sound file not found: {self.stop_sound_path}")

        if self.cancel_sound_path and not os.path.isfile(self.cancel_sound_path):
            self.logger.warning(f"Cancel sound file not found: {self.cancel_sound_path}")

    def _play_sound_file_async(self, file_path: str):
        def play():
            try:
                playsound(file_path, block=False)
            except Exception as e:
                self.logger.warning(f"Failed to play sound file {file_path}: {e}")

        threading.Thread(target=play, daemon=True).start()

    def play_start_sound(self):
        if self.enabled:
            self._play_sound_file_async(self.start_sound_path)

    def play_stop_sound(self):
        if self.enabled:
            self._play_sound_file_async(self.stop_sound_path)

    def play_cancel_sound(self):
        if self.enabled:
            self._play_sound_file_async(self.cancel_sound_path)
