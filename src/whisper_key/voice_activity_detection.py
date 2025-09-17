import logging
import threading
from collections import deque
from enum import Enum
from typing import Optional, Callable
import numpy as np

class VadState(Enum):
    WAITING = "waiting"
    SPEECH_DETECTED = "speech_detected"
    SILENCE_COUNTING = "silence_counting"
    TIMEOUT_TRIGGERED = "timeout_triggered"

class VadEvent(Enum):
    NO_EVENT = "no_event"
    SPEECH_STARTED = "speech_started"
    SPEECH_ENDED = "speech_ended"
    SILENCE_TIMEOUT = "silence_timeout"

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
        self.state = VadState.WAITING
        self._lock = threading.Lock()
        self.event_callback = event_callback
        self.logger = logging.getLogger(__name__)

    def _dispatch_event(self, event: VadEvent):
        if self.event_callback:
            try:
                threading.Thread(target=self.event_callback, args=(event,), daemon=True).start()
            except Exception as e:
                self.logger.error(f"Error in VAD event callback: {e}")

    def process_chunk(self, audio_chunk: np.ndarray) -> VadEvent:
        if not self.ten_vad:
            return VadEvent.NO_EVENT

        try:
            probability, _ = self.ten_vad.process(audio_chunk)
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

            if current_state == VadState.WAITING:
                if speech_detected:
                    self.state = VadState.SPEECH_DETECTED
                    self.silence_frame_count = 0
                    event = VadEvent.SPEECH_STARTED

            elif current_state == VadState.SPEECH_DETECTED:
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
            self.state = VadState.WAITING
            self.silence_frame_count = 0
            self.probability_buffer.clear()
            self.hysteresis.speech_detected = False

    def get_state(self) -> VadState:
        with self._lock:
            return self.state

    def get_silence_duration(self) -> float:
        with self._lock:
            return self.silence_frame_count * self.frame_duration_sec