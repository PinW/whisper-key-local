import logging
import threading
import time
from collections import deque
from enum import Enum
from typing import Optional, Callable
import numpy as np

try:
    from ten_vad import TenVad
    HAS_TEN_VAD = True
except ImportError:
    TenVad = None
    HAS_TEN_VAD = False

SAMPLE_RATE = 16000  # Fixed 16kHz sample rate for TEN VAD and Whisper
VAD_HOP_DURATION_SEC = 0.016  # Fixed 256 samples at 16kHz
VAD_CHUNK_SIZE = 256

def _convert_audio_for_ten_vad(audio_data: np.ndarray) -> np.ndarray:
    # Flatten audio (TEN VAD expects 1D array)
    if len(audio_data.shape) > 1:
        audio_flat = audio_data.flatten()
    else:
        audio_flat = audio_data

    # Convert float32 to int16 for TEN VAD (range -32768 to 32767)
    if audio_flat.dtype == np.float32:
        audio_flat = np.clip(audio_flat, -1.0, 1.0)
        audio_int16 = (audio_flat * 32767).astype(np.int16)
    else:
        audio_int16 = audio_flat.astype(np.int16)

    return audio_int16

class VadState(Enum):
    SILENCE_COUNTING = "silence_counting"
    SPEECH_DETECTED = "speech_detected"
    TIMEOUT_TRIGGERED = "timeout_triggered"

class VadEvent(Enum):
    NO_EVENT = "no_event"
    SILENCE_TIMEOUT = "silence_timeout"

class VadManager:
    def __init__(self,
                 vad_precheck_enabled: bool = True,
                 vad_realtime_enabled: bool = False,
                 vad_onset_threshold: float = 0.7,
                 vad_offset_threshold: float = 0.55,
                 vad_min_speech_duration: float = 0.1,
                 vad_silence_timeout_seconds: float = 20.0):

        self.vad_precheck_enabled = vad_precheck_enabled
        self.vad_realtime_enabled = vad_realtime_enabled
        self.vad_onset_threshold = vad_onset_threshold
        self.vad_offset_threshold = vad_offset_threshold
        self.vad_min_speech_duration = vad_min_speech_duration
        self.vad_silence_timeout_seconds = vad_silence_timeout_seconds

        self.logger = logging.getLogger(__name__)

        self.ten_vad = self._check_and_init_ten_vad()

    def _check_and_init_ten_vad(self):
        if (self.vad_precheck_enabled or self.vad_realtime_enabled) and HAS_TEN_VAD:
            ten_vad = TenVad()
            self.logger.info("TEN VAD initialized for speech detection")
            return ten_vad
        elif (self.vad_precheck_enabled or self.vad_realtime_enabled) and not HAS_TEN_VAD:
            self.logger.warning("VAD enabled but ten-vad not available. VAD will be disabled.")
            return None
        else:
            return None

    def check_audio_for_speech(self, audio_data: np.ndarray) -> bool:
        duration = len(audio_data) / SAMPLE_RATE
        vad_start_time = time.time()

        try:
            audio_int16 = _convert_audio_for_ten_vad(audio_data)
            chunk_size = VAD_CHUNK_SIZE

            probabilities = []
            for i in range(0, len(audio_int16), chunk_size):
                chunk = audio_int16[i:i + chunk_size]

                # Make sure chunk meets TEN VAD 256-sample requirement
                if len(chunk) < chunk_size:
                    chunk = np.pad(chunk, (0, chunk_size - len(chunk)), mode='constant', constant_values=0)

                out_probability, _ = self.ten_vad.process(chunk)
                probabilities.append(out_probability)

            # Capture processing time for performance monitoring
            vad_time = (time.time() - vad_start_time) * 1000

            hysteresis = Hysteresis(high_threshold=self.vad_onset_threshold,
                                   low_threshold=self.vad_offset_threshold,
                                   frame_duration_sec=VAD_HOP_DURATION_SEC)
            speech_detected = hysteresis.detect_speech_in_probabilities(
                probabilities,
                self.vad_min_speech_duration
            )

            if speech_detected:
                self.logger.info(f"TEN VAD check: SPEECH detected (duration: {duration:.2f}s, processing: {vad_time:.1f}ms)")
            else:
                self.logger.info(f"TEN VAD check: SILENCE (duration: {duration:.2f}s, processing: {vad_time:.1f}ms)")

            return speech_detected

        except Exception as e:
            vad_time = (time.time() - vad_start_time) * 1000
            self.logger.warning(f"TEN VAD check failed after {vad_time:.1f}ms: {e}")
            return True

    def create_continuous_detector(self, event_callback: Optional[Callable[[VadEvent], None]] = None) -> Optional["ContinuousVoiceDetector"]:
        if not self.vad_realtime_enabled or not self.ten_vad:
            return None

        return ContinuousVoiceDetector(
            ten_vad=self.ten_vad,
            vad_onset_threshold=self.vad_onset_threshold,
            vad_offset_threshold=self.vad_offset_threshold,
            vad_silence_timeout_seconds=self.vad_silence_timeout_seconds,
            frame_duration_sec=VAD_HOP_DURATION_SEC,
            event_callback=event_callback
        )

    def is_available(self) -> bool:
        return self.ten_vad is not None

