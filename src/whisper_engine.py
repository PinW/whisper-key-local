import logging
import os
import time
import threading
from typing import Optional, Callable

import numpy as np
from faster_whisper import WhisperModel
from ten_vad import TenVad
from src.utils import OptionalComponent

class WhisperEngine:    
    MODEL_CACHE_PREFIX = "models--Systran--faster-whisper-"  # file prefix for hugging-face model
    SAMPLE_RATE = 16000  # Fixed 16kHz sample rate for TEN VAD and Whisper
    VAD_HOP_DURATION_SEC = 0.016  # Fixed 256 samples at 16kHz
    VAD_CHUNK_SIZE = 256  

    def __init__(self, 
                 model_size: str = "tiny", 
                 device: str = "cpu", 
                 compute_type: str = "int8", 
                 language: str = None, 
                 beam_size: int = 5, 
                 vad_enabled: bool = True,
                 vad_onset_threshold: float = 0.7,
                 vad_offset_threshold: float = 0.55,
                 vad_min_speech_duration: float = 0.1):
        
        self.model_size = model_size
        self.device = device
        self.compute_type = compute_type
        self.language = None if language == 'auto' else language
        self.beam_size = beam_size
        self.vad_enabled = vad_enabled
        self.vad_onset_threshold = vad_onset_threshold
        self.vad_offset_threshold = vad_offset_threshold
        self.vad_min_speech_duration = vad_min_speech_duration
        self.model = None
        self.logger = logging.getLogger(__name__)
        
        self._loading_thread = None
        self._progress_callback = None
        
        vad_instance = TenVad() if self.vad_enabled else None
        self.ten_vad = OptionalComponent(vad_instance)
        
        self._load_model()
    
    def _get_cache_directory(self):
        userprofile = os.getenv('USERPROFILE')
        if not userprofile:
            home = os.path.expanduser('~')
            userprofile = home
        
        cache_dir = os.path.join(userprofile, '.cache', 'huggingface', 'hub')
        return cache_dir
    
    def _is_model_cached(self, model_size=None):
        if model_size is None:
            model_size = self.model_size
        cache_dir = self._get_cache_directory()
        model_folder = f"{self.MODEL_CACHE_PREFIX}{model_size}"
        return os.path.exists(os.path.join(cache_dir, model_folder))
    
    def _load_model(self):
        try:
            print(f"🧠 Loading Whisper AI model [{self.model_size}]...")
            
            was_cached = self._is_model_cached()
            if not was_cached:
                print("Downloading model, this may take a few minutes....")
            
            self.model = WhisperModel(
                self.model_size,
                device=self.device,
                compute_type=self.compute_type
            )
            
            if not was_cached:
                print("\n") # Workaround for download status bar misplacement

            print(f"   ✓ Whisper model [{self.model_size}] ready!")
            
        except Exception as e:
            self.logger.error(f"Failed to load Whisper model: {e}")
            raise
    
    def _load_model_async(self,
                          new_model_size: str,
                          progress_callback: Optional[Callable[[str], None]] = None):
        def _background_loader():
            try:             
                if progress_callback:
                    progress_callback("Checking model cache...")
                
                old_model_size = self.model_size
                was_cached = self._is_model_cached(new_model_size)
                
                if progress_callback:
                    if was_cached:
                        progress_callback("Loading cached model...")
                    else:
                        progress_callback("Downloading model...")
                               
                self.logger.info(f"Loading Whisper model: {new_model_size} (async)")

                new_model = WhisperModel(
                    new_model_size,
                    device=self.device,
                    compute_type=self.compute_type
                )
                
                self.model = new_model
                self.logger.info(f"Whisper model [{new_model_size}] loaded successfully (async)")
                
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
    
    def _detect_speech_with_hysteresis(self,
                                       probabilities: list,
                                       onset: float = None,
                                       offset: float = None,
                                       min_duration: float = None) -> bool:
        if not probabilities:
            return False
        
        onset = onset or self.vad_onset_threshold
        offset = offset or self.vad_offset_threshold
        min_duration = min_duration or self.vad_min_speech_duration
            
        min_frames_for_speech = int(min_duration / self.VAD_HOP_DURATION_SEC)
        
        speech_state = False
        hysteresis_flags = []
        
        # Apply hysteresis to prevent "flickering"
        for prob in probabilities:
            if not speech_state and prob >= onset:
                speech_state = True
            elif speech_state and prob <= offset:
                speech_state = False
            hysteresis_flags.append(speech_state)
        
        consecutive_speech_count = 0
        
        for flag in hysteresis_flags:
            if flag:
                consecutive_speech_count += 1

                if consecutive_speech_count >= min_frames_for_speech:
                    return True  # Speech segment detected
            else:
                consecutive_speech_count = 0
        
        return False

    def _check_audio_for_speech(self, audio_data: np.ndarray) -> bool:
        duration = len(audio_data) / self.SAMPLE_RATE
        
        if not self.ten_vad:
            return True # Skip speech check, but still transcribe
        
        vad_start_time = time.time()
        
        try:
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
            
            chunk_size = self.VAD_CHUNK_SIZE
            
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
            
            # Apply hysteresis + consecutive frame detection
            speech_detected = self._detect_speech_with_hysteresis(probabilities)
            
            if speech_detected:
                self.logger.info(f"TEN VAD check: SPEECH detected (duration: {duration:.2f}s, processing: {vad_time:.1f}ms)")
            else:
                self.logger.info(f"TEN VAD check: SILENCE (duration: {duration:.2f}s, processing: {vad_time:.1f}ms)")
            
            return speech_detected
            
        except Exception as e:
            vad_time = (time.time() - vad_start_time) * 1000
            self.logger.warning(f"TEN VAD check failed after {vad_time:.1f}ms: {e}")
            return True
    
    def transcribe_audio(self,
                         audio_data: np.ndarray,
                         sample_rate: int = SAMPLE_RATE) -> Optional[str]:
        if self.model is None:
            return None
        
        if audio_data is None or len(audio_data) == 0:
            self.logger.warning("No audio data to transcribe")
            return None
        
        try:
            speech_detected = self._check_audio_for_speech(audio_data)
            
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
    