import logging
import threading
import time
from typing import Optional, Callable, List

import numpy as np
import sounddevice as sd
import soxr


WHISPER_SAMPLE_RATE = 16000
STREAM_CHUNK_SAMPLES = 512
STREAM_DTYPE = np.float32
WASAPI_REOPEN_DELAY = 0.05


class AudioStreamManager:
    def __init__(self, device=None):
        self.logger = logging.getLogger(__name__)
        self._consumers: List[Callable] = []
        self._consumers_lock = threading.Lock()
        self._stream: Optional[sd.InputStream] = None
        self._running = False

        self.device = None
        self.device_hostapi = None
        self.device_native_rate = WHISPER_SAMPLE_RATE
        self._resolve_device(device)

    def _resolve_device(self, device):
        if device == "default" or device is None:
            self.device = None
            self._resolve_hostapi(None)
        elif isinstance(device, int):
            try:
                device_info = sd.query_devices(device)
                if device_info.get('max_input_channels', 0) > 0:
                    self.device = device
                    self._resolve_hostapi(device_info)
                else:
                    self.logger.warning(f"Selected device {device} has no input channels; using default input instead")
                    self.device = None
                    self._resolve_hostapi(None)
            except Exception as e:
                self.logger.warning(f"Failed to load device {device}: {e}. Falling back to default input")
                self.device = None
                self._resolve_hostapi(None)
        else:
            self.logger.warning(f"Invalid device parameter: {device}, using default")
            self.device = None
            self._resolve_hostapi(None)

    def _resolve_hostapi(self, device_info):
        try:
            if device_info is None:
                device_info = sd.query_devices(kind='input')
            hostapi_index = device_info['hostapi']
            self.device_hostapi = sd.query_hostapis(hostapi_index)['name']
            self.device_native_rate = int(device_info['default_samplerate'])
        except Exception as e:
            self.logger.debug(f"Could not determine host API: {e}")
            self.device_hostapi = None
            self.device_native_rate = WHISPER_SAMPLE_RATE

    def needs_resampling(self) -> bool:
        return self.device_hostapi is not None and 'wasapi' in self.device_hostapi.lower()

    def get_recording_sample_rate(self) -> int:
        if self.needs_resampling():
            return self.device_native_rate
        return WHISPER_SAMPLE_RATE

    def resample_to_whisper(self, audio: np.ndarray) -> np.ndarray:
        orig_rate = self.get_recording_sample_rate()
        if orig_rate == WHISPER_SAMPLE_RATE or len(audio) == 0:
            return audio
        return soxr.resample(audio.flatten(), orig_rate, WHISPER_SAMPLE_RATE).astype(np.float32)

    def add_consumer(self, callback: Callable):
        with self._consumers_lock:
            if callback not in self._consumers:
                self._consumers.append(callback)

    def remove_consumer(self, callback: Callable):
        with self._consumers_lock:
            try:
                self._consumers.remove(callback)
            except ValueError:
                pass

    def start(self):
        if self._running:
            return

        self._test_audio_source()
        recording_rate = self.get_recording_sample_rate()

        if self.needs_resampling():
            blocksize = int(STREAM_CHUNK_SAMPLES * recording_rate / WHISPER_SAMPLE_RATE)
        else:
            blocksize = STREAM_CHUNK_SAMPLES

        if self.needs_resampling():
            time.sleep(WASAPI_REOPEN_DELAY)

        self._stream = sd.InputStream(
            samplerate=recording_rate,
            channels=1,
            callback=self._audio_callback,
            dtype=STREAM_DTYPE,
            blocksize=blocksize,
            device=self.device,
        )
        self._stream.start()
        self._running = True
        self.logger.info(f"Audio stream started (rate={recording_rate}, device={self.device})")

    def stop(self):
        if not self._running:
            return

        self._running = False
        if self._stream:
            try:
                self._stream.stop()
                self._stream.close()
            except Exception as e:
                self.logger.error(f"Error closing audio stream: {e}")
            self._stream = None
        self.logger.info("Audio stream stopped")

    def restart_stream(self, device=None):
        self.stop()
        if device is not None:
            self._resolve_device(device)
        self.start()

    def _audio_callback(self, audio_data, frames, time_info, status):
        if status:
            self.logger.debug(f"Audio stream status: {status}")

        with self._consumers_lock:
            consumers = list(self._consumers)

        for consumer in consumers:
            try:
                consumer(audio_data)
            except Exception as e:
                self.logger.error(f"Consumer error: {e}")

    def _test_audio_source(self):
        try:
            if self.device is not None:
                device_info = sd.query_devices(self.device)
                self.logger.info(f"Using device: {device_info['name']}")
            else:
                default_input = sd.query_devices(kind='input')
                self.logger.info(f"Default source: {default_input['name']}")
        except Exception as e:
            self.logger.error(f"Audio source test failed: {e}")
            raise

    def get_device_id(self) -> Optional[int]:
        if self.device is not None:
            return self.device
        return sd.query_devices(kind='input')['index']

    @staticmethod
    def get_available_audio_devices(host_filter: Optional[str] = None):
        try:
            all_devices = sd.query_devices()
            hostapis = sd.query_hostapis()
        except Exception as e:
            logging.getLogger(__name__).error(f"Failed to enumerate audio devices: {e}")
            return []

        devices = []
        host_filter_lower = host_filter.lower() if host_filter else None

        for idx, device in enumerate(all_devices):
            if device.get('max_input_channels', 0) <= 0:
                continue

            hostapi_index = device['hostapi']
            hostapi_info = hostapis[hostapi_index]
            hostapi_name = hostapi_info['name']

            if host_filter_lower and hostapi_name.lower() != host_filter_lower:
                continue

            devices.append({
                'id': idx,
                'name': device['name'],
                'input_channels': device['max_input_channels'],
                'sample_rate': device['default_samplerate'],
                'hostapi': hostapi_name,
            })

        return devices