class Hysteresis:
    def __init__(self, high_threshold, low_threshold, frame_duration_sec):
        self.high_threshold = high_threshold
        self.low_threshold = low_threshold
        self.frame_duration_sec = frame_duration_sec
        self.speech_detected = False

    def detect_speech(self, probability):
        if self.speech_detected:
            self.speech_detected = probability > self.low_threshold
        else:
            self.speech_detected = probability > self.high_threshold
        return self.speech_detected

    def detect_speech_in_probabilities(self, probabilities, min_speech_duration):
        if not probabilities:
            return False

        min_frames_for_speech = int(min_speech_duration / self.frame_duration_sec)
        consecutive_speech_count = 0

        for prob in probabilities:
            if self.detect_speech(prob):
                consecutive_speech_count += 1
                if consecutive_speech_count >= min_frames_for_speech:
                    return True
            else:
                consecutive_speech_count = 0

        return False

class ContinuousVoiceDetector:
    def __init__(self, ten_vad, vad_onset_threshold, vad_offset_threshold,
                 vad_silence_timeout_seconds, frame_duration_sec,
                 event_callback: Optional[Callable[[VadEvent], None]] = None):
        self.ten_vad = ten_vad
        self.hysteresis = Hysteresis(high_threshold=vad_onset_threshold,
                                   low_threshold=vad_offset_threshold,
                                   frame_duration_sec=frame_duration_sec)
        self.silence_timeout_sec = vad_silence_timeout_seconds
        self.frame_duration_sec = frame_duration_sec
        self.silence_frame_count = 0
        self.frames_for_timeout = int(self.silence_timeout_sec / self.frame_duration_sec)
        self.probability_buffer = deque(maxlen=self.frames_for_timeout) # Control memory growth with circular buffer
        self.state = VadState.SILENCE_COUNTING
        self._lock = threading.Lock()
        self.event_callback = event_callback
        self.logger = logging.getLogger(__name__)

    def _dispatch_event(self, event: VadEvent):
        if self.event_callback:
            threading.Thread(target=self.event_callback, args=(event,), daemon=True).start()

    def process_chunk(self, audio_chunk: np.ndarray) -> VadEvent:
        if not self.ten_vad:
            return VadEvent.NO_EVENT

        try:
            audio_int16 = _convert_audio_for_ten_vad(audio_chunk)
            probability, _ = self.ten_vad.process(audio_int16)
            speech_detected = self.hysteresis.detect_speech(probability)
            self.probability_buffer.append(probability)
            return self._update_state(speech_detected)

        except Exception as e:
            self.logger.error(f"Error processing VAD chunk: {e}")
            return VadEvent.NO_EVENT

    def _update_state(self, speech_detected: bool) -> VadEvent:
        with self._lock:
            current_state = self.state
            event = VadEvent.NO_EVENT

            if current_state == VadState.SPEECH_DETECTED:
                if speech_detected:
                    self.silence_frame_count = 0
                else:
                    self.state = VadState.SILENCE_COUNTING
                    self.silence_frame_count = 1

            elif current_state == VadState.SILENCE_COUNTING:
                if speech_detected:
                    self.state = VadState.SPEECH_DETECTED
                    self.silence_frame_count = 0
                else:
                    self.silence_frame_count += 1
                    if self.silence_frame_count >= self.frames_for_timeout:
                        self.state = VadState.TIMEOUT_TRIGGERED
                        event = VadEvent.SILENCE_TIMEOUT

            elif current_state == VadState.TIMEOUT_TRIGGERED:
                pass

            if event != VadEvent.NO_EVENT:
                threading.Thread(target=self._dispatch_event, args=(event,), daemon=True).start()

            return event

    def reset(self):
        with self._lock:
            self.state = VadState.SILENCE_COUNTING
            self.silence_frame_count = 0
            self.probability_buffer.clear()
            self.hysteresis.speech_detected = False

    def get_state(self) -> VadState:
        with self._lock:
            return self.state

    def get_silence_duration(self) -> float:
        with self._lock:
            return self.silence_frame_count * self.frame_duration_sec
