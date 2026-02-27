import logging

from .platform import hotkeys
from .state_manager import StateManager

class HotkeyListener:
    def __init__(self, state_manager: StateManager, recording_hotkey: str,
                 auto_enter_hotkey: str = None, auto_enter_enabled: bool = True,
                 stop_with_modifier_enabled: bool = False, cancel_combination: str = None,
                 command_hotkey: str = None):
        self.state_manager = state_manager
        self.recording_hotkey = recording_hotkey
        self.auto_enter_hotkey = auto_enter_hotkey
        self.auto_enter_enabled = auto_enter_enabled
        self.stop_with_modifier_enabled = stop_with_modifier_enabled
        self.cancel_combination = cancel_combination
        self.command_hotkey = command_hotkey
        self.stop_modifier_hotkey = None
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

        if self.cancel_combination:
            hotkey_configs.append({
                'combination': self.cancel_combination,
                'callback': self._cancel_hotkey_pressed,
                'name': 'cancel'
            })

        if self.command_hotkey:
            hotkey_configs.append({
                'combination': self.command_hotkey,
                'callback': self._command_hotkey_pressed,
                'name': 'command'
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

        hotkey_configs.sort(key=self._get_hotkey_combination_specificity, reverse=True)

        self.hotkey_bindings = []
        for config in hotkey_configs:
            hotkey = config['combination'].lower().strip()
            self.hotkey_bindings.append([
                hotkey,
                config['callback'],
                config.get('release_callback') or None,
                False
            ])
            self.logger.info(f"Configured {config['name']} hotkey: {hotkey}")

        self.logger.info(f"Total hotkeys configured: {len(self.hotkey_bindings)}")

    def _get_hotkey_combination_specificity(self, hotkey_config: dict) -> int:
        combination = hotkey_config['combination'].lower()
        return len(combination.split('+'))

    def _standard_hotkey_pressed(self):
        self.logger.info(f"Standard hotkey pressed: {self.recording_hotkey}")

        self.modifier_key_released = False

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

        self.modifier_key_released = False

        self.state_manager.stop_recording(use_auto_enter=True)

    def _cancel_hotkey_pressed(self):
        self.logger.info(f"Cancel hotkey pressed: {self.cancel_combination}")
        self.state_manager.cancel_recording_hotkey_pressed()

    def _command_hotkey_pressed(self):
        self.logger.info(f"Command hotkey pressed: {self.command_hotkey}")
        self.modifier_key_released = False
        self.state_manager.start_command_recording()

    def _stop_modifier_hotkey_pressed(self):
        self.logger.debug(f"Stop-modifier hotkey pressed: {self.stop_modifier_hotkey}, modifier_released={self.modifier_key_released}")

        if self.modifier_key_released:
            self.logger.info(f"Stop-modifier hotkey activated: {self.stop_modifier_hotkey}")
            self.state_manager.stop_recording()
        else:
            self.logger.debug("Stop-modifier ignored - waiting for key release first")

    def _arm_stop_modifier_hotkey_on_release(self):
        self.logger.debug(f"Stop-modifier key released: {self.stop_modifier_hotkey}")
        self.modifier_key_released = True

    def _extract_first_modifier(self, hotkey_str: str) -> str:
        parts = hotkey_str.lower().split('+')
        if len(parts) > 1:
            return parts[0].strip()
        return None

    def start_listening(self):
        if self.is_listening:
            return

        try:
            hotkeys.register(self.hotkey_bindings)
            hotkeys.start()
            self.is_listening = True

        except Exception as e:
            self.logger.error(f"Failed to start hotkey listener: {e}")
            raise

    def stop_listening(self):
        if not self.is_listening:
            return

        try:
            hotkeys.stop()
            self.is_listening = False
            self.logger.info("Hotkey listener stopped")

        except Exception as e:
            self.logger.error(f"Error stopping hotkey listener: {e}")


    def change_hotkey_config(self, setting: str, value):
        valid_settings = ['recording_hotkey', 'auto_enter_hotkey', 'auto_enter_enabled', 'stop_with_modifier_enabled', 'cancel_combination', 'command_hotkey']

        if setting not in valid_settings:
            raise ValueError(f"Invalid setting '{setting}'. Valid options: {valid_settings}")

        old_value = getattr(self, setting)

        if old_value == value:
            return

        setattr(self, setting, value)
        self.logger.info(f"Changed {setting}: {old_value} -> {value}")

        self.stop_listening()
        self._setup_hotkeys()
        self.start_listening()

    def is_active(self) -> bool:
        return self.is_listening
