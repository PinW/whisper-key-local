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
from typing import Optional, Tuple
import tempfile
import os
import wave
import time

class WhisperEngine:
    """
    A class that handles speech-to-text transcription using Whisper AI
    
    This class loads the Whisper AI model and converts audio data into text.
    """
    
    def __init__(self, model_size: str = "tiny", device: str = "cpu", compute_type: str = "int8", 
                 language: str = None, beam_size: int = 5):
        """
        Initialize the Whisper transcription engine
        
        Parameters:
        - model_size: Size of Whisper model ("tiny", "base", "small") - bigger = more accurate but slower
        - device: "cpu" or "cuda" (GPU) - we'll use CPU since it works everywhere
        - compute_type: "int8" for efficiency, "float16" for better quality
        - language: Language code (e.g., "en") or None for auto-detection
        - beam_size: Search beam size for transcription (higher = more accurate but slower)
        
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
        self.model = None
        self.logger = logging.getLogger(__name__)
        
        # Load the model when we create this object
        self._load_model()
    
    def _load_model(self):
        """
        Load the Whisper model into memory
        
        This downloads the model if it's not already on your computer, then loads 
        it into RAM so it's ready to transcribe audio quickly.
        """
        try:
            self.logger.info(f"Loading Whisper model: {self.model_size}")
            print(f"Loading Whisper AI model ({self.model_size})...")
            print("First time may take a few minutes to download the model...")
            
            # Create the Whisper model
            # This is where the AI "brain" gets loaded into memory
            self.model = WhisperModel(
                self.model_size,
                device=self.device,
                compute_type=self.compute_type
            )
            
            self.logger.info("Whisper model loaded successfully")
            print("Whisper model ready!")
            
        except Exception as e:
            self.logger.error(f"Failed to load Whisper model: {e}")
            raise RuntimeError(f"Could not load Whisper model: {e}")
    
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
            self.logger.info(f"Transcribed text: '{transcribed_text}'")
            
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
            
            self.logger.info(f"File transcription complete: '{transcribed_text}'")
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
    
    def change_model(self, new_model_size: str):
        """
        Switch to a different Whisper model size (for future customization)
        
        This allows users to switch between tiny/base/small models depending 
        on whether they want speed or accuracy.
        """
        if new_model_size == self.model_size:
            self.logger.info(f"Already using model size: {new_model_size}")
            return
        
        self.logger.info(f"Switching from {self.model_size} to {new_model_size} model")
        
        self.model_size = new_model_size
        self._load_model()  # Reload with new model size