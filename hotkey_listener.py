"""
Global Hotkey Listener Module

This module detects when you press specific key combinations (like Ctrl+Shift+Space)
from anywhere on your computer, even when our app isn't the active window.

For beginners: This is like having a universal remote control - no matter what 
program you're using, pressing the special key combination will trigger our app.
"""

import logging
from global_hotkeys import register_hotkeys, start_checking_hotkeys, stop_checking_hotkeys
from typing import TYPE_CHECKING

# This import trick prevents circular imports (advanced concept)
if TYPE_CHECKING:
    from state_manager import StateManager

class HotkeyListener:
    """
    A class that listens for global hotkey presses
    
    This class registers hotkeys with the operating system and responds when they're pressed.
    """
    
    def __init__(self, state_manager: 'StateManager', hotkey: str = "ctrl+shift+space"):
        """
        Initialize the hotkey listener
        
        Parameters:
        - state_manager: The StateManager that coordinates our app
        - hotkey: The key combination to listen for (default: Ctrl+Shift+Space)
        
        For beginners: We pass the state_manager so this class can tell the rest 
        of the app when the hotkey is pressed.
        """
        self.state_manager = state_manager
        self.hotkey = hotkey
        self.is_listening = False
        self.logger = logging.getLogger(__name__)
        
        # Set up the hotkey mapping
        self._setup_hotkeys()
        
        # Start listening for hotkeys
        self.start_listening()
    
    def _setup_hotkeys(self):
        """
        Configure which hotkeys to listen for and what to do when pressed
        
        This creates a list of hotkey configurations in the format expected by
        the global_hotkeys library: ["key_combination", None, callback, False]
        """
        # Convert string format "ctrl+shift+space" to global_hotkeys format "control + shift + space"
        hotkey_formatted = self._convert_hotkey_to_global_format(self.hotkey)
        
        self.hotkey_bindings = [
            [hotkey_formatted, None, self._hotkey_pressed, False]
        ]
        
        self.logger.info(f"Configured hotkey: {self.hotkey} -> {hotkey_formatted}")
    
    def _hotkey_pressed(self):
        """
        This function gets called when our hotkey is pressed
        
        It's like the "button handler" - when someone presses the button (hotkey),
        this function decides what to do about it.
        """
        self.logger.info(f"Hotkey pressed: {self.hotkey}")
        
        try:
            # Tell the state manager to toggle recording
            # "Toggle" means if it's off, turn it on; if it's on, turn it off
            self.state_manager.toggle_recording()
            
        except Exception as e:
            self.logger.error(f"Error handling hotkey press: {e}")
    
    def start_listening(self):
        """
        Start listening for hotkey presses
        
        This registers our hotkeys with the operating system and starts the
        global hotkey checker thread.
        """
        if self.is_listening:
            self.logger.warning("Already listening for hotkeys!")
            return
        
        try:
            self.logger.info("Starting hotkey listener...")
            
            # Register our hotkeys with the global-hotkeys library
            register_hotkeys(self.hotkey_bindings)
            
            # Start the global hotkey checker
            start_checking_hotkeys()
            
            self.is_listening = True
            self.logger.info("Hotkey listener started successfully")
            
        except Exception as e:
            self.logger.error(f"Failed to start hotkey listener: {e}")
            raise RuntimeError(f"Could not start hotkey listener: {e}")
    
    def stop_listening(self):
        """
        Stop listening for hotkey presses
        
        This is important for cleanup when the app shuts down.
        """
        if not self.is_listening:
            return
        
        try:
            self.logger.info("Stopping hotkey listener...")
            
            # Stop the global hotkey checker
            stop_checking_hotkeys()
            
            self.is_listening = False
            self.logger.info("Hotkey listener stopped")
            
        except Exception as e:
            self.logger.error(f"Error stopping hotkey listener: {e}")
    
    def _convert_hotkey_to_global_format(self, hotkey_str: str) -> str:
        """
        Convert hotkey string format to global_hotkeys format
        
        Examples:
        - "ctrl+shift+space" -> "control + shift + space"
        - "alt+f4" -> "alt + f4"
        """
        # Mapping from common string formats to global_hotkeys format
        key_mapping = {
            'ctrl': 'control',
            'shift': 'shift',
            'alt': 'alt',
            'space': 'space',
            'enter': 'enter',
            'esc': 'escape'
        }
        
        keys = hotkey_str.lower().split('+')
        converted_keys = []
        
        for key in keys:
            key = key.strip()
            # Use mapping if available, otherwise use the key as-is
            converted_keys.append(key_mapping.get(key, key))
        
        # Join with ' + ' format expected by global_hotkeys
        return ' + '.join(converted_keys)
    
    
    def change_hotkey(self, new_hotkey: str):
        """
        Change the hotkey combination (for future customization)
        
        This allows users to customize which keys trigger the recording.
        """
        self.logger.info(f"Changing hotkey from {self.hotkey} to {new_hotkey}")
        
        # Stop current listener
        self.stop_listening()
        
        # Update hotkey
        self.hotkey = new_hotkey
        self._setup_hotkeys()
        
        # Restart listener with new hotkey
        self.start_listening()
    
    def get_current_hotkey(self) -> str:
        """
        Get the currently configured hotkey
        
        Simple getter method to see what hotkey is active.
        """
        return self.hotkey
    
    def is_active(self) -> bool:
        """
        Check if the hotkey listener is currently active
        """
        return self.is_listening