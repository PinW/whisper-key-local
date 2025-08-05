"""
Whisper Speech Recognition Engine

This module handles speech-to-text transcription using OpenAI's Whisper AI model.
It converts recorded audio into written text that can be pasted anywhere.

For beginners: This is the "brain" of our app - it listens to audio and figures 
out what words were spoken, like having a super-smart stenographer.
"""

import logging
import numpy as np
from faster_whisper import WhisperModel
from typing import Optional, Tuple, Callable
import tempfile
from src.utils import sanitize_for_logging
import os
import wave
import time
import threading

# TEN VAD for speech detection in short recordings
try:
    from ten_vad import TenVad
    TEN_VAD_AVAILABLE = True
except ImportError:
    TEN_VAD_AVAILABLE = False

class WhisperEngine:
    """
    A class that handles speech-to-text transcription using Whisper AI
    
    This class loads the Whisper AI model and converts audio data into text.
    """
    
    def __init__(self, model_size: str = "tiny", device: str = "cpu", compute_type: str = "int8", 
                 language: str = None, beam_size: int = 5, vad_enabled: bool = True):
        """
        Initialize the Whisper transcription engine
        
        Parameters:
        - model_size: Size of Whisper model ("tiny", "base", "small") - bigger = more accurate but slower
        - device: "cpu" or "cuda" (GPU) - we'll use CPU since it works everywhere
        - compute_type: "int8" for efficiency, "float16" for better quality
        - language: Language code (e.g., "en") or None for auto-detection
        - beam_size: Search beam size for transcription (higher = more accurate but slower)
        - vad_enabled: Enable TEN VAD pre-check for short recordings
        
        For beginners: 
        - "tiny" model is ~39MB and fastest
        - "base" model is ~74MB and more accurate
        - "small" model is ~244MB and very accurate but slower
        """
        self.model_size = model_size
        self.device = device
        self.compute_type = compute_type
        self.language = language
        self.beam_size = beam_size
        self.vad_enabled = vad_enabled
        self.model = None
        self.logger = logging.getLogger(__name__)
        
        # Model loading state tracking
        self._loading_thread = None
        self._loading_cancelled = False
        self._progress_callback = None
        
        # Initialize TEN VAD if available and enabled
        self.ten_vad = None
        if self.vad_enabled and TEN_VAD_AVAILABLE:
            try:
                self.ten_vad = TenVad()
                self.logger.info("TEN VAD initialized successfully")
            except Exception as e:
                self.logger.warning(f"Failed to initialize TEN VAD: {e}")
                self.ten_vad = None
        elif self.vad_enabled and not TEN_VAD_AVAILABLE:
            self.logger.warning("TEN VAD requested but not available, VAD pre-check disabled")
        
        # Load the model when we create this object
        self._load_model()
    
    def _get_cache_directory(self):
        """Get the HuggingFace cache directory path"""
        userprofile = os.getenv('USERPROFILE')
        if not userprofile:
            home = os.path.expanduser('~')
            userprofile = home
        
        cache_dir = os.path.join(userprofile, '.cache', 'huggingface', 'hub')
        return cache_dir
    
    def _is_model_cached(self):
        """Check if the current model is already cached"""
        cache_dir = self._get_cache_directory()
        model_folder = f"models--Systran--faster-whisper-{self.model_size}"
        return os.path.exists(os.path.join(cache_dir, model_folder))
    
    def _load_model(self):
        """
        Load the Whisper model into memory
        
        This downloads the model if it's not already on your computer, then loads 
        it into RAM so it's ready to transcribe audio quickly.
        """
        try:
            self.logger.info(f"Loading Whisper model: {self.model_size}")
            print(f"Loading Whisper AI model [{self.model_size}]...")
            
            # Check if model is already cached
            was_cached = self._is_model_cached()
            if not was_cached:
                print("Downloading model, this may take a few minutes....")
            
            # Create the Whisper model
            # This is where the AI "brain" gets loaded into memory
            self.model = WhisperModel(
                self.model_size,
                device=self.device,
                compute_type=self.compute_type
            )
            
            # Only show download message if model wasn't cached
            if not was_cached:
                print("\n")
            self.logger.info("Whisper model loaded successfully")
            print(f"Whisper model [{self.model_size}] ready!")
            
        except Exception as e:
            self.logger.error(f"Failed to load Whisper model: {e}")
            raise RuntimeError(f"Could not load Whisper model: {e}")
    
    def _load_model_async(self, new_model_size: str, progress_callback: Optional[Callable[[str], None]] = None):
        """
        Load the Whisper model asynchronously in a background thread
        
        This prevents the UI from freezing during model downloads.
        
        Parameters:
        - new_model_size: The model size to load
        - progress_callback: Optional callback function to report progress updates
        """
        def _background_loader():
            try:
                self._loading_cancelled = False
                
                if progress_callback:
                    progress_callback("Checking model cache...")
                
                # Check if model is already cached
                old_model_size = self.model_size
                self.model_size = new_model_size  # Temporarily set for cache check
                was_cached = self._is_model_cached()
                
                if progress_callback:
                    if was_cached:
                        progress_callback("Loading cached model...")
                    else:
                        progress_callback("Downloading model...")
                
                # Check for cancellation before starting heavy work
                if self._loading_cancelled:
                    self.model_size = old_model_size  # Restore original
                    return
                
                self.logger.info(f"Loading Whisper model: {new_model_size} (async)")
                
                # Create the Whisper model
                new_model = WhisperModel(
                    new_model_size,
                    device=self.device,
                    compute_type=self.compute_type
                )
                
                # Check for cancellation before applying changes
                if self._loading_cancelled:
                    self.model_size = old_model_size  # Restore original
                    return
                
                # Successfully loaded - apply changes
                self.model = new_model
                self.logger.info(f"Whisper model [{new_model_size}] loaded successfully (async)")
                
                if progress_callback:
                    progress_callback("Model ready!")
                
            except Exception as e:
                # Restore original model size on error
                self.model_size = old_model_size
                self.logger.error(f"Failed to load Whisper model async: {e}")
                if progress_callback:
                    progress_callback(f"Failed to load model: {e}")
                raise
            finally:
                # Clear loading state
                self._loading_thread = None
                self._progress_callback = None
        
        # Start background thread
        if self._loading_thread and self._loading_thread.is_alive():
            self.logger.warning("Model loading already in progress, cancelling previous load")
            self.cancel_model_loading()
        
        self._progress_callback = progress_callback
        self._loading_thread = threading.Thread(target=_background_loader, daemon=True)
        self._loading_thread.start()
    
    def cancel_model_loading(self):
        """
        Cancel any ongoing model loading operation
        """
        if self._loading_thread and self._loading_thread.is_alive():
            self.logger.info("Cancelling model loading...")
            self._loading_cancelled = True
            # Wait for thread to finish with timeout
            self._loading_thread.join(timeout=2.0)
            if self._loading_thread.is_alive():
                self.logger.warning("Model loading thread did not terminate cleanly")
    
    def is_loading(self) -> bool:
        """
        Check if a model is currently being loaded
        
        Returns:
        - True if model loading is in progress, False otherwise
        """
        return self._loading_thread is not None and self._loading_thread.is_alive()
    
    def _check_short_audio_for_speech(self, audio_data: np.ndarray) -> bool:
        """
        Check if short audio contains speech using TEN VAD
        Returns True if speech detected, False otherwise
        Note: Audio is always 16kHz (app standard), perfect for TEN VAD
        """
        duration = len(audio_data) / 16000  # Fixed 16kHz sample rate
        
        # Only check recordings 2.5 seconds or shorter
        if duration > 2.5:
            return True  # Assume longer recordings have speech
        
        # Skip VAD if not available or disabled
        if not self.ten_vad:
            return True  # Default to transcribing if VAD unavailable
        
        try:
            # Run TEN VAD check (audio already 16kHz - no conversion needed)
            result = self.ten_vad.predict(audio_data)
            speech_detected = any(segment['is_speech'] for segment in result)
            
            return speech_detected
        except Exception as e:
            self.logger.warning(f"TEN VAD check failed: {e}")
            return True  # Default to transcribing on VAD error
    
    def transcribe_audio(self, audio_data: np.ndarray, sample_rate: int = 16000) -> Optional[str]:
        """
        Convert audio data to text using Whisper AI
        
        Parameters:
        - audio_data: The recorded audio as a numpy array
        - sample_rate: How many audio samples per second the audio was recorded at
        
        Returns:
        - The transcribed text, or None if transcription failed
        
        For beginners: This is where the magic happens - the AI listens to your 
        audio and converts it to text, like a super-smart voice-to-text converter.
        """
        if self.model is None:
            self.logger.error("Whisper model not loaded!")
            return None
        
        if audio_data is None or len(audio_data) == 0:
            self.logger.warning("No audio data to transcribe")
            return None
        
        try:
            # TEN VAD pre-check for short recordings
            if not self._check_short_audio_for_speech(audio_data):
                self.logger.info("TEN VAD pre-check: No speech detected in short recording")
                print("No speech detected (recording too short/silent)")
                return None
            
            self.logger.info("Starting transcription...")
            print("Transcribing audio...")
            
            # Start timing the transcription process
            start_time = time.time()
            
            # Whisper expects audio as a 1D array (flat list of numbers)
            if len(audio_data.shape) > 1:
                audio_data = audio_data.flatten()
            
            # Make sure audio data is the right type (32-bit floating point numbers)
            audio_data = audio_data.astype(np.float32)
            
            # Transcribe the audio
            # This is where we ask the AI: "What words do you hear in this audio?"
            segments, info = self.model.transcribe(
                audio_data,
                beam_size=self.beam_size,  # How many possibilities to consider (configurable)
                language=self.language,  # Language setting from config (None = auto-detect)
                condition_on_previous_text=False  # Don't use context from previous transcriptions
            )
            
            # Collect all the transcribed text segments
            # Whisper breaks long audio into segments and transcribes each part
            transcribed_text = ""
            for segment in segments:
                transcribed_text += segment.text
            
            # Clean up the text (remove extra spaces, etc.)
            transcribed_text = transcribed_text.strip()
            
            # Calculate transcription time
            end_time = time.time()
            transcription_time = end_time - start_time
            
            # Show transcription time to user
            print(f"Transcription completed in {transcription_time:.1f} seconds")
            
            # Log some info about what we transcribed
            detected_language = info.language
            confidence = info.language_probability
            
            self.logger.info(f"Transcription complete. Language: {detected_language} (confidence: {confidence:.2f}) - Time: {transcription_time:.2f}s")
            self.logger.info(f"Transcribed text: '{sanitize_for_logging(transcribed_text)}'")
            
            if transcribed_text:
                print(f"Transcribed: '{transcribed_text}'")
                return transcribed_text
            else:
                self.logger.warning("Transcription was empty")
                print("No speech detected in audio")
                return None
                
        except Exception as e:
            self.logger.error(f"Transcription failed: {e}")
            print(f"Transcription error: {e}")
            return None
    
    def transcribe_file(self, audio_file_path: str) -> Optional[str]:
        """
        Transcribe audio from a file (for future use/testing)
        
        This method can transcribe audio files directly, which is useful for 
        testing with recorded audio files.
        """
        if self.model is None:
            self.logger.error("Whisper model not loaded!")
            return None
        
        try:
            self.logger.info(f"Transcribing file: {audio_file_path}")
            
            segments, info = self.model.transcribe(audio_file_path)
            
            transcribed_text = ""
            for segment in segments:
                transcribed_text += segment.text
            
            transcribed_text = transcribed_text.strip()
            
            self.logger.info(f"File transcription complete: '{sanitize_for_logging(transcribed_text)}'")
            return transcribed_text if transcribed_text else None
            
        except Exception as e:
            self.logger.error(f"File transcription failed: {e}")
            return None
    
    def get_model_info(self) -> dict:
        """
        Get information about the currently loaded model
        
        Returns a dictionary with model details for debugging/info purposes.
        """
        return {
            "model_size": self.model_size,
            "device": self.device,
            "compute_type": self.compute_type,
            "model_loaded": self.model is not None
        }
    
    def change_model(self, new_model_size: str, progress_callback: Optional[Callable[[str], None]] = None):
        """
        Switch to a different Whisper model size (for future customization)
        
        This allows users to switch between tiny/base/small models depending 
        on whether they want speed or accuracy.
        
        Parameters:
        - new_model_size: The new model size to switch to
        - progress_callback: Optional callback function to report progress updates
        """
        if new_model_size == self.model_size:
            self.logger.info(f"Already using model size: {new_model_size}")
            if progress_callback:
                progress_callback("Model already loaded")
            return
        
        self.logger.info(f"Switching from {self.model_size} to {new_model_size} model")
        
        # Use async loading to prevent UI blocking
        self._load_model_async(new_model_size, progress_callback)