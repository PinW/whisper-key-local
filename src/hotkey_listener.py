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
    from .state_manager import StateManager

class HotkeyListener:
    """
    A class that listens for global hotkey presses
    
    This class registers hotkeys with the operating system and responds when they're pressed.
    """
    
    def __init__(self, state_manager: 'StateManager', hotkey: str = "ctrl+shift+space", auto_enter_hotkey: str = None, auto_enter_enabled: bool = True):
        """
        Initialize the hotkey listener with support for multiple hotkeys
        
        Parameters:
        - state_manager: The StateManager that coordinates our app
        - hotkey: The standard key combination for recording (default: Ctrl+Shift+Space)
        - auto_enter_hotkey: The auto-enter key combination (default: None)
        - auto_enter_enabled: Whether the auto-enter hotkey is enabled
        
        For beginners: We pass the state_manager so this class can tell the rest 
        of the app when the hotkey is pressed. Now supports both standard and auto-enter hotkeys.
        """
        self.state_manager = state_manager
        self.hotkey = hotkey
        self.auto_enter_hotkey = auto_enter_hotkey
        self.auto_enter_enabled = auto_enter_enabled
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
        
        IMPORTANT: Hotkeys are automatically sorted by specificity (number of modifiers)
        so that more specific combinations (e.g., CTRL+SHIFT+X) take priority over
        less specific ones (e.g., CTRL+X) when they share the same base key.
        """
        # Collect all hotkey configurations
        hotkey_configs = []
        
        # Add standard recording hotkey
        hotkey_configs.append({
            'combination': self.hotkey,
            'callback': self._standard_hotkey_pressed,
            'name': 'standard'
        })
        
        # Add auto-enter hotkey if enabled and configured
        if self.auto_enter_enabled and self.auto_enter_hotkey:
            hotkey_configs.append({
                'combination': self.auto_enter_hotkey,
                'callback': self._auto_enter_hotkey_pressed,
                'name': 'auto-enter'
            })
        
        # Sort by specificity (more modifiers = higher priority)
        hotkey_configs.sort(key=self._get_hotkey_specificity, reverse=True)
        
        # Convert to global_hotkeys format
        self.hotkey_bindings = []
        for config in hotkey_configs:
            formatted = self._convert_hotkey_to_global_format(config['combination'])
            self.hotkey_bindings.append([formatted, None, config['callback'], False])
            self.logger.info(f"Configured {config['name']} hotkey: {config['combination']} -> {formatted}")
        
        self.logger.info(f"Total hotkeys configured: {len(self.hotkey_bindings)}")
    
    def _get_hotkey_specificity(self, hotkey_config: dict) -> int:
        """
        Calculate the specificity of a hotkey combination based on number of modifiers
        
        More modifiers = higher specificity = higher priority
        This ensures CTRL+SHIFT+` takes precedence over CTRL+`
        
        Parameters:
        - hotkey_config: Dictionary with 'combination' key
        
        Returns:
        - Integer representing specificity (higher = more specific)
        """
        combination = hotkey_config['combination'].lower()
        
        # Count modifier keys
        modifiers = ['ctrl', 'shift', 'alt', 'win', 'cmd', 'super']
        specificity = sum(1 for modifier in modifiers if modifier in combination)
        
        # Add base key count (usually 1, but accounts for complex combinations)
        keys = combination.split('+')
        base_keys = [key.strip() for key in keys if key.strip() not in modifiers]
        specificity += len(base_keys)
        
        return specificity
    
    def _standard_hotkey_pressed(self):
        """
        Called when the standard recording hotkey is pressed
        
        This triggers the normal toggle recording behavior.
        """
        self.logger.info(f"Standard hotkey pressed: {self.hotkey}")
        
        try:
            # Tell the state manager to toggle recording (standard behavior)
            self.state_manager.toggle_recording()
            
        except Exception as e:
            self.logger.error(f"Error handling standard hotkey press: {e}")
    
    def _auto_enter_hotkey_pressed(self):
        """
        Called when the auto-enter hotkey is pressed
        
        This triggers enhanced recording behavior with auto-paste and ENTER.
        """
        self.logger.info(f"Auto-enter hotkey pressed: {self.auto_enter_hotkey}")
        
        try:
            # Tell the state manager to toggle recording with auto-enter behavior
            self.state_manager.toggle_recording(auto_enter=True)
            
        except Exception as e:
            self.logger.error(f"Error handling auto-enter hotkey press: {e}")
    
    
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
    
    
    def change_hotkey(self, new_hotkey: str = None, new_auto_enter_hotkey: str = None, auto_enter_enabled: bool = None):
        """
        Change the hotkey combinations (for future customization)
        
        This allows users to customize which keys trigger recording and auto-enter.
        
        Parameters:
        - new_hotkey: New standard recording hotkey (optional)
        - new_auto_enter_hotkey: New auto-enter hotkey (optional)  
        - auto_enter_enabled: Enable/disable auto-enter hotkey (optional)
        """
        changes = []
        
        if new_hotkey is not None:
            changes.append(f"standard: {self.hotkey} -> {new_hotkey}")
            self.hotkey = new_hotkey
        
        if new_auto_enter_hotkey is not None:
            changes.append(f"auto-enter: {self.auto_enter_hotkey} -> {new_auto_enter_hotkey}")
            self.auto_enter_hotkey = new_auto_enter_hotkey
            
        if auto_enter_enabled is not None:
            changes.append(f"auto-enter enabled: {self.auto_enter_enabled} -> {auto_enter_enabled}")
            self.auto_enter_enabled = auto_enter_enabled
        
        if changes:
            self.logger.info(f"Changing hotkeys: {', '.join(changes)}")
            
            # Stop current listener
            self.stop_listening()
            
            # Update hotkey configuration
            self._setup_hotkeys()
            
            # Restart listener with new hotkeys
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