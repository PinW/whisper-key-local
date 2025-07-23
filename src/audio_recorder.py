"""
Audio Recording Module

This module handles recording audio from your microphone using the sounddevice library.
Think of it like a digital tape recorder that can start and stop on command.

For beginners: This is where we capture the sound from your microphone and convert 
it into data that our computer can process.
"""

import logging
import numpy as np
import sounddevice as sd
import threading
from typing import Optional

class AudioRecorder:
    """
    A class that handles audio recording functionality
    
    Classes in Python are like blueprints - they define what something can do.
    This class knows how to record audio, start/stop recording, and store the audio data.
    """
    
    def __init__(self, sample_rate: int = 16000, channels: int = 1, dtype: str = "float32", 
                 max_duration: int = 30):
        """
        Initialize the audio recorder
        
        Parameters:
        - sample_rate: How many audio samples per second (16000 is good for speech)
        - channels: 1 for mono (single channel), 2 for stereo
        - dtype: Audio data type ("float32", "int16", etc.)
        - max_duration: Maximum recording length in seconds (0 = unlimited)
        
        For beginners: Think of sample_rate like photo resolution - higher means 
        better quality but bigger file size. 16000 is perfect for speech recognition.
        """
        self.sample_rate = sample_rate
        self.channels = channels
        self.dtype = dtype
        self.max_duration = max_duration
        self.is_recording = False
        self.audio_data = []  # This will store our recorded audio
        self.recording_thread = None
        self.logger = logging.getLogger(__name__)
        
        # Test if we can access the microphone
        self._test_microphone()
    
    def _test_microphone(self):
        """
        Test if we can access the microphone
        
        Private method (starts with _) - this is just for internal use
        """
        try:
            # Try to get list of audio devices
            devices = sd.query_devices()
            self.logger.info(f"Found {len(devices)} audio devices")
            
            # Find default input device (microphone)
            default_input = sd.query_devices(kind='input')
            self.logger.info(f"Default microphone: {default_input['name']}")
            
        except Exception as e:
            self.logger.error(f"Microphone test failed: {e}")
            raise RuntimeError("Could not access microphone. Please check your audio settings.")
    
    def start_recording(self):
        """
        Start recording audio from the microphone
        
        This creates a separate thread for recording so it doesn't block the main program.
        Threading is like having multiple workers doing different jobs at the same time.
        """
        if self.is_recording:
            self.logger.warning("Already recording!")
            return False
        
        self.logger.info("Starting audio recording...")
        self.is_recording = True
        self.audio_data = []  # Clear any previous recording
        
        # Start recording in a separate thread
        self.recording_thread = threading.Thread(target=self._record_audio)
        self.recording_thread.daemon = True  # Thread will close when main program closes
        self.recording_thread.start()
        
        return True
    
    def stop_recording(self) -> Optional[np.ndarray]:
        """
        Stop recording and return the recorded audio data
        
        Returns:
        - numpy array of audio data, or None if no recording was made
        
        For beginners: numpy arrays are like super-powered lists that are great 
        for handling large amounts of numerical data (like audio samples).
        """
        if not self.is_recording:
            self.logger.warning("Not currently recording!")
            return None
        
        self.logger.info("Stopping audio recording...")
        self.is_recording = False
        
        # Wait for recording thread to finish
        if self.recording_thread:
            self.recording_thread.join(timeout=2.0)  # Wait max 2 seconds
        
        if len(self.audio_data) == 0:
            self.logger.warning("No audio data recorded!")
            return None
        
        # Convert list of audio chunks into a single numpy array
        audio_array = np.concatenate(self.audio_data, axis=0)
        self.logger.info(f"Recorded {len(audio_array) / self.sample_rate:.2f} seconds of audio")
        
        return audio_array
    
    def _record_audio(self):
        """
        The actual recording function that runs in a separate thread
        
        This is the "worker" function that continuously captures audio while recording.
        """
        try:
            # Define callback function that gets called for each chunk of audio
            def audio_callback(indata, frames, time, status):
                """
                This function gets called automatically by sounddevice
                every time it has new audio data for us.
                
                indata: the audio data (what we want to save)
                """
                if status:
                    self.logger.warning(f"Audio callback status: {status}")
                
                # Save this chunk of audio data
                if self.is_recording:
                    self.audio_data.append(indata.copy())
            
            # Start the audio stream
            # This is like pressing "record" on a tape recorder
            with sd.InputStream(
                samplerate=self.sample_rate,
                channels=self.channels,
                callback=audio_callback,
                dtype=np.float32  # Type of numbers to use for audio data
            ):
                self.logger.info("Audio stream started")
                
                # Keep recording while is_recording is True
                while self.is_recording:
                    sd.sleep(100)  # Sleep for 100ms, then check again
                
                self.logger.info("Audio stream stopped")
                
        except Exception as e:
            self.logger.error(f"Error during audio recording: {e}")
            self.is_recording = False
    
    def get_recording_status(self) -> bool:
        """
        Check if we're currently recording
        
        Simple getter method - returns True if recording, False if not
        """
        return self.is_recording