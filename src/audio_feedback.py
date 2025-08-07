"""
Audio Feedback Module

Plays sound files for recording start/stop events to give users clear audio feedback.

For beginners: This is like having sound effects in a video game - when recording starts
you hear one sound file, when it stops you hear another sound file.
"""

import logging
import threading
import os
from typing import Optional
from .utils import resolve_asset_path

try:
    import winsound
    WINSOUND_AVAILABLE = True
except ImportError:
    # winsound is only available on Windows
    WINSOUND_AVAILABLE = False

class AudioFeedback:
    """
    Plays audio files for recording start/stop events
    
    This class loads and plays sound files to give users audio confirmation
    of recording state changes.
    """
    
    def __init__(self, config: dict):
        """
        Initialize the audio feedback system
        
        Parameters:
        - config: Dictionary containing audio feedback configuration
        
        Expected config structure:
        {
            'enabled': True,
            'start_sound': 'path/to/start.wav',
            'stop_sound': 'path/to/stop.wav'
        }
        """
        self.config = config
        self.enabled = config.get('enabled', True)
        self.logger = logging.getLogger(__name__)
        
        # Sound file paths - resolve relative paths for PyInstaller compatibility
        self.start_sound_path = resolve_asset_path(config.get('start_sound', ''))
        self.stop_sound_path = resolve_asset_path(config.get('stop_sound', ''))
        
        # Check if we can play sounds
        if not WINSOUND_AVAILABLE:
            self.logger.warning("winsound module not available - audio feedback disabled")
            self.enabled = False
        elif not self.enabled:
            self.logger.info("Audio feedback disabled by configuration")
        else:
            self.logger.info("Audio feedback enabled")
            self.logger.debug(f"Start sound: {self.start_sound_path}")
            self.logger.debug(f"Stop sound: {self.stop_sound_path}")
            
            # Validate sound files exist
            self._validate_sound_files()
    
    def _validate_sound_files(self):
        """
        Validate that configured sound files exist and are accessible
        """
        if self.start_sound_path and not os.path.isfile(self.start_sound_path):
            self.logger.warning(f"Start sound file not found: {self.start_sound_path}")
        
        if self.stop_sound_path and not os.path.isfile(self.stop_sound_path):
            self.logger.warning(f"Stop sound file not found: {self.stop_sound_path}")
    
    def _play_sound_file_async(self, file_path: str):
        """
        Play a sound file asynchronously (non-blocking)
        
        Parameters:
        - file_path: Path to the sound file to play
        
        For beginners: "Asynchronously" means the sound plays in the background
        without stopping our main program.
        """
        def play_sound():
            try:
                if not os.path.isfile(file_path):
                    self.logger.warning(f"Sound file not found: {file_path}")
                    return
                
                # Play the sound file
                # SND_FILENAME = play from file, SND_ASYNC = don't block
                winsound.PlaySound(file_path, winsound.SND_FILENAME | winsound.SND_ASYNC)
                
            except Exception as e:
                self.logger.warning(f"Failed to play sound file {file_path}: {e}")
        
        # Start sound in a separate thread so it doesn't block our main program
        sound_thread = threading.Thread(target=play_sound, daemon=True)
        sound_thread.start()
    
    def play_start_sound(self):
        """
        Play the recording start sound file
        
        This gives users audio confirmation that recording has begun.
        """
        if not self.enabled or not self.start_sound_path:
            return
        
        self.logger.debug(f"Playing recording start sound: {self.start_sound_path}")
        self._play_sound_file_async(self.start_sound_path)
    
    def play_stop_sound(self):
        """
        Play the recording stop sound file
        
        This gives users audio confirmation that recording has ended.
        """
        if not self.enabled or not self.stop_sound_path:
            return
        
        self.logger.debug(f"Playing recording stop sound: {self.stop_sound_path}")
        self._play_sound_file_async(self.stop_sound_path)
    
    def test_sounds(self):
        """
        Test both start and stop sound files
        
        This method is helpful for users to preview their configured sounds.
        """
        if not self.enabled:
            print("Audio feedback is disabled")
            return
        
        if not WINSOUND_AVAILABLE:
            print("Audio feedback not available on this system")
            return
        
        print("Testing start sound...")
        if self.start_sound_path:
            self.play_start_sound()
        else:
            print("No start sound configured")
        
        # Wait a moment between sounds
        import time
        time.sleep(1.0)
        
        print("Testing stop sound...")
        if self.stop_sound_path:
            self.play_stop_sound()
        else:
            print("No stop sound configured")
        
        print("Sound test complete!")
    
    def set_enabled(self, enabled: bool):
        """
        Enable or disable audio feedback
        
        Parameters:
        - enabled: True to enable sounds, False to disable
        """
        if not WINSOUND_AVAILABLE and enabled:
            self.logger.warning("Cannot enable audio feedback - winsound not available")
            return False
        
        old_state = self.enabled
        self.enabled = enabled
        
        if old_state != enabled:
            self.logger.info(f"Audio feedback {'enabled' if enabled else 'disabled'}")
        
        return True
    
    def update_config(self, new_config: dict):
        """
        Update the audio feedback configuration
        
        Parameters:
        - new_config: New configuration dictionary
        """
        self.config = new_config
        self.enabled = new_config.get('enabled', True) and WINSOUND_AVAILABLE
        
        self.start_sound_path = resolve_asset_path(new_config.get('start_sound', ''))
        self.stop_sound_path = resolve_asset_path(new_config.get('stop_sound', ''))
        
        self.logger.info("Audio feedback configuration updated")
        self.logger.debug(f"New start sound: {self.start_sound_path}")
        self.logger.debug(f"New stop sound: {self.stop_sound_path}")
        
        # Validate new sound files
        if self.enabled:
            self._validate_sound_files()
    
    def get_status(self) -> dict:
        """
        Get current status of audio feedback system
        
        Returns:
        - Dictionary with status information
        """
        return {
            'enabled': self.enabled,
            'winsound_available': WINSOUND_AVAILABLE,
            'start_sound_path': self.start_sound_path,
            'stop_sound_path': self.stop_sound_path,
            'start_sound_exists': os.path.isfile(self.start_sound_path) if self.start_sound_path else False,
            'stop_sound_exists': os.path.isfile(self.stop_sound_path) if self.stop_sound_path else False
        }