import logging
import os
import shutil
import subprocess
import sys
import tempfile
import threading
import time
import wave
from pathlib import Path
from typing import Optional, Callable

import numpy as np


def _find_whisper_cli():
    env = os.environ.get("WHISPER_CPP_BINARY", "")
    if env and os.path.isfile(env):
        return env
    candidates = [
        Path(__file__).parent.parent.parent.parent / "tools" / "whisper.cpp" / "build" / "bin" / "whisper-cli.exe",
        Path.home() / "tools" / "whisper.cpp" / "build" / "bin" / "whisper-cli.exe",
    ]
    for p in candidates:
        if p.is_file() and os.access(p, os.X_OK):
            return str(p)
    which = shutil.which("whisper-cli")
    if which:
        return which
    which_exe = shutil.which("whisper-cli.exe")
    if which_exe:
        return which_exe
    return None


def _find_model_dir():
    env = os.environ.get("WHISPER_CPP_MODEL_DIR", "")
    if env:
        p = Path(env)
        if p.is_dir():
            return str(p)
    candidates = [
        Path.home() / "tools" / "whisper.cpp",
        Path.home() / "tools" / "whisper.cpp" / "models",
        Path(__file__).parent.parent.parent.parent / "tools" / "whisper.cpp",
    ]
    for p in candidates:
        if p.is_dir():
            return str(p)
    return None


_MODEL_FILE_MAP = {
    "tiny": "ggml-tiny.bin",
    "tiny.en": "ggml-tiny.en.bin",
    "base": "ggml-base.bin",
    "base.en": "ggml-base.en.bin",
    "small": "ggml-small.bin",
    "small.en": "ggml-small.en.bin",
    "medium": "ggml-medium.bin",
    "medium.en": "ggml-medium.en.bin",
    "large": "ggml-large.bin",
    "large-v3": "ggml-large-v3.bin",
    "large-v3-turbo": "ggml-large-v3-turbo.bin",
}


