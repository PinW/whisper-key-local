import logging
import threading
import time
from typing import Optional, Callable

import numpy as np
import sounddevice as sd
import soxr

from .voice_activity_detection import VadEvent, VAD_CHUNK_SIZE

class AudioRecorder:
    WHISPER_SAMPLE_RATE = 16000
    THREAD_JOIN_TIMEOUT = 2.0
    RECORDING_SLEEP_INTERVAL = 100
    STREAM_DTYPE = np.float32
    WASAPI_REOPEN_DELAY = 0.05
       
    def __init__(self,
                 on_vad_event: Callable[[VadEvent], None],
                 channels: int = 1,
                 dtype: str = "float32",
                 max_duration: int = 30,
                 on_max_duration_reached: callable = None,
                 vad_manager = None,
                 device = None):

        self.sample_rate = self.WHISPER_SAMPLE_RATE
        self.channels = channels
        self.dtype = dtype
        self.max_duration = max_duration
        self.on_max_duration_reached = on_max_duration_reached
        self.is_recording = False
        self.audio_data = []
        self.recording_thread = None
        self.recording_start_time = None
        self.logger = logging.getLogger(__name__)

        self.vad_manager = vad_manager
        self.on_vad_event = on_vad_event
        self.continuous_vad = self._setup_continuous_vad_monitoring()

        self.resolve_device(device)
        self._test_audio_source()

    def _setup_continuous_vad_monitoring(self):
        if self.vad_manager.is_available():
            continuous_vad = self.vad_manager.create_continuous_detector(
                event_callback=self._handle_vad_event
            )
            return continuous_vad
        else:
            return None

    def resolve_device(self, device):
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
            self.device_native_rate = self.WHISPER_SAMPLE_RATE

    def _needs_resampling(self) -> bool:
        return self.device_hostapi and 'wasapi' in self.device_hostapi.lower()

    def _get_recording_sample_rate(self) -> int:
        if self._needs_resampling():
            return self.device_native_rate
        return self.WHISPER_SAMPLE_RATE

    def _resample_audio(self, audio: np.ndarray, orig_rate: int, target_rate: int) -> np.ndarray:
        if orig_rate == target_rate or len(audio) == 0:
            return audio
        return soxr.resample(audio.flatten(), orig_rate, target_rate).astype(np.float32)

    def _handle_vad_event(self, event: VadEvent):
        self.on_vad_event(event)

    def _wait_for_thread_finish(self):
        if self.recording_thread:
            self.recording_thread.join(timeout=self.THREAD_JOIN_TIMEOUT)
            if self.recording_thread.is_alive():
                self.logger.warning("Recording thread did not exit within timeout")
    
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

            self.recording_thread = threading.Thread(target=self._record_audio)
            self.recording_thread.daemon = True  # Thread will close when main program closes
            self.recording_thread.start()

            print("🎤 Recording started! Speak now...")
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
        self._wait_for_thread_finish()
        
        return self._process_audio_data()
    
    def _process_audio_data(self) -> Optional[np.ndarray]:
        if len(self.audio_data) == 0:
            print("   ✗ No audio data recorded!")
            return None

        audio_array = np.concatenate(self.audio_data, axis=0)

        if self._needs_resampling():
            recording_rate = self._get_recording_sample_rate()
            self.logger.info(f"Resampling from {recording_rate} Hz to {self.WHISPER_SAMPLE_RATE} Hz")
            audio_array = self._resample_audio(audio_array, recording_rate, self.WHISPER_SAMPLE_RATE)

        duration = self.get_audio_duration(audio_array)
        self.logger.info(f"Recorded {duration:.2f} seconds of audio")
        return audio_array
    
    def cancel_recording(self):
        if not self.is_recording:
            return
        
        self.is_recording = False
        self._wait_for_thread_finish()
        
        self.audio_data = []
        self.recording_start_time = None
    
    def _record_audio(self):
        try:
            recording_rate = self._get_recording_sample_rate()
            needs_resampling = self._needs_resampling()

            if needs_resampling:
                vad_blocksize = int(VAD_CHUNK_SIZE * recording_rate / self.WHISPER_SAMPLE_RATE)
            else:
                vad_blocksize = VAD_CHUNK_SIZE

            def audio_callback(audio_data, frames, _time, status):
                if self.is_recording:
                    self.audio_data.append(audio_data.copy())

                    if self.continuous_vad and frames == vad_blocksize:
                        if needs_resampling:
                            chunk_16k = self._resample_audio(audio_data, recording_rate, self.WHISPER_SAMPLE_RATE)
                            self.continuous_vad.process_chunk(chunk_16k.reshape(-1, 1))
                        else:
                            self.continuous_vad.process_chunk(audio_data)

                if status:
                    self.logger.debug(f"Audio callback status: {status}")

            blocksize = vad_blocksize if self.continuous_vad else None

            # WASAPI requires delay before reopening stream (OS-level async cleanup)
            if needs_resampling:
                time.sleep(self.WASAPI_REOPEN_DELAY)

            with sd.InputStream(samplerate=recording_rate,
                                channels=self.channels,
                                callback=audio_callback,
                                dtype=self.STREAM_DTYPE,
                                blocksize=blocksize,
                                device=self.device):

                while self.is_recording:
                    if self._check_max_duration_exceeded():
                        break

                    sd.sleep(self.RECORDING_SLEEP_INTERVAL)

        except Exception as e:
            self.logger.error(f"Error during audio recording: {e}")
            self.is_recording = False
    
    def _check_max_duration_exceeded(self) -> bool:
        if self.max_duration > 0 and self.recording_start_time:
            elapsed_time = time.time() - self.recording_start_time
            if elapsed_time >= self.max_duration:
                self.logger.info(f"Maximum recording duration of {self.max_duration}s reached")
                print(f"⏰ Maximum recording duration of {self.max_duration}s reached - stopping recording")
                
                self.is_recording = False
                audio_data = self._process_audio_data()
                
                if self.on_max_duration_reached:
                    self.on_max_duration_reached(audio_data)
                return True
        return False
    
    def get_recording_status(self) -> bool:
        return self.is_recording
    
    def get_audio_duration(self, audio_data: np.ndarray) -> float:
        if audio_data is None or len(audio_data) == 0:
            return 0.0
        return len(audio_data) / self.sample_rate

    def get_device_id(self) -> Optional[int]:
        if self.device is not None:
            return self.device
        default_device_id = sd.query_devices(kind='input')['index']
        return default_device_id

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
                'hostapi': hostapi_name
            })

        return devices
