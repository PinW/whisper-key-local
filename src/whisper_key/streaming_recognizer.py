import logging
import os
from typing import Optional

import numpy as np
import soxr

SHERPA_SAMPLE_RATE = 16000

MODELS = {
    "standard": {
        "repo": "models--csukuangfj--sherpa-onnx-streaming-zipformer-en-20M-2023-02-17",
        "encoder": "encoder-epoch-99-avg-1.int8.onnx",
        "decoder": "decoder-epoch-99-avg-1.int8.onnx",
        "joiner": "joiner-epoch-99-avg-1.int8.onnx",
        "tokens": "tokens.txt",
    },
}


def get_hf_cache_path():
    userprofile = os.environ.get('USERPROFILE')
    if not userprofile:
        userprofile = os.path.expanduser('~')
    return os.path.join(userprofile, '.cache', 'huggingface', 'hub')


def get_model_path(model_type="standard"):
    model_info = MODELS.get(model_type)
    if not model_info:
        return None

    cache_base = get_hf_cache_path()
    model_dir = os.path.join(cache_base, model_info["repo"])

    if not os.path.exists(model_dir):
        return None

    snapshots_dir = os.path.join(model_dir, 'snapshots')
    if not os.path.exists(snapshots_dir):
        return None

    snapshots = os.listdir(snapshots_dir)
    if not snapshots:
        return None

    return os.path.join(snapshots_dir, snapshots[0]), model_info


class StreamingRecognizer:
    def __init__(self, model_type: str = "standard", recording_rate: int = 16000):
        self.logger = logging.getLogger(__name__)
        self.model_type = model_type
        self.recording_rate = recording_rate
        self.recognizer = None
        self.stream = None

    def load_model(self) -> bool:
        try:
            import sherpa_onnx
        except ImportError:
            self.logger.warning("sherpa-onnx not installed, streaming recognition unavailable")
            return False

        result = get_model_path(self.model_type)
        if not result:
            self.logger.warning(f"Streaming model '{self.model_type}' not found in HuggingFace cache")
            return False

        model_path, model_info = result

        encoder = os.path.join(model_path, model_info["encoder"])
        decoder = os.path.join(model_path, model_info["decoder"])
        joiner = os.path.join(model_path, model_info["joiner"])
        tokens = os.path.join(model_path, model_info["tokens"])

        for name, f in [("encoder", encoder), ("decoder", decoder), ("joiner", joiner), ("tokens", tokens)]:
            if not os.path.exists(f):
                self.logger.warning(f"Missing streaming model file: {name}")
                return False

        self.recognizer = sherpa_onnx.OnlineRecognizer.from_transducer(
            encoder=encoder,
            decoder=decoder,
            joiner=joiner,
            tokens=tokens,
            num_threads=4,
            sample_rate=SHERPA_SAMPLE_RATE,
            feature_dim=80,
            decoding_method="greedy_search",
            provider="cpu",
            enable_endpoint_detection=True,
            rule1_min_trailing_silence=2.4,
            rule2_min_trailing_silence=1.2,
            rule3_min_utterance_length=300,
        )

        self.stream = self.recognizer.create_stream()
        self.logger.info(f"Streaming recognizer loaded: {self.model_type}")
        return True

    def is_loaded(self) -> bool:
        return self.recognizer is not None and self.stream is not None

    def process_chunk(self, audio_chunk: np.ndarray) -> None:
        if not self.is_loaded():
            return

        samples = audio_chunk.flatten().astype(np.float32)

        if self.recording_rate != SHERPA_SAMPLE_RATE:
            samples = soxr.resample(samples, self.recording_rate, SHERPA_SAMPLE_RATE).astype(np.float32)

        self.stream.accept_waveform(SHERPA_SAMPLE_RATE, samples)

        while self.recognizer.is_ready(self.stream):
            self.recognizer.decode_stream(self.stream)

    def get_partial_result(self) -> str:
        if not self.is_loaded():
            return ""
        return self.recognizer.get_result(self.stream).strip()

    def is_endpoint(self) -> bool:
        if not self.is_loaded():
            return False
        return self.recognizer.is_endpoint(self.stream)

    def reset(self) -> None:
        if not self.is_loaded():
            return
        self.recognizer.reset(self.stream)

    def set_recording_rate(self, rate: int) -> None:
        self.recording_rate = rate
