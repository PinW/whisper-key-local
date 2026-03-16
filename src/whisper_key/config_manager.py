import os
import copy
import logging
from typing import Dict, Any, Optional
from io import StringIO

from ruamel.yaml import YAML

from .utils import resolve_asset_path, beautify_hotkey, get_user_app_data_path, get_version
from .platform import IS_MACOS

REPO_URL = "https://github.com/PinW/whisper-key-local"


def _build_settings_header():
    version = get_version()
    ref = "master" if version.endswith("-dev") else f"v{version}"
    return (
        f"# Whisper Key {version} - User Settings\n"
        "#\n"
        f"# Available settings: {REPO_URL}/tree/{ref}?tab=readme-ov-file#%EF%B8%8F-configuration\n"
        f"# Defaults reference: {REPO_URL}/blob/{ref}/src/whisper_key/config.defaults.yaml\n"
        "\n"
    )

EXTENSIBLE_PATHS = {'whisper.models', 'streaming.models'}

def deep_merge_config(default_config: Dict[str, Any],
                      user_config: Dict[str, Any]) -> Dict[str, Any]:

    result = default_config.copy()

    for key, value in user_config.items():
        if key in result and isinstance(result[key], dict) and isinstance(value, dict):
            result[key] = deep_merge_config(result[key], value)
        else:
            result[key] = value

    return result


def _to_plain(obj):
    if isinstance(obj, dict):
        return {k: _to_plain(v) for k, v in obj.items()}
    if isinstance(obj, list):
        return [_to_plain(v) for v in obj]
    return obj


def _compute_overrides(config, defaults, path_prefix=''):
    overrides = {}
    for key, value in config.items():
        current_path = f"{path_prefix}.{key}" if path_prefix else key
        if key not in defaults:
            if current_path in EXTENSIBLE_PATHS or path_prefix in EXTENSIBLE_PATHS:
                overrides[key] = value
            continue
        if isinstance(value, dict) and isinstance(defaults[key], dict):
            nested = _compute_overrides(value, defaults[key], current_path)
            if nested:
                overrides[key] = nested
        elif value != defaults[key]:
            overrides[key] = value
    return overrides


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
    
    
    def _ensure_user_settings_exist(self):
        user_settings_dir = os.path.dirname(self.user_settings_path)

        if not os.path.exists(user_settings_dir):
            os.makedirs(user_settings_dir, exist_ok=True)

        if not os.path.exists(self.user_settings_path):
            with open(self.user_settings_path, 'w', encoding='utf-8') as f:
                f.write(_build_settings_header())
            self.logger.info(f"Created user settings at {self.user_settings_path}")
    
    def _remove_unused_keys_from_user_config(self, user_config: Dict[str, Any], default_config: Dict[str, Any]):

        sections_to_remove = []

        for section, values in user_config.items():
            if section not in default_config:
                self.logger.info(f"Removed invalid config section: {section}")
                sections_to_remove.append(section)
            elif isinstance(values, dict) and isinstance(default_config[section], dict):
                keys_to_remove = []
                for key in values.keys():
                    if key not in default_config[section] and f"{section}.{key}" not in EXTENSIBLE_PATHS:
                        self.logger.info(f"Removed invalid config key: {section}.{key}")
                        keys_to_remove.append(key)

                for key in keys_to_remove:
                    del values[key]

        for section in sections_to_remove:
            del user_config[section]
    
    def _load_config(self):

        default_config = self._load_default_config()
        self._defaults_baseline = validate_config(
            _resolve_platform_values(copy.deepcopy(default_config)),
            default_config,
            self.logger,
        )

        if self.use_user_settings:
            self._ensure_user_settings_exist()

            try:
                yaml = YAML()
                with open(self.config_path, 'r', encoding='utf-8') as file:
                    user_config = yaml.load(file)

                if user_config is None:
                    user_config = {}

                self._remove_unused_keys_from_user_config(user_config, default_config)
                merged_config = deep_merge_config(default_config, user_config)
                resolved_config = _resolve_platform_values(merged_config)
                self.logger.info(f"Loaded user configuration from {self.config_path}")

                validated_config = validate_config(resolved_config, default_config, self.logger)
                self.config = validated_config

                return validated_config

            except Exception as e:
                if "YAML" in str(e):
                    self.logger.error(f"Error parsing user YAML config: {e}")
                else:
                    self.logger.error(f"Error loading user config file: {e}")
                print(f"   ✗ Error loading user settings, using defaults: {e}")

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

    def _write_user_config(self, user_config):
        yaml = YAML()
        yaml.preserve_quotes = True
        yaml.indent(mapping=2, sequence=4, offset=2)

        body = StringIO()
        yaml.dump(_to_plain(user_config), body)

        with open(self.user_settings_path, 'w', encoding='utf-8') as f:
            f.write(_build_settings_header())
            f.write(body.getvalue())

    def _print_config_status(self):
        print("📁 Loading configuration...")

        if self.use_user_settings:
            config_dir = os.path.dirname(self.user_settings_path)
            display_dir = self._display_path(config_dir)
            settings_file = os.path.basename(self.user_settings_path)
            print(f"   ✓ Local settings: {display_dir}{os.sep}{settings_file}")

            if self.get_voice_commands_config().get('enabled', True):
                print(f"   ✓ Voice commands: {display_dir}{os.sep}commands.yaml")
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
        auto_send_key = self.config['hotkey'].get('auto_send_key', '')
        keys = f"{stop_key}/{beautify_hotkey(auto_send_key)}" if auto_send_key else stop_key
        print(f"   [{keys}] to stop and execute command")
    
    def get_whisper_config(self) -> Dict[str, Any]:
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

    def get_voice_commands_config(self) -> Dict[str, Any]:
        return self.config.get('voice_commands', {}).copy()

    def get_streaming_config(self) -> Dict[str, Any]:
        return self.config.get('streaming', {}).copy()

    def get_log_file_path(self) -> str:
        log_filename = self.config['logging']['file']['filename']
        return os.path.join(get_user_app_data_path(), log_filename)

    def get_setting(self, section: str, key: str) -> Any:
        return self.config[section][key]
    
    def _save_user_overrides(self):
        try:
            overrides = _compute_overrides(self.config, self._defaults_baseline)
            self._write_user_config(overrides)
            self.logger.info(f"User overrides saved to {self.user_settings_path}")
        except Exception as e:
            self.logger.error(f"Error saving user overrides to {self.user_settings_path}: {e}")
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
                    self._save_user_overrides()

                    self.logger.debug(f"Updated setting {section}.{key}: {old_value} -> {value}")
            else:
                self.logger.error(f"Setting {section}:{key} does not exist")

        except Exception as e:
            self.logger.error(f"Error updating user setting {section}.{key}: {e}")
            raise


