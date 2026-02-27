import os
import logging
import platform
import shutil
from typing import Dict, Any, Optional
from io import StringIO

from ruamel.yaml import YAML

from .utils import resolve_asset_path, beautify_hotkey, get_user_app_data_path
from .platform import IS_MACOS, keyboard as platform_keyboard

def deep_merge_config(default_config: Dict[str, Any],
                      user_config: Dict[str, Any]) -> Dict[str, Any]:

    result = default_config.copy()

    for key, value in user_config.items():
        if key in result and isinstance(result[key], dict) and isinstance(value, dict):
            result[key] = deep_merge_config(result[key], value)
        else:
            result[key] = value

    return result


def _parse_platform_value(value: str) -> str:
    parts = value.split(' | macos:')
    default_value = parts[0].strip()
    macos_value = parts[1].strip() if len(parts) > 1 else default_value
    return macos_value if IS_MACOS else default_value


def _resolve_platform_values(config: Dict[str, Any]) -> Dict[str, Any]:
    for key, value in config.items():
        if isinstance(value, dict):
            _resolve_platform_values(value)
        elif isinstance(value, str) and ' | macos:' in value:
            config[key] = _parse_platform_value(value)
    return config


class ConfigManager:   
    def __init__(self, config_path: str = None, use_user_settings: bool = True):
        if config_path is None:
            config_path = resolve_asset_path("config.defaults.yaml")
        
        self.default_config_path = config_path
        self.use_user_settings = use_user_settings
        self.config = {}
        self.logger = logging.getLogger(__name__)
        self.validator = ConfigValidator(self.logger)
        
        self.config_path = self._determine_config_path(use_user_settings, config_path)
        
        self.config = self._load_config()
        self._print_config_status()

        self.logger.info("Configuration loaded successfully")
    
    def _determine_config_path(self, use_user_settings: bool, config_path: str) -> str:
        if use_user_settings:
            whisperkey_dir = get_user_app_data_path()
            self.user_settings_path = os.path.join(whisperkey_dir, 'user_settings.yaml')
            return self.user_settings_path
        else:
            return config_path
    
    
    def _is_user_config_empty(self) -> bool:
        try:
            with open(self.user_settings_path, 'r', encoding='utf-8') as f:
                yaml = YAML()
                content = yaml.load(f)
                return content is None or len(content) == 0
        except:
            return True
    
    def _ensure_user_settings_exist(self):
        user_settings_dir = os.path.dirname(self.user_settings_path)
        
        if not os.path.exists(user_settings_dir):
            os.makedirs(user_settings_dir, exist_ok=True)
        
        if not os.path.exists(self.user_settings_path) or self._is_user_config_empty():
            if os.path.exists(self.default_config_path):
                shutil.copy2(self.default_config_path, self.user_settings_path)
                self.logger.info(f"Created user settings from {self.default_config_path}")
            else:
                error_msg = f"Default config {self.default_config_path} not found - cannot create user settings"
                self.logger.error(error_msg)
                raise FileNotFoundError(error_msg)
    
    def _remove_unused_keys_from_user_config(self, user_config: Dict[str, Any], default_config: Dict[str, Any]):
        
        sections_to_remove = []
        
        for section, values in user_config.items():
            if section not in default_config:
                self.logger.info(f"Removed invalid config section: {section}")
                sections_to_remove.append(section)
            elif isinstance(values, dict) and isinstance(default_config[section], dict):
                keys_to_remove = []
                for key in values.keys():
                    if key not in default_config[section]:
                        self.logger.info(f"Removed invalid config key: {section}.{key}")
                        keys_to_remove.append(key)
                
                for key in keys_to_remove:
                    del values[key]
        
        for section in sections_to_remove:
            del user_config[section]
    
    def _load_config(self):

        default_config = self._load_default_config()
        
        if self.use_user_settings:
            self._ensure_user_settings_exist()

            try:
                yaml = YAML()
                with open(self.config_path, 'r', encoding='utf-8') as file:
                    user_config = yaml.load(file)
                
                self._remove_unused_keys_from_user_config(user_config, default_config)
                merged_config = deep_merge_config(default_config, user_config)
                resolved_config = _resolve_platform_values(merged_config)
                self.logger.info(f"Loaded user configuration from {self.config_path}")

                validated_config = self.validator.fix_config(resolved_config, default_config)
                self.config = validated_config
                
                self.save_config_to_user_settings_file()

                return validated_config
                    
            except Exception as e:
                if "YAML" in str(e):
                    self.logger.error(f"Error parsing user YAML config: {e}")
                else:
                    self.logger.error(f"Error loading user config file: {e}")
                
        self.logger.info(f"Using default configuration from {self.default_config_path}")
        return _resolve_platform_values(default_config)
    
    def _load_default_config(self) -> Dict[str, Any]:
        try:
            yaml = YAML()
            with open(self.default_config_path, 'r', encoding='utf-8') as file:
                default_config = yaml.load(file)
            
            if default_config:
                self.logger.info(f"Loaded default configuration from {self.default_config_path}")
                return default_config
            else:
                self.logger.error(f"Default config file {self.default_config_path} is empty")
                raise ValueError("Default configuration is empty")
                
        except Exception as e:
            if "YAML" in str(e):
                self.logger.error(f"Error parsing default YAML config: {e}")
            else:
                self.logger.error(f"Error loading default config file: {e}")
            raise
    
    def _print_config_status(self):
        print("📁 Loading configuration...")

        if self.use_user_settings:
            config_dir = os.path.dirname(self.user_settings_path)
            display_dir = self._display_path(config_dir)
            settings_file = os.path.basename(self.user_settings_path)
            print(f"   ✓ Local settings: {display_dir}\\{settings_file}")

            if self.get_voice_commands_config().get('enabled', True):
                print(f"   ✓ Voice commands: {display_dir}\\commands.yaml")
            else:
                print(f"   ✓ Voice commands: disabled")

    def _display_path(self, path: str) -> str:
        if IS_MACOS:
            home = os.path.expanduser("~")
            if path.startswith(home):
                return "~" + path[len(home):]
        else:
            appdata = os.getenv('APPDATA', '')
            if appdata and path.startswith(appdata):
                return "%APPDATA%" + path[len(appdata):]
        return path
    
    def _get_stop_key_display(self) -> str:
        return beautify_hotkey(self.config['hotkey']['stop_key'])

    def print_stop_instructions_based_on_config(self):
        stop_key = self._get_stop_key_display()
        auto_paste_enabled = self.config['clipboard']['auto_paste']
        auto_send_key = self.config['hotkey'].get('auto_send_key', '')

        if auto_paste_enabled:
            print(f"   [{stop_key}] to stop and auto-paste")
        else:
            print(f"   [{stop_key}] to stop and copy to clipboard")

        if auto_paste_enabled and auto_send_key:
            print(f"   [{beautify_hotkey(auto_send_key)}] to auto-paste and send with ENTER")

    def print_startup_hotkey_instructions(self):
        recording_hotkey = beautify_hotkey(self.config['hotkey']['recording_hotkey'])
        print(f"   [{recording_hotkey}] for transcription")

        if self.get_voice_commands_config().get('enabled', True):
            command_hotkey = self.config['hotkey'].get('command_hotkey')
            if command_hotkey:
                print(f"   [{beautify_hotkey(command_hotkey)}] for voice commands")

    def print_command_stop_instructions(self):
        stop_key = self._get_stop_key_display()
        print(f"   [{stop_key}] to stop and execute command")
    
    def get_whisper_config(self) -> Dict[str, Any]:
        """Get Whisper AI configuration settings"""
        return self.config['whisper'].copy()
    
    def get_hotkey_config(self) -> Dict[str, Any]:
        return self.config['hotkey'].copy()
    
    def get_audio_config(self) -> Dict[str, Any]:
        return self.config['audio'].copy()

    def get_audio_host(self) -> Optional[str]:
        return self.config['audio'].get('host')
    
    def get_clipboard_config(self) -> Dict[str, Any]:
        return self.config['clipboard'].copy()
    
    def get_logging_config(self) -> Dict[str, Any]:
        return self.config['logging'].copy()
    
    def get_vad_config(self) -> Dict[str, Any]:
        return self.config['vad'].copy()
    
    def get_system_tray_config(self) -> Dict[str, Any]:
        return self.config['system_tray'].copy()
    
    def get_audio_feedback_config(self) -> Dict[str, Any]:
        return self.config['audio_feedback'].copy()

    def get_console_config(self) -> Dict[str, Any]:
        return self.config.get('console', {}).copy()

    def get_voice_commands_config(self) -> Dict[str, Any]:
        return self.config.get('voice_commands', {}).copy()

    def get_streaming_config(self) -> Dict[str, Any]:
        return self.config.get('streaming', {}).copy()

    def get_log_file_path(self) -> str:
        log_filename = self.config['logging']['file']['filename']
        return os.path.join(get_user_app_data_path(), log_filename)

    def get_setting(self, section: str, key: str) -> Any:
        return self.config[section][key]
    
    def _prepare_user_config_header(self, config_data):
        yaml = YAML()
        yaml.preserve_quotes = True
        yaml.indent(mapping=2, sequence=4, offset=2)

        temp_output = StringIO()
        yaml.dump(config_data, temp_output)
        lines = temp_output.getvalue().split('\n')

        content_start = 0
        for i, line in enumerate(lines):
            stripped = line.strip()
            if stripped and not stripped.startswith('#'):
                content_start = i
                break

        content_lines = lines[content_start:]

        header = [
            "# =============================================================================",
            "# WHISPER KEY - PERSONAL CONFIGURATION",
            "# =============================================================================",
            "# Edit this file to customize your settings",
            "# Save and restart Whisper Key for changes to take effect",
            ""
        ]

        return '\n'.join(header + content_lines)

    def save_config_to_user_settings_file(self):
        try:
            config_to_save = self.config
            config_with_user_header = self._prepare_user_config_header(config_to_save)
            
            with open(self.user_settings_path, 'w', encoding='utf-8') as f:
                f.write(config_with_user_header)
            
            self.logger.info(f"Configuration saved to {self.user_settings_path}")
        except Exception as e:
            self.logger.error(f"Error saving configuration to {self.user_settings_path}: {e}")
            raise
    
    def update_audio_host(self, host_name: Optional[str]):
        self.update_user_setting('audio', 'host', host_name)

    def update_user_setting(self, section: str, key: str, value: Any):
        try:
            old_value = None
            if section in self.config and key in self.config[section]:
                old_value = self.config[section][key]
                        
                if old_value != value:
                    self.config[section][key] = value
                    self.save_config_to_user_settings_file()

                    self.logger.debug(f"Updated setting {section}.{key}: {old_value} -> {value}")
            else:
                self.logger.error(f"Setting {section}:{key} does not exist")
            
        except Exception as e:
            self.logger.error(f"Error updating user setting {section}.{key}: {e}")
            raise


