import logging
import threading
import time
from abc import ABC, abstractmethod
from typing import Callable, Optional

import numpy as np

from .audio_stream import AudioStreamManager, WHISPER_SAMPLE_RATE, STREAM_CHUNK_SAMPLES
from .voice_activity_detection import VadManager, convert_audio_for_ten_vad

try:
    import openwakeword
    from openwakeword.model import Model as OwwModel
    HAS_OPENWAKEWORD = True
except ImportError:
    OwwModel = None
    HAS_OPENWAKEWORD = False

try:
    import pvporcupine
    HAS_PORCUPINE = True
except ImportError:
    pvporcupine = None
    HAS_PORCUPINE = False


class WakeWordEngine(ABC):
    @property
    @abstractmethod
    def chunk_samples(self) -> int:
        ...

    @abstractmethod
    def predict(self, audio_int16: np.ndarray) -> bool:
        ...

    @abstractmethod
    def reset(self):
        ...

    @abstractmethod
    def cleanup(self):
        ...


class OpenWakeWordEngine(WakeWordEngine):
    CHUNK_SAMPLES = 1280

    def __init__(self, model_paths=None, threshold: float = 0.5):
        self.threshold = threshold
        self.logger = logging.getLogger(__name__)

        if not HAS_OPENWAKEWORD:
            raise ImportError("openwakeword is not installed")

        inference_framework = "onnx"
        kwargs = {"inference_framework": inference_framework}
        if model_paths:
            kwargs["wakeword_models"] = model_paths

        self._model = OwwModel(**kwargs)
        self.logger.info(f"OpenWakeWord engine initialized (models: {list(self._model.models.keys())})")

    @property
    def chunk_samples(self) -> int:
        return self.CHUNK_SAMPLES

    def predict(self, audio_int16: np.ndarray) -> bool:
        prediction = self._model.predict(audio_int16)
        for model_name, score in prediction.items():
            if score >= self.threshold:
                self.logger.info(f"Wake word detected: {model_name} (score={score:.3f})")
                return True
        return False

    def reset(self):
        self._model.reset()

    def cleanup(self):
        pass


class PorcupineEngine(WakeWordEngine):
    CHUNK_SAMPLES = 512

    def __init__(self, access_key: str, keyword_paths=None, keywords=None, sensitivities=None):
        self.logger = logging.getLogger(__name__)

        if not HAS_PORCUPINE:
            raise ImportError("pvporcupine is not installed")

        kwargs = {"access_key": access_key}
        if keyword_paths:
            kwargs["keyword_paths"] = keyword_paths
        elif keywords:
            kwargs["keywords"] = keywords
        else:
            kwargs["keywords"] = ["porcupine"]

        if sensitivities:
            kwargs["sensitivities"] = sensitivities

        self._handle = pvporcupine.create(**kwargs)
        self.logger.info("Porcupine engine initialized")

    @property
    def chunk_samples(self) -> int:
        return self.CHUNK_SAMPLES

    def predict(self, audio_int16: np.ndarray) -> bool:
        result = self._handle.process(audio_int16)
        if result >= 0:
            self.logger.info(f"Porcupine wake word detected (index={result})")
            return True
        return False

    def reset(self):
        pass

    def cleanup(self):
        if self._handle:
            self._handle.delete()
            self._handle = None


class WakeWordManager:
    def __init__(self,
                 audio_stream_manager: AudioStreamManager,
                 vad_manager: VadManager,
                 engine: WakeWordEngine,
                 on_wake_word: Callable[[], None],
                 is_busy: Callable[[], bool],
                 cooldown_sec: float = 2.0,
                 vad_pre_filter: bool = True):

        self.audio_stream_manager = audio_stream_manager
        self.vad_manager = vad_manager
        self.engine = engine
        self.on_wake_word = on_wake_word
        self.is_busy = is_busy
        self.cooldown_sec = cooldown_sec
        self.vad_pre_filter = vad_pre_filter and vad_manager.is_available()

        self.logger = logging.getLogger(__name__)
        self._active = False
        self._last_trigger_time: float = 0
        self._chunk_accumulator: np.ndarray = np.array([], dtype=np.int16)

        self._onset_threshold = vad_manager.vad_onset_threshold
        self._speech_detected = False

    def _detect_speech_vad(self, audio_int16: np.ndarray) -> bool:
        try:
            probability, _ = self.vad_manager.ten_vad.process(audio_int16)
            if self._speech_detected:
                self._speech_detected = probability > self.vad_manager.vad_offset_threshold
            else:
                self._speech_detected = probability > self._onset_threshold
            return self._speech_detected
        except Exception:
            return True

    def activate(self):
        if self._active:
            return

        self._active = True
        self._chunk_accumulator = np.array([], dtype=np.int16)
        self._speech_detected = False
        self.engine.reset()
        self.audio_stream_manager.add_consumer(self._on_audio_chunk)
        self.logger.info("Wake word manager activated")
        print("   [WAKE WORD] listening for wake word...")

    def deactivate(self):
        if not self._active:
            return

        self._active = False
        self.audio_stream_manager.remove_consumer(self._on_audio_chunk)
        self._chunk_accumulator = np.array([], dtype=np.int16)
        self._speech_detected = False
        self.logger.info("Wake word manager deactivated")

    def _on_audio_chunk(self, audio_data):
        if not self._active:
            return

        if self.is_busy():
            return

        if self.audio_stream_manager.needs_resampling():
            chunk_16k = self.audio_stream_manager.resample_to_whisper(audio_data)
        else:
            chunk_16k = audio_data

        audio_int16 = convert_audio_for_ten_vad(chunk_16k)

        if self.vad_pre_filter and not self._detect_speech_vad(audio_int16):
            self._chunk_accumulator = np.array([], dtype=np.int16)
            return

        target_samples = self.engine.chunk_samples

        if len(audio_int16) == target_samples:
            self._process_engine_chunk(audio_int16)
        else:
            self._chunk_accumulator = np.concatenate([self._chunk_accumulator, audio_int16])
            while len(self._chunk_accumulator) >= target_samples:
                engine_chunk = self._chunk_accumulator[:target_samples]
                self._chunk_accumulator = self._chunk_accumulator[target_samples:]
                self._process_engine_chunk(engine_chunk)

    def _process_engine_chunk(self, audio_int16: np.ndarray):
        now = time.time()
        if now - self._last_trigger_time < self.cooldown_sec:
            return

        if self.engine.predict(audio_int16):
            self._last_trigger_time = now
            self.engine.reset()
            self._chunk_accumulator = np.array([], dtype=np.int16)
            self.logger.info("Wake word triggered")
            print("\n🔊 Wake word detected!")
            threading.Thread(target=self.on_wake_word, daemon=True).start()

    @property
    def active(self) -> bool:
        return self._active

    def cleanup(self):
        self.deactivate()
        self.engine.cleanup()
