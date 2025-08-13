import logging
from global_hotkeys import register_hotkeys, start_checking_hotkeys, stop_checking_hotkeys
from typing import TYPE_CHECKING
from .utils import error_logging

# This import trick prevents circular imports (advanced concept)
if TYPE_CHECKING:
    from .state_manager import StateManager

class HotkeyListener:   
    def __init__(self, state_manager: 'StateManager', recording_hotkey: str, auto_enter_hotkey: str = None, auto_enter_enabled: bool = True, stop_with_modifier_enabled: bool = False):
        self.state_manager = state_manager
        self.recording_hotkey = recording_hotkey
        self.auto_enter_hotkey = auto_enter_hotkey
        self.auto_enter_enabled = auto_enter_enabled
        self.stop_with_modifier_enabled = stop_with_modifier_enabled
        self.stop_modifier_hotkey = None  # Will be calculated from recording_hotkey
        self.modifier_key_released = True
        self.is_listening = False
        self.logger = logging.getLogger(__name__)
        
        self._setup_hotkeys()
        
        self.start_listening()
    
    def _setup_hotkeys(self):
        hotkey_configs = []
        
        hotkey_configs.append({
            'combination': self.recording_hotkey,
            'callback': self._standard_hotkey_pressed,
            'name': 'standard'
        })
        
        if self.auto_enter_enabled and self.auto_enter_hotkey:
            hotkey_configs.append({
                'combination': self.auto_enter_hotkey,
                'callback': self._auto_enter_hotkey_pressed,
                'name': 'auto-enter'
            })
        
        if self.stop_with_modifier_enabled:
            self.stop_modifier_hotkey = self._extract_first_modifier(self.recording_hotkey)
            if self.stop_modifier_hotkey:
                hotkey_configs.append({
                    'combination': self.stop_modifier_hotkey,
                    'callback': self._stop_modifier_hotkey_pressed,
                    'release_callback': self._arm_stop_modifier_hotkey_on_release,
                    'name': 'stop-modifier'
                })
        
        # More modifiers = higher priority
        hotkey_configs.sort(key=self._get_hotkey_combination_specificity, reverse=True)
        
        self.hotkey_bindings = []
        for config in hotkey_configs:
            formatted_hotkey = self._convert_hotkey_to_global_format(config['combination'])
            
            # Setup for global-hotkeys
            # Expected format: [hotkey, press_callback, release_callback, actuate_on_partial_release]
            self.hotkey_bindings.append([
                                         formatted_hotkey,
                                         config['callback'],
                                         config.get('release_callback') or None,
                                         False])

            self.logger.info(f"Configured {config['name']} hotkey: {config['combination']} -> {formatted_hotkey}")
        
        self.logger.info(f"Total hotkeys configured: {len(self.hotkey_bindings)}")
    
    def _get_hotkey_combination_specificity(self, hotkey_config: dict) -> int:
        """
        Returns specificity score to ensure combos with more keys take priority
        """
        combination = hotkey_config['combination'].lower()
        return len(combination.split('+'))
    
    def _standard_hotkey_pressed(self):
        self.logger.info(f"Standard hotkey pressed: {self.recording_hotkey}")
        
        # Disable stop-modifier until key is released (prevents immediate stopping)
        self.modifier_key_released = False
        
        with error_logging("standard hotkey", self.logger):
            self.state_manager.toggle_recording()
    
    def _auto_enter_hotkey_pressed(self):
        self.logger.info(f"Auto-enter hotkey pressed: {self.auto_enter_hotkey}")
        
        if not self.state_manager.audio_recorder.get_recording_status():
            self.logger.debug("Auto-enter hotkey ignored - not currently recording")
            return
        
        if not self.state_manager.clipboard_manager.auto_paste:
            self.logger.debug("Auto-enter hotkey ignored - auto-paste is disabled")
            return
        
        if self.stop_with_modifier_enabled and not self.modifier_key_released:
            self.logger.debug("Auto-enter hotkey ignored - waiting for modifier key release")
            return
        
        # Disable stop-modifier until key is released
        self.modifier_key_released = False
        
        with error_logging("auto-enter hotkey", self.logger):
            self.state_manager.stop_recording(use_auto_enter=True)
    
    def _stop_modifier_hotkey_pressed(self):
        self.logger.debug(f"Stop-modifier hotkey pressed: {self.stop_modifier_hotkey}, modifier_released={self.modifier_key_released}")
        
        # Only stop if the modifier key has been released since last full hotkey press
        if self.modifier_key_released:
            self.logger.info(f"Stop-modifier hotkey activated: {self.stop_modifier_hotkey}")
            with error_logging("stop-modifier hotkey", self.logger):
                self.state_manager.stop_recording()
        else:
            self.logger.debug("Stop-modifier ignored - waiting for key release first")
    
    def _arm_stop_modifier_hotkey_on_release(self):
        self.logger.debug(f"Stop-modifier key released: {self.stop_modifier_hotkey}")
        self.modifier_key_released = True
        
    def _extract_first_modifier(self, hotkey_str: str) -> str:
        return hotkey_str.lower().split('+')[0].strip()
    
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
            changes.append(f"standard: {self.recording_hotkey} -> {new_hotkey}")
            self.recording_hotkey = new_hotkey
        
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
        return self.recording_hotkey
    
    def is_active(self) -> bool:
        """
        Check if the hotkey listener is currently active
        """
        return self.is_listening