class WhisperCppEngine:

    def __init__(self,
                 model_key: str = "base",
                 device: str = "cpu",
                 compute_type: str = "int8",
                 language: str = None,
                 beam_size: int = 5,
                 initial_prompt: str = "",
                 hotwords: list = None,
                 strip_trailing_period: bool = False,
                 vad_manager=None,
                 model_registry=None,
                 log_transcriptions: bool = False,
                 binary_path: str = None,
                 model_dir: str = None):

        self.model_key = model_key
        self.language = None if language == 'auto' else language
        self.beam_size = beam_size
        self.initial_prompt = initial_prompt or None
        self.hotwords = ", ".join(hotwords) if hotwords else None
        self.strip_trailing_period = strip_trailing_period
        self.vad_manager = vad_manager
        self.registry = model_registry
        self.log_transcriptions = log_transcriptions
        self.logger = logging.getLogger(__name__)

        self._binary = binary_path or _find_whisper_cli()
        self._model_dir = model_dir or _find_model_dir()

        self._loading_thread = None
        self._progress_callback = None

        if not self._binary:
            raise RuntimeError(
                "whisper-cli not found. Set WHISPER_CPP_BINARY env var "
                "or install whisper.cpp (https://github.com/ggerganov/whisper.cpp)"
            )

        self.logger.info("WhisperCppEngine: binary=%s model_dir=%s", self._binary, self._model_dir)
        self._load_model()

    def _get_model_path(self, model_key: str = None):
        key = model_key or self.model_key
        filename = _MODEL_FILE_MAP.get(key, f"ggml-{key}.bin")

        if self._model_dir:
            candidate = os.path.join(self._model_dir, filename)
            if os.path.isfile(candidate):
                return candidate

        if self.registry:
            source = self.registry.get_source(key)
            if source and os.path.isfile(source):
                return source

        return filename

    def _is_model_cached(self, model_key: str = None):
        path = self._get_model_path(model_key)
        return os.path.isfile(path)

    def _load_model(self):
        model_path = self._get_model_path()
        print(f"[WhisperCpp] Loading model [{self.model_key}]...")
        if not os.path.isfile(model_path):
            print(f"[!] Model file not found: {model_path}")
            raise FileNotFoundError(
                f"Model file not found: {model_path}\n"
                f"Download models with: cd whisper.cpp && ./models/download-ggml-model.cmd {self.model_key}"
            )
        print(f"   OK WhisperCpp model [{self.model_key}] ready at {model_path}")
        print(f"   OK Binary: {self._binary}")

    def _load_model_async(self,
                          new_model_key: str,
                          progress_callback: Optional[Callable[[str], None]] = None):

        def _background_loader():
            try:
                if progress_callback:
                    progress_callback("Checking model cache...")

                if not self._is_model_cached(new_model_key):
                    if progress_callback:
                        progress_callback(f"Model '{new_model_key}' not found. Download it first.")
                    raise FileNotFoundError(f"Model '{new_model_key}' not available")

                if progress_callback:
                    progress_callback("Loading model...")

                old_model_key = self.model_key
                self.model_key = new_model_key
                self.logger.info("WhisperCpp model changed: %s -> %s", old_model_key, new_model_key)

                if progress_callback:
                    progress_callback("Model ready!")
            except Exception as e:
                self.logger.error("Failed to change model: %s", e)
                if progress_callback:
                    progress_callback(f"Failed: {e}")

        if self._loading_thread and self._loading_thread.is_alive():
            self.logger.warning("Model loading already in progress, ignoring new request")
            return

        self._progress_callback = progress_callback
        self._loading_thread = threading.Thread(target=_background_loader, daemon=True)
        self._loading_thread.start()

    def is_loading(self) -> bool:
        return self._loading_thread is not None and self._loading_thread.is_alive()

    def transcribe_audio(self, audio_data: np.ndarray) -> Optional[str]:
        if audio_data is None or len(audio_data) == 0:
            self.logger.warning("No audio data to transcribe")
            return None

        if self.vad_manager and self.vad_manager.is_available():
            speech_detected = self.vad_manager.check_audio_for_speech(audio_data)
            if not speech_detected:
                print("   X No speech detected, skipping transcription")
                return None

        start_time = time.time()
        tmp_path = None
        try:
            tmp_fd, tmp_path = tempfile.mkstemp(suffix=".wav", prefix="whisperkey_")
            os.close(tmp_fd)
            self._write_wav(tmp_path, audio_data)

            model_path = self._get_model_path()
            cmd = [
                self._binary,
                "-m", model_path,
                "-f", tmp_path,
                "-nt",
            ]
            if self.language:
                cmd.extend(["-l", self.language])
            if self.beam_size:
                cmd.extend(["-bs", str(self.beam_size)])

            self.logger.info("Running: %s", " ".join(cmd))
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                encoding="utf-8",
                errors="replace",
                timeout=120,
            )

            stderr = result.stderr.strip()
            if stderr:
                for line in stderr.splitlines():
                    if "ggml_vulkan" in line.lower() or "vulkan" in line.lower() or "amd" in line.lower() or "radeon" in line.lower():
                        self.logger.debug("Vulkan: %s", line)

            transcribed = result.stdout.strip()

            if transcribed and transcribed.startswith("["):
                lines = transcribed.splitlines()
                text_lines = []
                for line in lines:
                    if "]   " in line:
                        text_lines.append(line.split("]   ", 1)[1])
                    elif line.startswith("[") and "-->" in line:
                        continue
                    elif line.strip() and not line.startswith("whisper_"):
                        text_lines.append(line)
                transcribed = " ".join(text_lines).strip()

            if self.strip_trailing_period and transcribed.endswith('.'):
                transcribed = transcribed[:-1]

            elapsed = time.time() - start_time
            print(f"   OK Transcription completed in {elapsed:.1f}s")

            if self.log_transcriptions and transcribed:
                self.logger.info("Transcribed text: '%s'", transcribed)
            elif transcribed:
                self.logger.info("Transcribed %d chars", len(transcribed))

            if transcribed:
                print(f"   OK Transcribed: '{transcribed}'")
                return transcribed

            self.logger.info("Transcription was empty")
            return None

        except subprocess.TimeoutExpired:
            self.logger.error("Transcription timed out")
            return None
        except Exception as e:
            self.logger.error("Transcription failed: %s", e)
            return None
        finally:
            if tmp_path and os.path.isfile(tmp_path):
                try:
                    os.unlink(tmp_path)
                except OSError:
                    pass

    def change_model(self, new_model_key: str, progress_callback=None):
        if new_model_key == self.model_key:
            if progress_callback:
                progress_callback("Model already loaded")
            return
        self._load_model_async(new_model_key, progress_callback)

    @staticmethod
    def _write_wav(path: str, audio_data: np.ndarray):
        if len(audio_data.shape) > 1:
            audio_data = audio_data.ravel()
        if audio_data.dtype == np.float32:
            audio_data = (audio_data * 32767).clip(-32768, 32767).astype(np.int16)
        elif audio_data.dtype != np.int16:
            audio_data = audio_data.astype(np.int16)
        rate = 16000
        with wave.open(path, "wb") as wf:
            wf.setnchannels(1)
            wf.setsampwidth(2)
            wf.setframerate(rate)
            wf.writeframes(audio_data.tobytes())
