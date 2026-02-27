import logging

from .platform import hotkeys
from .state_manager import StateManager

class HotkeyListener:
    def __init__(self, state_manager: StateManager, recording_hotkey: str, stop_key: str,
                 auto_send_key: str = None, cancel_combination: str = None,
                 command_hotkey: str = None):
        self.state_manager = state_manager
        self.recording_hotkey = recording_hotkey
        self.stop_key = stop_key
        self.auto_send_key = auto_send_key
        self.cancel_combination = cancel_combination
        self.command_hotkey = command_hotkey
        self.keys_armed = True
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

        hotkey_configs.append({
            'combination': self.stop_key,
            'callback': self._stop_key_pressed,
            'release_callback': self._arm_keys_on_release,
            'name': 'stop'
        })

        if self.auto_send_key:
            hotkey_configs.append({
                'combination': self.auto_send_key,
                'callback': self._auto_send_key_pressed,
                'release_callback': self._arm_keys_on_release,
                'name': 'auto-send'
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
        self.keys_armed = False
        self.state_manager.start_recording()

    def _stop_key_pressed(self):
        self.logger.debug(f"Stop key pressed: {self.stop_key}, keys_armed={self.keys_armed}")

        if self.keys_armed:
            self.logger.info(f"Stop key activated: {self.stop_key}")
            self.state_manager.stop_recording()
        else:
            self.logger.debug("Stop key ignored - waiting for key release first")

    def _auto_send_key_pressed(self):
        self.logger.debug(f"Auto-send key pressed: {self.auto_send_key}, keys_armed={self.keys_armed}")

        if not self.state_manager.audio_recorder.get_recording_status():
            self.logger.debug("Auto-send key ignored - not currently recording")
            return

        if not self.keys_armed:
            self.logger.debug("Auto-send key ignored - waiting for key release first")
            return

        self.keys_armed = False

        if self.state_manager.is_transcription_recording() and self.state_manager.clipboard_manager.auto_paste:
            self.state_manager.stop_recording(use_auto_enter=True)
        else:
            self.state_manager.stop_recording()

    def _cancel_hotkey_pressed(self):
        self.logger.info(f"Cancel hotkey pressed: {self.cancel_combination}")
        self.state_manager.cancel_recording_hotkey_pressed()

    def _command_hotkey_pressed(self):
        self.logger.info(f"Command hotkey pressed: {self.command_hotkey}")
        self.keys_armed = False
        self.state_manager.start_command_recording()

    def _arm_keys_on_release(self):
        self.logger.debug("Key released - arming stop/auto-send keys")
        self.keys_armed = True

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
        valid_settings = ['recording_hotkey', 'stop_key', 'auto_send_key', 'cancel_combination', 'command_hotkey']

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