def _get_config_value_at_path(config_dict, path):
    keys = path.split('.')
    current = config_dict
    for key in keys:
        current = current[key]
    return current


def _set_config_value_at_path(config_dict, path, value):
    keys = path.split('.')
    current = config_dict
    for key in keys[:-1]:
        current = current[key]
    current[keys[-1]] = value


def _set_to_default(config, default_config, path, prev_value, logger):
    default_value = _get_config_value_at_path(default_config, path)
    _set_config_value_at_path(config, path, default_value)
    logger.warning(f"{prev_value} value not validated for config {path}, setting to default")


def _validate_numeric_range(config, default_config, path, logger, min_val=None, max_val=None):
    current_value = _get_config_value_at_path(config, path)

    if not isinstance(current_value, (int, float)):
        logger.warning(f"{current_value} must be numeric")
        _set_to_default(config, default_config, path, current_value, logger)
    elif min_val is not None and current_value < min_val:
        logger.warning(f"{current_value} must be >= {min_val}")
        _set_to_default(config, default_config, path, current_value, logger)
    elif max_val is not None and current_value > max_val:
        logger.warning(f"{current_value} must be <= {max_val}")
        _set_to_default(config, default_config, path, current_value, logger)


def _resolve_hotkey_conflicts(config, default_config, stop_key, auto_send_key, recording_hotkey, command_hotkey, logger):
    if stop_key == auto_send_key:
        logger.warning(f"   ✗ Auto-send key disabled: '{auto_send_key}' conflicts with stop key")
        _set_config_value_at_path(config, 'hotkey.auto_send_key', '')

    if stop_key == recording_hotkey:
        logger.warning(f"   ✗ Stop key '{stop_key}' conflicts with recording hotkey, resetting to default")
        _set_to_default(config, default_config, 'hotkey.stop_key', stop_key, logger)

    if command_hotkey and command_hotkey == recording_hotkey:
        logger.warning(f"   ✗ Command hotkey disabled: '{command_hotkey}' conflicts with recording hotkey")
        _set_config_value_at_path(config, 'hotkey.command_hotkey', '')


def validate_config(config, default_config, logger):
    _validate_numeric_range(config, default_config, 'audio.max_duration', logger, min_val=0)

    _validate_numeric_range(config, default_config, 'vad.vad_onset_threshold', logger, min_val=0.0, max_val=1.0)
    _validate_numeric_range(config, default_config, 'vad.vad_offset_threshold', logger, min_val=0.0, max_val=1.0)
    _validate_numeric_range(config, default_config, 'vad.vad_min_speech_duration', logger, min_val=0.001, max_val=5.0)
    _validate_numeric_range(config, default_config, 'vad.vad_silence_timeout_seconds', logger, min_val=1.0, max_val=36000.0)

    stop_key = _get_config_value_at_path(config, 'hotkey.stop_key')
    auto_send_key = _get_config_value_at_path(config, 'hotkey.auto_send_key')
    recording_hotkey = _get_config_value_at_path(config, 'hotkey.recording_hotkey')
    command_hotkey = _get_config_value_at_path(config, 'hotkey.command_hotkey')
    _resolve_hotkey_conflicts(config, default_config, stop_key, auto_send_key, recording_hotkey, command_hotkey, logger)

    return config
