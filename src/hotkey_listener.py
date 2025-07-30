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
    
    def __init__(self, state_manager: 'StateManager', hotkey: str, auto_enter_hotkey: str = None, auto_enter_enabled: bool = True, stop_with_modifier_enabled: bool = False):
        """
        Initialize the hotkey listener with support for multiple hotkeys
        
        Parameters:
        - state_manager: The StateManager that coordinates our app
        - hotkey: The standard key combination for recording (required)
        - auto_enter_hotkey: The auto-enter key combination (optional)
        - auto_enter_enabled: Whether the auto-enter hotkey is enabled (default: True)
        - stop_with_modifier_enabled: Whether to enable stop-only with first modifier key (default: False)
        
        For beginners: We pass the state_manager so this class can tell the rest 
        of the app when the hotkey is pressed.
        """
        self.state_manager = state_manager
        self.hotkey = hotkey
        self.auto_enter_hotkey = auto_enter_hotkey
        self.auto_enter_enabled = auto_enter_enabled
        self.stop_with_modifier_enabled = stop_with_modifier_enabled
        self.stop_modifier_hotkey = None  # Will be calculated from main hotkey
        self.auto_enter_modifier_hotkey = None  # Will be calculated from auto-enter hotkey
        self.modifier_key_released = True  # Track if modifier key has been released
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
        
        # Add stop-with-modifier hotkey if enabled
        if self.stop_with_modifier_enabled:
            self.stop_modifier_hotkey = self._extract_first_modifier(self.hotkey)
            if self.stop_modifier_hotkey:
                hotkey_configs.append({
                    'combination': self.stop_modifier_hotkey,
                    'callback': self._stop_modifier_hotkey_pressed,
                    'release_callback': self._stop_modifier_key_released,
                    'name': 'stop-modifier'
                })
        
        # Add auto-enter modifier hotkey if both features enabled
        if self.stop_with_modifier_enabled and self.auto_enter_enabled and self.auto_enter_hotkey:
            self.auto_enter_modifier_hotkey = self._extract_first_modifier(self.auto_enter_hotkey)
            if self.auto_enter_modifier_hotkey:
                # Check if auto-enter modifier is different from main stop modifier
                if self.auto_enter_modifier_hotkey != self.stop_modifier_hotkey:
                    hotkey_configs.append({
                        'combination': self.auto_enter_modifier_hotkey,
                        'callback': self._auto_enter_modifier_hotkey_pressed,
                        'name': 'auto-enter-modifier'
                    })
                    self.logger.info(f"Auto-enter stop-modifier enabled: {self.auto_enter_modifier_hotkey}")
                else:
                    self.logger.warning(f"⚠️ AUTO-ENTER HOTKEY DISABLED: Both main hotkey and auto-enter use the same modifier key '{self.auto_enter_modifier_hotkey}' with stop-with-modifier enabled. To re-enable auto-enter, use a different modifier key or turn off stop-with-modifier.")
                    self.auto_enter_modifier_hotkey = None  # Will use shared modifier
        
        # Sort by specificity (more modifiers = higher priority)
        hotkey_configs.sort(key=self._get_hotkey_specificity, reverse=True)
        
        # Convert to global_hotkeys format
        self.hotkey_bindings = []
        for config in hotkey_configs:
            formatted = self._convert_hotkey_to_global_format(config['combination'])
            
            # Check if this config has both press and release callbacks
            if 'release_callback' in config:
                # Format: [hotkey, press_callback, release_callback, actuate_on_partial_release]
                self.hotkey_bindings.append([formatted, config['callback'], config['release_callback'], False])
                self.logger.info(f"Configured {config['name']} hotkey with key-up detection: {config['combination']} -> {formatted}")
            else:
                # Standard format: [hotkey, press_callback, None, False] - press callback triggers on key down
                self.hotkey_bindings.append([formatted, config['callback'], None, False])
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
        
        # Disable stop-modifier until key is released (prevents immediate stopping)
        self.modifier_key_released = False
        
        try:
            # Tell the state manager to toggle recording (standard behavior)
            self.state_manager.toggle_recording()
            
        except Exception as e:
            self.logger.error(f"Error handling standard hotkey press: {e}")
    
    def _auto_enter_hotkey_pressed(self):
        """
        Called when the auto-enter hotkey is pressed
        
        AUTO-ENTER STOP-ONLY HOTKEY:
        - When not recording or auto-paste is disabled, the hotkey press is ignored
        - Provides automatic pasting with ENTER key press when stopping
        """
        self.logger.info(f"Auto-enter hotkey pressed: {self.auto_enter_hotkey}")
        
        # Check if currently recording (stop-only behavior)
        if not self.state_manager.audio_recorder.get_recording_status():
            self.logger.debug("Auto-enter hotkey ignored - not currently recording")
            return
        
        # Check if auto-paste is enabled (required for auto-enter functionality)
        if not self.state_manager.clipboard_config.get('auto_paste', False):
            self.logger.debug("Auto-enter hotkey ignored - auto-paste is disabled")
            return
        
        # Apply stop-modifier protection if enabled
        if self.stop_with_modifier_enabled and not self.modifier_key_released:
            self.logger.debug("Auto-enter hotkey ignored - waiting for modifier key release")
            return
        
        # Disable stop-modifier until key is released
        self.modifier_key_released = False
        
        try:
            # Stop recording with auto-enter behavior (stop-only)
            self.state_manager.stop_recording(use_auto_enter=True)
            
        except Exception as e:
            self.logger.error(f"Error handling auto-enter hotkey press: {e}")
    
    def _stop_modifier_hotkey_pressed(self):
        """
        Called when the stop-modifier hotkey is pressed (just the first modifier)
        
        This only stops recording if:
        1. Currently recording 
        2. The modifier key has been released since the last full hotkey press
        
        This prevents immediate stopping when the modifier is part of the start combination.
        """
        self.logger.debug(f"Stop-modifier hotkey pressed: {self.stop_modifier_hotkey}, modifier_released={self.modifier_key_released}")
        
        # Only stop if the modifier key has been released since last full hotkey press
        if self.modifier_key_released:
            self.logger.info(f"Stop-modifier hotkey activated: {self.stop_modifier_hotkey}")
            try:
                # Tell the state manager to stop recording only (no toggle behavior)
                self.state_manager.stop_recording()
                
            except Exception as e:
                self.logger.error(f"Error handling stop-modifier hotkey press: {e}")
        else:
            self.logger.debug("Stop-modifier ignored - waiting for key release first")
    
    def _stop_modifier_key_released(self):
        """
        Called when the stop-modifier key is released
        
        This enables the stop functionality after the key is released.
        """
        self.logger.debug(f"Stop-modifier key released: {self.stop_modifier_hotkey}")
        self.modifier_key_released = True
    
    def _auto_enter_modifier_hotkey_pressed(self):
        """
        Called when the auto-enter modifier hotkey is pressed (just the first modifier)
        
        AUTO-ENTER MODIFIER STOP-ONLY HOTKEY:
        - This is a simplified stop-only handler for auto-enter modifier keys
        - Only functions when recording is active and auto-paste is enabled
        - Doesn't need key-up protection because auto-enter hotkeys can never start recording
        - Provides automatic pasting with ENTER key press when stopping
        """
        self.logger.debug(f"Auto-enter modifier hotkey pressed: {self.auto_enter_modifier_hotkey}")
        
        # Check if currently recording (stop-only behavior)
        if not self.state_manager.audio_recorder.get_recording_status():
            self.logger.debug("Auto-enter modifier hotkey ignored - not currently recording")
            return
        
        # Check if auto-paste is enabled (required for auto-enter functionality)
        if not self.state_manager.clipboard_config.get('auto_paste', False):
            self.logger.debug("Auto-enter modifier hotkey ignored - auto-paste is disabled")
            return
            
        self.logger.info(f"Auto-enter modifier hotkey activated: {self.auto_enter_modifier_hotkey}")
        try:
            # Tell the state manager to stop recording with auto-enter behavior
            self.state_manager.stop_recording(use_auto_enter=True)
            
        except Exception as e:
            self.logger.error(f"Error handling auto-enter modifier hotkey press: {e}")
    
    
    def _extract_first_modifier(self, hotkey_str: str) -> str:
        """
        Extract the first modifier key from a hotkey combination
        
        Examples:
        - "ctrl+win" -> "ctrl"
        - "ctrl+shift+t" -> "ctrl"  
        - "alt+f4" -> "alt"
        - "win+space" -> "win"
        
        Parameters:
        - hotkey_str: The full hotkey combination string
        
        Returns:
        - String with just the first modifier, or None if no modifiers found
        """
        keys = hotkey_str.lower().split('+')
        modifiers = ['ctrl', 'shift', 'alt', 'win', 'windows', 'cmd', 'super']
        
        # Find the first modifier in the combination
        for key in keys:
            key = key.strip()
            if key in modifiers:
                self.logger.info(f"Extracted first modifier '{key}' from hotkey '{hotkey_str}'")
                return key
        
        self.logger.warning(f"No modifier found in hotkey '{hotkey_str}' - stop-with-modifier disabled")
        return None
    
    
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
            'win': 'window',
            'windows': 'window',
            'cmd': 'window',
            'super': 'window',
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
    
    
    def change_hotkey(self, new_hotkey: str = None, new_auto_enter_hotkey: str = None, auto_enter_enabled: bool = None, stop_with_modifier_enabled: bool = None):
        """
        Change the hotkey combinations (for future customization)
        
        This allows users to customize which keys trigger recording and auto-enter.
        
        Parameters:
        - new_hotkey: New standard recording hotkey (optional)
        - new_auto_enter_hotkey: New auto-enter hotkey (optional)  
        - auto_enter_enabled: Enable/disable auto-enter hotkey (optional)
        - stop_with_modifier_enabled: Enable/disable stop-with-modifier hotkey (optional)
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
            
        if stop_with_modifier_enabled is not None:
            changes.append(f"stop-with-modifier enabled: {self.stop_with_modifier_enabled} -> {stop_with_modifier_enabled}")
            self.stop_with_modifier_enabled = stop_with_modifier_enabled
        
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