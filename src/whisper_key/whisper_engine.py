import logging
import time
import threading
from typing import Optional, Callable

import numpy as np
from faster_whisper import WhisperModel


class WhisperEngine:
    def __init__(self,
                 model_size: str = "tiny",
                 device: str = "cpu",
                 compute_type: str = "int8",
                 language: str = None,
                 beam_size: int = 5,
                 vad_manager = None,
                 model_registry = None):

        self.model_size = model_size
        self.device = device
        self.compute_type = compute_type
        self.language = None if language == 'auto' else language
        self.beam_size = beam_size
        self.model = None
        self.logger = logging.getLogger(__name__)
        self.registry = model_registry

        self._loading_thread = None
        self._progress_callback = None

        self.vad_manager = vad_manager

        self._load_model()
    
    def _get_model_source(self, model_key: str) -> str:
        if self.registry:
            return self.registry.get_source(model_key)
        return model_key

    def _is_model_cached(self, model_key: str = None) -> bool:
        if model_key is None:
            model_key = self.model_size
        if self.registry:
            return self.registry.is_model_cached(model_key)
        return False

    def _load_model(self):
        try:
            print(f"🧠 Loading Whisper AI model [{self.model_size}]...")

            was_cached = self._is_model_cached()
            if not was_cached:
                print("Downloading model, this may take a few minutes....")

            model_source = self._get_model_source(self.model_size)
            self.model = WhisperModel(
                model_source,
                device=self.device,
                compute_type=self.compute_type
            )

            if not was_cached:
                print("\n")  # Workaround for download status bar misplacement

            print(f"   ✓ Whisper model [{self.model_size}] ready!")

        except Exception as e:
            self.logger.error(f"Failed to load Whisper model: {e}")
            raise
    
    def _load_model_async(self,
                          new_model_key: str,
                          progress_callback: Optional[Callable[[str], None]] = None):
        def _background_loader():
            try:
                if progress_callback:
                    progress_callback("Checking model cache...")

                old_model_size = self.model_size
                was_cached = self._is_model_cached(new_model_key)

                if progress_callback:
                    if was_cached:
                        progress_callback("Loading cached model...")
                    else:
                        progress_callback("Downloading model...")

                self.logger.info(f"Loading Whisper model: {new_model_key} (async)")

                model_source = self._get_model_source(new_model_key)
                new_model = WhisperModel(
                    model_source,
                    device=self.device,
                    compute_type=self.compute_type
                )

                self.model = new_model
                self.model_size = new_model_key
                self.logger.info(f"Whisper model [{new_model_key}] loaded successfully (async)")

                if progress_callback:
                    progress_callback("Model ready!")

            except Exception as e:
                self.model_size = old_model_size
                self.logger.error(f"Failed to load Whisper model async: {e}")
                if progress_callback:
                    progress_callback(f"Failed to load model: {e}")
                raise
            finally:
                self._loading_thread = None
                self._progress_callback = None

        if self._loading_thread and self._loading_thread.is_alive():
            self.logger.warning("Model loading already in progress, ignoring new request")
            return
        
        self._progress_callback = progress_callback
        self._loading_thread = threading.Thread(target=_background_loader, daemon=True)
        self._loading_thread.start()
    
    def is_loading(self) -> bool:
        return self._loading_thread is not None and self._loading_thread.is_alive()
    

    def transcribe_audio(self,
                         audio_data: np.ndarray) -> Optional[str]:
        if self.model is None:
            return None
        
        if audio_data is None or len(audio_data) == 0:
            self.logger.warning("No audio data to transcribe")
            return None
        
        try:
            speech_detected = True
            if self.vad_manager and self.vad_manager.is_available():
                speech_detected = self.vad_manager.check_audio_for_speech(audio_data)
            
            if not speech_detected:
                print("   ✗ No speech detected, skipping transcription")
                return None
                       
            start_time = time.time() # Time transcription for user feedback
            
            # Prep audio for faster-whisper
            if len(audio_data.shape) > 1:
                audio_data = audio_data.flatten()
            
            audio_data = audio_data.astype(np.float32)
            
            segments, info = self.model.transcribe(
                audio_data,
                beam_size=self.beam_size,
                language=self.language,
                condition_on_previous_text=False 
            )
            
            transcribed_text = ""
            for segment in segments:
                transcribed_text += segment.text
            
            transcribed_text = transcribed_text.strip()
            
            end_time = time.time()
            transcription_time = end_time - start_time
            print(f"   ✓ Transcription completed in {transcription_time:.1f} seconds")
            
            # Log some info about what we transcribed
            detected_language = info.language
            confidence = info.language_probability
            self.logger.info(f"Transcription complete. Language: {detected_language} (confidence: {confidence:.2f}) - Time: {transcription_time:.2f}s")
            self.logger.info(f"Transcribed text: '{transcribed_text}'")
            
            if transcribed_text:
                print(f"   ✓ Transcribed: '{transcribed_text}'")
                return transcribed_text
            else:
                self.logger.info("Transcription was empty")
                return None
                
        except Exception as e:
            self.logger.error(f"Transcription failed: {e}")
            return None
    
    
    def change_model(self,
                     new_model_size: str,
                     progress_callback: Optional[Callable[[str], None]] = None):
        
        if new_model_size == self.model_size:
            if progress_callback:
                progress_callback("Model already loaded")
            return
        
        self._load_model_async(new_model_size, progress_callback)
    