import logging
import threading
from typing import TYPE_CHECKING, Optional, Callable

from .streaming_recognizer import StreamingRecognizer

if TYPE_CHECKING:
    from .model_registry import ModelRegistry


class ContinuousStreamingRecognizer:
    def __init__(self,
                 recognizer: StreamingRecognizer,
                 result_callback: Optional[Callable[[str, bool], None]] = None):
        self.recognizer = recognizer
        self.result_callback = result_callback
        self.last_text = ""
        self._lock = threading.Lock()
        self.logger = logging.getLogger(__name__)

    def process_chunk(self, audio_chunk) -> None:
        if not self.recognizer.is_loaded():
            return

        self.recognizer.process_chunk(audio_chunk)
        self._check_results()

    def _check_results(self) -> None:
        text = self.recognizer.get_partial_result()
        is_endpoint = self.recognizer.is_endpoint()

        with self._lock:
            text_changed = text and text != self.last_text

            if is_endpoint:
                if text and self.result_callback:
                    self.result_callback(text, True)
                self.recognizer.reset()
                self.last_text = ""
            elif text_changed:
                self.last_text = text
                if self.result_callback:
                    self.result_callback(text, False)

    def reset(self) -> None:
        with self._lock:
            self.last_text = ""
            self.recognizer.reset()

    def set_recording_rate(self, rate: int) -> None:
        self.recognizer.set_recording_rate(rate)


class StreamingManager:
    def __init__(self,
                 streaming_enabled: bool = False,
                 streaming_model: str = "standard",
                 model_registry: "ModelRegistry" = None):
        self.streaming_enabled = streaming_enabled
        self.streaming_model = streaming_model
        self.model_registry = model_registry
        self.recognizer: Optional[StreamingRecognizer] = None
        self._model_loaded = False
        self.logger = logging.getLogger(__name__)

    def initialize(self) -> None:
        if not self.streaming_enabled:
            return

        if self._load_model():
            print("   ✓ Real-time speech recognition enabled...")

    def _load_model(self) -> bool:
        if self._model_loaded:
            return True

        self.recognizer = StreamingRecognizer(
            model_type=self.streaming_model,
            model_registry=self.model_registry
        )
        success = self.recognizer.load_model()

        if success:
            self._model_loaded = True
            self.recognizer.warmup()
            self.logger.info("Streaming STT model loaded successfully")
        else:
            self.recognizer = None
            self.logger.warning("Streaming STT model failed to load")

        return success

    def is_available(self) -> bool:
        return self.streaming_enabled and self._model_loaded and self.recognizer is not None

    def create_continuous_recognizer(self,
                                      result_callback: Optional[Callable[[str, bool], None]] = None
                                      ) -> Optional[ContinuousStreamingRecognizer]:
        if not self.is_available():
            return None

        return ContinuousStreamingRecognizer(
            recognizer=self.recognizer,
            result_callback=result_callback
        )
