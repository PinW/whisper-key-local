import logging
import threading
import time
from typing import Optional, Callable

import numpy as np

from .audio_stream import AudioStreamManager, WHISPER_SAMPLE_RATE
from .voice_activity_detection import VadEvent


class AudioRecorder:
    THREAD_JOIN_TIMEOUT = 2.0

    def __init__(self,
                 audio_stream_manager: AudioStreamManager,
                 on_vad_event: Callable[[VadEvent], None],
                 max_duration: int = 30,
                 on_max_duration_reached: callable = None,
                 vad_manager=None,
                 streaming_manager=None,
                 on_streaming_result: Callable[[str, bool], None] = None):

        self.audio_stream_manager = audio_stream_manager
        self.max_duration = max_duration
        self.on_max_duration_reached = on_max_duration_reached
        self.is_recording = False
        self.audio_data = []
        self.recording_start_time = None
        self._max_duration_thread = None
        self.logger = logging.getLogger(__name__)

        self.vad_manager = vad_manager
        self.on_vad_event = on_vad_event
        self.continuous_vad = self._setup_continuous_vad_monitoring()

        self.streaming_manager = streaming_manager
        self.on_streaming_result = on_streaming_result
        self.continuous_streaming = self._setup_continuous_streaming()

    def _setup_continuous_vad_monitoring(self):
        if self.vad_manager.is_available():
            return self.vad_manager.create_continuous_detector(
                event_callback=self._handle_vad_event
            )
        return None

    def _setup_continuous_streaming(self):
        if self.streaming_manager and self.streaming_manager.is_available():
            continuous_streaming = self.streaming_manager.create_continuous_recognizer(
                result_callback=self._handle_streaming_result
            )
            recording_rate = self.audio_stream_manager.get_recording_sample_rate()
            continuous_streaming.set_recording_rate(recording_rate)
            return continuous_streaming
        return None

    def _handle_streaming_result(self, text: str, is_final: bool):
        if self.on_streaming_result:
            self.on_streaming_result(text, is_final)

    def _handle_vad_event(self, event: VadEvent):
        self.on_vad_event(event)

    def _on_audio_chunk(self, audio_data):
        if not self.is_recording:
            return

        self.audio_data.append(audio_data.copy())

        if self.continuous_vad:
            needs_resampling = self.audio_stream_manager.needs_resampling()
            if needs_resampling:
                chunk_16k = self.audio_stream_manager.resample_to_whisper(audio_data)
                self.continuous_vad.process_chunk(chunk_16k.reshape(-1, 1))
            else:
                self.continuous_vad.process_chunk(audio_data)

        if self.continuous_streaming:
            self.continuous_streaming.process_chunk(audio_data)

    def start_recording(self):
        if self.is_recording:
            return False

        try:
            self.logger.info("Starting audio recording...")
            self.is_recording = True
            self.audio_data = []
            self.recording_start_time = time.time()

            if self.continuous_vad:
                self.continuous_vad.reset()

            if self.continuous_streaming:
                self.continuous_streaming.reset()

            self.audio_stream_manager.add_consumer(self._on_audio_chunk)

            if self.max_duration > 0:
                self._max_duration_thread = threading.Thread(
                    target=self._monitor_max_duration, daemon=True
                )
                self._max_duration_thread.start()

            return True

        except Exception as e:
            self.logger.error(f"Failed to start audio recording: {e}")
            print("❌ Failed to start recording!")
            self.is_recording = False
            return False

    def stop_recording(self) -> Optional[np.ndarray]:
        if not self.is_recording:
            return None

        self.is_recording = False
        self.audio_stream_manager.remove_consumer(self._on_audio_chunk)

        if self._max_duration_thread:
            self._max_duration_thread.join(timeout=self.THREAD_JOIN_TIMEOUT)
            self._max_duration_thread = None

        return self._process_audio_data()

    def _process_audio_data(self) -> Optional[np.ndarray]:
        if len(self.audio_data) == 0:
            print("   ✗ No audio data recorded!")
            return None

        audio_array = np.concatenate(self.audio_data, axis=0)

        if self.audio_stream_manager.needs_resampling():
            recording_rate = self.audio_stream_manager.get_recording_sample_rate()
            self.logger.info(f"Resampling from {recording_rate} Hz to {WHISPER_SAMPLE_RATE} Hz")
            audio_array = self.audio_stream_manager.resample_to_whisper(audio_array)

        duration = self.get_audio_duration(audio_array)
        self.logger.info(f"Recorded {duration:.2f} seconds of audio")
        return audio_array

    def cancel_recording(self):
        if not self.is_recording:
            return

        self.is_recording = False
        self.audio_stream_manager.remove_consumer(self._on_audio_chunk)

        if self._max_duration_thread:
            self._max_duration_thread.join(timeout=self.THREAD_JOIN_TIMEOUT)
            self._max_duration_thread = None

        self.audio_data = []
        self.recording_start_time = None

    def _monitor_max_duration(self):
        while self.is_recording:
            if self.recording_start_time:
                elapsed_time = time.time() - self.recording_start_time
                if elapsed_time >= self.max_duration:
                    self.logger.info(f"Maximum recording duration of {self.max_duration}s reached")
                    print(f"⏰ Maximum recording duration of {self.max_duration}s reached - stopping recording")

                    self.is_recording = False
                    self.audio_stream_manager.remove_consumer(self._on_audio_chunk)
                    audio_data = self._process_audio_data()

                    if self.on_max_duration_reached:
                        self.on_max_duration_reached(audio_data)
                    return
            time.sleep(0.1)

    def get_recording_status(self) -> bool:
        return self.is_recording

    def get_audio_duration(self, audio_data: np.ndarray) -> float:
        if audio_data is None or len(audio_data) == 0:
            return 0.0
        return len(audio_data) / WHISPER_SAMPLE_RATE