class ConfigValidator:
    def __init__(self, logger: logging.Logger):
        self.logger = logger
        self.config = None
        self.default_config = None
    
    def _validate_enum(self, path: str, valid_values: list):
        current_value = self._get_config_value_at_path(self.config, path)
        if current_value not in valid_values:
            self._set_to_default(path, current_value)
    
    def _validate_boolean(self, path: str):
        current_value = self._get_config_value_at_path(self.config, path)
        if not isinstance(current_value, bool):
            self._set_to_default(path, current_value)
    
    def _validate_numeric_range(self, path: str, min_val: float = None, max_val: float = None, description: str = None):
        current_value = self._get_config_value_at_path(self.config, path)
        
        if not isinstance(current_value, (int, float)):
            self.logger.warning(f"{current_value} must be numeric")
            self._set_to_default(path, current_value)
        elif min_val is not None and current_value < min_val:
            self.logger.warning(f"{current_value} must be >= {min_val}")
            self._set_to_default(path, current_value)
        elif max_val is not None and current_value > max_val:
            self.logger.warning(f"{current_value} must be <= {max_val}")
            self._set_to_default(path, current_value)
    
    def _get_config_value_at_path(self, config_dict: dict, path: str):
        keys = path.split('.')
        current = config_dict
        for key in keys:
            current = current[key]
        return current
    
    def _set_config_value_at_path(self, config_dict: dict, path: str, value):
        keys = path.split('.')
        current = config_dict
        for key in keys[:-1]:
            current = current[key]
        current[keys[-1]] = value
    
    def _validate_hotkey_string(self, path: str):
        current_value = self._get_config_value_at_path(self.config, path)
        
        if not isinstance(current_value, str) or not current_value.strip():
            self._set_to_default(path, current_value)
            return self._get_config_value_at_path(self.config, path)
        
        cleaned_combination = current_value.strip().lower()
        if cleaned_combination != current_value:
            self._set_config_value_at_path(self.config, path, cleaned_combination)
        
        return cleaned_combination
    
    def _set_to_default(self, path: str, prev_value: str):
        default_value = self._get_config_value_at_path(self.default_config, path)
        self._set_config_value_at_path(self.config, path, default_value)
        self.logger.warning(f"{prev_value} value not validated for config {path}, setting to default")
    
    def fix_config(self, config: Dict[str, Any], default_config: Dict[str, Any]) -> Dict[str, Any]:
        self.config = config
        self.default_config = default_config
        
        self._validate_enum('whisper.device', ['cpu', 'cuda'])
        
        self._validate_enum('audio.channels', [1, 2])       
        self._validate_audio_host()
        self._validate_numeric_range('audio.max_duration', min_val=0, description='max duration')
        
        self._validate_enum('logging.level', ['DEBUG', 'INFO', 'WARNING', 'ERROR', 'CRITICAL'])
        self._validate_enum('logging.console.level', ['DEBUG', 'INFO', 'WARNING', 'ERROR', 'CRITICAL'])
        
        self._validate_boolean('clipboard.auto_paste')
        self._validate_enum('clipboard.delivery_method', ['type', 'paste'])
        validated_method = platform_keyboard.validate_delivery_method(
            self._get_config_value_at_path(self.config, 'clipboard.delivery_method')
        )
        self._set_config_value_at_path(self.config, 'clipboard.delivery_method', validated_method)
        self._validate_numeric_range('clipboard.paste_pre_paste_delay', min_val=0, description='paste pre-paste delay')
        self._validate_boolean('clipboard.paste_preserve_clipboard')
        self._validate_numeric_range('clipboard.paste_clipboard_restore_delay', min_val=0, description='paste clipboard restore delay')
        self._validate_boolean('clipboard.type_also_copy_to_clipboard')
        self._validate_numeric_range('clipboard.type_auto_enter_delay', min_val=0, description='type auto enter delay')
        self._validate_numeric_range('clipboard.type_auto_enter_delay_per_100_chars', min_val=0, description='type auto enter delay per char')
        self._validate_numeric_range('clipboard.macos_key_simulation_delay', min_val=0, description='macOS key simulation delay')
        self._validate_hotkey_string('clipboard.paste_hotkey')
        
        recording_hotkey = self._validate_hotkey_string('hotkey.recording_hotkey')
        stop_key = self._validate_hotkey_string('hotkey.stop_key')
        auto_send_key = self._validate_hotkey_string('hotkey.auto_send_key')
        self._validate_hotkey_string('hotkey.cancel_combination')
        command_hotkey = self._validate_hotkey_string('hotkey.command_hotkey')
        self._resolve_hotkey_conflicts(stop_key, auto_send_key, recording_hotkey, command_hotkey)
        
        self._validate_boolean('vad.vad_precheck_enabled')
        self._validate_boolean('vad.vad_realtime_enabled')
        self._validate_numeric_range('vad.vad_onset_threshold', min_val=0.0, max_val=1.0, description='VAD onset threshold')
        self._validate_numeric_range('vad.vad_offset_threshold', min_val=0.0, max_val=1.0, description='VAD offset threshold')
        self._validate_numeric_range('vad.vad_min_speech_duration', min_val=0.001, max_val=5.0, description='VAD minimum speech duration')
        self._validate_numeric_range('vad.vad_silence_timeout_seconds', min_val=1.0, max_val=36000.0, description='VAD silence timeout')
        
        self._validate_boolean('audio_feedback.enabled')
        self._validate_boolean('system_tray.enabled')
        self._validate_boolean('voice_commands.enabled')
        
        return self.config
    
    def _resolve_hotkey_conflicts(self, stop_key: str, auto_send_key: str, recording_hotkey: str, command_hotkey: str = None):
        if stop_key == auto_send_key:
            self.logger.warning(f"   ✗ Auto-send key disabled: '{auto_send_key}' conflicts with stop key")
            self._set_config_value_at_path(self.config, 'hotkey.auto_send_key', '')

        if stop_key == recording_hotkey:
            self.logger.warning(f"   ✗ Stop key '{stop_key}' conflicts with recording hotkey, resetting to default")
            self._set_to_default('hotkey.stop_key', stop_key)

        if command_hotkey and command_hotkey == recording_hotkey:
            self.logger.warning(f"   ✗ Command hotkey disabled: '{command_hotkey}' conflicts with recording hotkey")
            self._set_config_value_at_path(self.config, 'hotkey.command_hotkey', '')

    def _validate_audio_host(self):
        host_path = 'audio.host'
        host_value = self._get_config_value_at_path(self.config, host_path)

        if host_value is not None and not isinstance(host_value, str):
            self._set_to_default(host_path, host_value)
            host_value = self._get_config_value_at_path(self.config, host_path)

        if host_value is None:
            platform_default = self._get_platform_default_audio_host()
            if platform_default:
                self._set_config_value_at_path(self.config, host_path, platform_default)

    def _get_platform_default_audio_host(self) -> Optional[str]:
        current_platform = platform.system().lower()
        if current_platform == 'windows':
            return 'WASAPI'
        return None
