"""
Audio Feedback Module

This module provides audio feedback for recording start/stop events to give users
clear indication of recording state changes.

For beginners: This is like adding sound effects to your app - when recording starts
you hear one sound, when it stops you hear another sound, so you always know what's happening.
"""

import logging
import threading
from typing import Optional

try:
    import winsound
    WINSOUND_AVAILABLE = True
except ImportError:
    # winsound is only available on Windows
    WINSOUND_AVAILABLE = False

class AudioFeedback:
    """
    A class that provides audio feedback for recording events
    
    This class plays different sounds when recording starts and stops,
    helping users understand when the microphone is active.
    """
    
    def __init__(self, config: dict):
        """
        Initialize the audio feedback system
        
        Parameters:
        - config: Dictionary containing audio feedback configuration
        
        For beginners: We pass in configuration so users can customize
        the sounds (or turn them off completely).
        """
        self.config = config
        self.enabled = config.get('enabled', True)
        self.logger = logging.getLogger(__name__)
        
        # Sound configuration
        self.start_sound = config.get('start_sound', {
            'frequency': 800,  # Higher pitch for start (Hz)
            'duration': 200    # Short beep (milliseconds)
        })
        
        self.stop_sound = config.get('stop_sound', {
            'frequency': 600,  # Lower pitch for stop (Hz) 
            'duration': 300    # Slightly longer beep (milliseconds)
        })
        
        # Check if we can play sounds
        if not WINSOUND_AVAILABLE:
            self.logger.warning("winsound module not available - audio feedback disabled")
            self.enabled = False
        elif not self.enabled:
            self.logger.info("Audio feedback disabled by configuration")
        else:
            self.logger.info("Audio feedback enabled")
            self.logger.debug(f"Start sound: {self.start_sound}")
            self.logger.debug(f"Stop sound: {self.stop_sound}")
    
    def _play_beep_async(self, frequency: int, duration: int):
        """
        Play a beep sound asynchronously (non-blocking)
        
        Parameters:
        - frequency: Sound frequency in Hz (higher = more high-pitched)
        - duration: How long to play the sound in milliseconds
        
        For beginners: "Asynchronously" means the sound plays in the background
        without stopping our main program. Like background music while you work.
        """
        def play_sound():
            try:
                winsound.Beep(frequency, duration)
            except Exception as e:
                self.logger.warning(f"Failed to play beep: {e}")
        
        # Start sound in a separate thread so it doesn't block our main program
        sound_thread = threading.Thread(target=play_sound, daemon=True)
        sound_thread.start()
    
    def play_start_sound(self):
        """
        Play the recording start sound
        
        This gives users audio confirmation that recording has begun.
        """
        if not self.enabled:
            return
        
        self.logger.debug("Playing recording start sound")
        self._play_beep_async(
            self.start_sound['frequency'], 
            self.start_sound['duration']
        )
    
    def play_stop_sound(self):
        """
        Play the recording stop sound
        
        This gives users audio confirmation that recording has ended.
        """
        if not self.enabled:
            return
        
        self.logger.debug("Playing recording stop sound")
        self._play_beep_async(
            self.stop_sound['frequency'], 
            self.stop_sound['duration']
        )
    
    def test_sounds(self):
        """
        Test both start and stop sounds (useful for configuration)
        
        This method is helpful for users to preview the sounds and
        adjust their preferences.
        """
        if not self.enabled:
            print("Audio feedback is disabled")
            return
        
        if not WINSOUND_AVAILABLE:
            print("Audio feedback not available on this system")
            return
        
        print("Testing start sound...")
        self.play_start_sound()
        
        # Wait a moment between sounds
        import time
        time.sleep(0.5)
        
        print("Testing stop sound...")
        self.play_stop_sound()
        
        print("Sound test complete!")
    
    def set_enabled(self, enabled: bool):
        """
        Enable or disable audio feedback
        
        Parameters:
        - enabled: True to enable sounds, False to disable
        
        This allows users to turn sounds on/off without restarting the app.
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
        
        This allows users to change sound settings without restarting.
        """
        self.config = new_config
        self.enabled = new_config.get('enabled', True) and WINSOUND_AVAILABLE
        
        self.start_sound = new_config.get('start_sound', {
            'frequency': 800,
            'duration': 200
        })
        
        self.stop_sound = new_config.get('stop_sound', {
            'frequency': 600,
            'duration': 300
        })
        
        self.logger.info("Audio feedback configuration updated")
        self.logger.debug(f"New start sound: {self.start_sound}")
        self.logger.debug(f"New stop sound: {self.stop_sound}")
    
    def get_status(self) -> dict:
        """
        Get current status of audio feedback system
        
        Returns:
        - Dictionary with status information
        
        Useful for debugging and displaying current settings to users.
        """
        return {
            'enabled': self.enabled,
            'winsound_available': WINSOUND_AVAILABLE,
            'start_sound': self.start_sound.copy(),
            'stop_sound': self.stop_sound.copy()
        }