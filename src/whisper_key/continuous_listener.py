import logging
import threading
import time
from collections import deque
from enum import Enum
from typing import Callable, Optional

import numpy as np

from .audio_stream import AudioStreamManager, WHISPER_SAMPLE_RATE, STREAM_CHUNK_SAMPLES
from .voice_activity_detection import convert_audio_for_ten_vad, VadManager


class ListenerState(Enum):
    IDLE = "idle"
    SPEECH_ACTIVE = "speech_active"
    POST_SPEECH = "post_speech"


class ContinuousListener:
    def __init__(self,
                 audio_stream_manager: AudioStreamManager,
                 vad_manager: VadManager,
                 on_speech_audio: Callable[[np.ndarray], None],
                 is_busy: Callable[[], bool],
                 pre_buffer_duration_sec: float = 0.3,
                 post_speech_silence_ms: int = 800,
                 max_speech_duration_sec: float = 60.0,
                 min_speech_duration_sec: float = 0.5):

        self.audio_stream_manager = audio_stream_manager
        self.vad_manager = vad_manager
        self.on_speech_audio = on_speech_audio
        self.is_busy = is_busy
        self.post_speech_silence_ms = post_speech_silence_ms
        self.max_speech_duration_sec = max_speech_duration_sec
        self.min_speech_duration_sec = min_speech_duration_sec

        self.logger = logging.getLogger(__name__)
        self._active = False
        self._state = ListenerState.IDLE

        chunk_duration_sec = STREAM_CHUNK_SAMPLES / WHISPER_SAMPLE_RATE
        pre_buffer_chunks = max(1, int(pre_buffer_duration_sec / chunk_duration_sec))
        self._pre_buffer: deque = deque(maxlen=pre_buffer_chunks)

        self._speech_chunks: list = []
        self._speech_start_time: Optional[float] = None
        self._silence_start_time: Optional[float] = None

        self._onset_threshold = vad_manager.vad_onset_threshold
        self._offset_threshold = vad_manager.vad_offset_threshold
        self._speech_detected = False

    def _detect_speech(self, probability: float) -> bool:
        if self._speech_detected:
            self._speech_detected = probability > self._offset_threshold
        else:
            self._speech_detected = probability > self._onset_threshold
        return self._speech_detected

    def activate(self):
        if self._active:
            return

        if not self.vad_manager.is_available():
            self.logger.warning("Cannot activate continuous listener: VAD not available")
            return

        self._active = True
        self._reset_state()
        self.audio_stream_manager.add_consumer(self._on_audio_chunk)
        self.logger.info("Continuous listener activated")
        print("   [CONTINUOUS] listening for speech...")

    def deactivate(self):
        if not self._active:
            return

        self._active = False
        self.audio_stream_manager.remove_consumer(self._on_audio_chunk)
        self._reset_state()
        self.logger.info("Continuous listener deactivated")

    def _reset_state(self):
        self._state = ListenerState.IDLE
        self._pre_buffer.clear()
        self._speech_chunks = []
        self._speech_start_time = None
        self._silence_start_time = None
        self._speech_detected = False

    def _get_vad_probability(self, audio_chunk: np.ndarray) -> Optional[float]:
        try:
            if self.audio_stream_manager.needs_resampling():
                chunk_16k = self.audio_stream_manager.resample_to_whisper(audio_chunk)
            else:
                chunk_16k = audio_chunk

            audio_int16 = convert_audio_for_ten_vad(chunk_16k)
            probability, _ = self.vad_manager.ten_vad.process(audio_int16)
            return probability
        except Exception as e:
            self.logger.error(f"VAD processing error: {e}")
            return None

    def _on_audio_chunk(self, audio_data):
        if not self._active:
            return

        if self.is_busy():
            if self._state != ListenerState.IDLE:
                self._reset_state()
            return

        chunk = audio_data.copy()
        probability = self._get_vad_probability(chunk)
        if probability is None:
            return

        is_speech = self._detect_speech(probability)
        now = time.time()

        if self._state == ListenerState.IDLE:
            self._pre_buffer.append(chunk)
            if is_speech:
                self._transition_to_speech(now)

        elif self._state == ListenerState.SPEECH_ACTIVE:
            self._speech_chunks.append(chunk)
            if not is_speech:
                self._state = ListenerState.POST_SPEECH
                self._silence_start_time = now
            elif now - self._speech_start_time >= self.max_speech_duration_sec:
                self.logger.info(f"Max speech duration ({self.max_speech_duration_sec}s) reached")
                self._finalize_speech()

        elif self._state == ListenerState.POST_SPEECH:
            self._speech_chunks.append(chunk)
            if is_speech:
                self._state = ListenerState.SPEECH_ACTIVE
                self._silence_start_time = None
            else:
                silence_elapsed_ms = (now - self._silence_start_time) * 1000
                if silence_elapsed_ms >= self.post_speech_silence_ms:
                    self._finalize_speech()

    def _transition_to_speech(self, now: float):
        self._state = ListenerState.SPEECH_ACTIVE
        self._speech_start_time = now
        self._silence_start_time = None
        self._speech_chunks = list(self._pre_buffer)
        self._pre_buffer.clear()
        self.logger.info("Continuous listener: speech started")

    def _finalize_speech(self):
        speech_chunks = self._speech_chunks

        self._state = ListenerState.IDLE
        self._speech_chunks = []
        self._speech_start_time = None
        self._silence_start_time = None
        self._speech_detected = False

        if not speech_chunks:
            return

        audio_array = np.concatenate(speech_chunks, axis=0)

        if self.audio_stream_manager.needs_resampling():
            audio_array = self.audio_stream_manager.resample_to_whisper(audio_array)

        duration = len(audio_array) / WHISPER_SAMPLE_RATE

        if duration < self.min_speech_duration_sec:
            self.logger.info(f"Discarding short speech segment ({duration:.2f}s < {self.min_speech_duration_sec}s)")
            return

        self.logger.info(f"Continuous listener: speech segment {duration:.2f}s")
        print(f"\n🎙️ Speech detected ({duration:.1f}s), transcribing...")
        threading.Thread(target=self.on_speech_audio, args=(audio_array,), daemon=True).start()

    @property
    def active(self) -> bool:
        return self._active

    @property
    def state(self) -> ListenerState:
        return self._state
