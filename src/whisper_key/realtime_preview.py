import logging
import threading
from typing import Optional, Callable

import numpy as np

from .audio_stream import AudioStreamManager, WHISPER_SAMPLE_RATE
from .whisper_engine import WhisperEngine


class RealtimePreview:
    def __init__(self,
                 whisper_engine: WhisperEngine,
                 audio_stream_manager: AudioStreamManager,
                 on_preview_text: Optional[Callable[[str], None]] = None,
                 preview_interval_sec: float = 1.5,
                 preview_max_audio_seconds: float = 30.0):

        self.whisper_engine = whisper_engine
        self.audio_stream_manager = audio_stream_manager
        self.on_preview_text = on_preview_text
        self.preview_interval_sec = preview_interval_sec
        self.preview_max_audio_seconds = preview_max_audio_seconds

        self._buffer_lock = threading.Lock()
        self._buffer = np.array([], dtype=np.float32)
        self._active = False
        self._timer: Optional[threading.Timer] = None
        self._max_samples = int(preview_max_audio_seconds * WHISPER_SAMPLE_RATE)
        self.logger = logging.getLogger(__name__)

    def activate(self):
        if self._active:
            return

        self._active = True
        with self._buffer_lock:
            self._buffer = np.array([], dtype=np.float32)

        self.audio_stream_manager.add_consumer(self._on_audio_chunk)
        self._schedule_next_preview()
        self.logger.info("Realtime preview activated")

    def deactivate(self):
        if not self._active:
            return

        self._active = False

        if self._timer:
            self._timer.cancel()
            self._timer = None

        self.audio_stream_manager.remove_consumer(self._on_audio_chunk)

        with self._buffer_lock:
            self._buffer = np.array([], dtype=np.float32)

        self.logger.info("Realtime preview deactivated")

    def _on_audio_chunk(self, audio_data):
        if not self._active:
            return

        chunk = audio_data.flatten().astype(np.float32)
        if self.audio_stream_manager.needs_resampling():
            chunk = self.audio_stream_manager.resample_to_whisper(chunk)

        with self._buffer_lock:
            self._buffer = np.concatenate([self._buffer, chunk])
            if len(self._buffer) > self._max_samples:
                self._buffer = self._buffer[-self._max_samples:]

    def _schedule_next_preview(self):
        if not self._active:
            return
        self._timer = threading.Timer(self.preview_interval_sec, self._run_preview)
        self._timer.daemon = True
        self._timer.start()

    def _run_preview(self):
        if not self._active:
            return

        try:
            with self._buffer_lock:
                if len(self._buffer) == 0:
                    return
                snapshot = self._buffer.copy()

            text = self.whisper_engine.transcribe_preview(snapshot)

            if text and self.on_preview_text and self._active:
                self.on_preview_text(text, False)

        except Exception as e:
            self.logger.error(f"Preview cycle failed: {e}")
        finally:
            self._schedule_next_preview()
