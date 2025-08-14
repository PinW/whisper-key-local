import os
import logging
from ruamel.yaml import YAML
import shutil
from typing import Dict, Any, Optional
from .utils import resolve_asset_path
from pathlib import Path
from io import StringIO

def deep_merge_config(default_config: Dict[str, Any],
                      user_config: Dict[str, Any]) -> Dict[str, Any]:
    
    result = default_config.copy()
    
    for key, value in user_config.items():
        if key in result and isinstance(result[key], dict) and isinstance(value, dict):
            result[key] = deep_merge_config(result[key], value)
        else:
            result[key] = value
    
    return result

class ConfigManager:   
    def __init__(self, config_path: str = None, use_user_settings: bool = True):
        if config_path is None:
            config_path = resolve_asset_path("config.defaults.yaml")
        
        self.default_config_path = config_path
        self.use_user_settings = use_user_settings
        self.config = {}
        self.logger = logging.getLogger(__name__)
        
        if use_user_settings:
            self.user_settings_path = self._compute_user_settings_path()
            self.config_path = self.user_settings_path
        else:
            self.config_path = config_path
        
        self._print_config_status()
        self.config = self._load_config()       
        self._validate_config()
        
        self.logger.info("Configuration loaded successfully")
    
    def _compute_user_settings_path(self) -> str:
        appdata = os.getenv('APPDATA')
        whisperkey_dir = os.path.join(appdata, 'whisperkey')
        user_settings_file = os.path.join(whisperkey_dir, 'user_settings.yaml')
        
        return user_settings_file
    
    def _ensure_user_settings_exist(self):
        user_settings_dir = os.path.dirname(self.user_settings_path)
        
        if not os.path.exists(user_settings_dir):
            os.makedirs(user_settings_dir, exist_ok=True)
        
        if not os.path.exists(self.user_settings_path) or os.path.getsize(self.user_settings_path) == 0:
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
                self.logger.info(f"Loaded user configuration from {self.config_path}")
                
                return merged_config
                    
            except Exception as e:
                if "YAML" in str(e):
                    self.logger.error(f"Error parsing user YAML config: {e}")
                else:
                    self.logger.error(f"Error loading user config file: {e}")
                
        self.logger.info(f"Using default configuration from {self.default_config_path}")
        return default_config
    
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
    
    def _validate_config(self):
        # Validate whisper model size
        valid_models = ['tiny', 'base', 'small', 'medium', 'large', 'tiny.en', 'base.en', 'small.en', 'medium.en']
        if self.config['whisper']['model_size'] not in valid_models:
            self.logger.warning(f"Invalid model size '{self.config['whisper']['model_size']}', using 'tiny'")
            self.config['whisper']['model_size'] = 'tiny'
        
        # Validate device
        valid_devices = ['cpu', 'cuda']
        if self.config['whisper']['device'] not in valid_devices:
            self.logger.warning(f"Invalid device '{self.config['whisper']['device']}', using 'cpu'")
            self.config['whisper']['device'] = 'cpu'
        
        # Validate compute type
        valid_compute_types = ['int8', 'float16', 'float32']
        if self.config['whisper']['compute_type'] not in valid_compute_types:
            self.logger.warning(f"Invalid compute type '{self.config['whisper']['compute_type']}', using 'int8'")
            self.config['whisper']['compute_type'] = 'int8'
        
        # Sample rate is fixed at 16000 Hz for Whisper and TEN VAD compatibility
        # No validation needed as it's hardcoded in the audio recorder
        
        # Validate channels
        if self.config['audio']['channels'] not in [1, 2]:
            self.logger.warning(f"Invalid channels {self.config['audio']['channels']}, using 1")
            self.config['audio']['channels'] = 1
        
        # Validate max duration
        if self.config['audio']['max_duration'] < 0:
            self.logger.warning(f"Invalid max duration {self.config['audio']['max_duration']}, using 30")
            self.config['audio']['max_duration'] = 30
        
        # Validate logging level
        valid_log_levels = ['DEBUG', 'INFO', 'WARNING', 'ERROR', 'CRITICAL']
        if self.config['logging']['level'] not in valid_log_levels:
            self.logger.warning(f"Invalid log level '{self.config['logging']['level']}', using 'INFO'")
            self.config['logging']['level'] = 'INFO'
        
        # Validate console logging level
        console_level = self.config['logging']['console'].get('level', 'WARNING')
        if console_level not in valid_log_levels:
            self.logger.warning(f"Invalid console log level '{console_level}', using 'WARNING'")
            self.config['logging']['console']['level'] = 'WARNING'
        else:
            self.config['logging']['console']['level'] = console_level
        
        
        # Validate auto_paste setting
        auto_paste = self.config['clipboard'].get('auto_paste', True)
        if not isinstance(auto_paste, bool):
            self.logger.warning(f"Invalid auto_paste value '{auto_paste}', using True")
            self.config['clipboard']['auto_paste'] = True
        else:
            self.config['clipboard']['auto_paste'] = auto_paste
        
        # Validate paste_method setting
        valid_paste_methods = ['key_simulation', 'windows_api']
        paste_method = self.config['clipboard'].get('paste_method', 'key_simulation')
        if paste_method not in valid_paste_methods:
            self.logger.warning(f"Invalid paste_method '{paste_method}', using 'key_simulation'")
            self.config['clipboard']['paste_method'] = 'key_simulation'
        else:
            self.config['clipboard']['paste_method'] = paste_method
        
        # Validate preserve_clipboard setting
        preserve_clipboard = self.config['clipboard'].get('preserve_clipboard', True)
        if not isinstance(preserve_clipboard, bool):
            self.logger.warning(f"Invalid preserve_clipboard value '{preserve_clipboard}', using True")
            self.config['clipboard']['preserve_clipboard'] = True
        else:
            self.config['clipboard']['preserve_clipboard'] = preserve_clipboard
               
        # Validate key_simulation_delay setting
        key_simulation_delay = self.config['hotkey'].get('key_simulation_delay', 0.05)
        if not isinstance(key_simulation_delay, (int, float)) or key_simulation_delay < 0:
            self.logger.warning(f"Invalid key_simulation_delay value '{key_simulation_delay}', using 0.05")
            self.config['hotkey']['key_simulation_delay'] = 0.05
        else:
            self.config['hotkey']['key_simulation_delay'] = key_simulation_delay
        
        # Validate main hotkey combination format
        main_combination = self.config['hotkey'].get('recording_hotkey', 'ctrl+win')
        if not isinstance(main_combination, str) or not main_combination.strip():
            self.logger.warning(f"Invalid main hotkey combination '{main_combination}', using 'ctrl+win'")
            self.config['hotkey']['recording_hotkey'] = 'ctrl+win'
            main_combination = 'ctrl+win'
        else:
            # Clean up the combination (strip whitespace, convert to lowercase)
            cleaned_combination = main_combination.strip().lower()
            if cleaned_combination != main_combination:
                self.config['hotkey']['recording_hotkey'] = cleaned_combination
                main_combination = cleaned_combination
        
        # Validate stop-with-modifier setting
        stop_with_modifier_enabled = self.config['hotkey'].get('stop_with_modifier_enabled', False)
        if not isinstance(stop_with_modifier_enabled, bool):
            self.logger.warning(f"Invalid stop_with_modifier_enabled value '{stop_with_modifier_enabled}', using False")
            self.config['hotkey']['stop_with_modifier_enabled'] = False
        else:
            self.config['hotkey']['stop_with_modifier_enabled'] = stop_with_modifier_enabled

        # Validate auto-enter hotkey settings
        auto_enter_enabled = self.config['hotkey'].get('auto_enter_enabled', True)
        if not isinstance(auto_enter_enabled, bool):
            self.logger.warning(f"Invalid auto_enter_enabled value '{auto_enter_enabled}', using True")
            self.config['hotkey']['auto_enter_enabled'] = True
        else:
            self.config['hotkey']['auto_enter_enabled'] = auto_enter_enabled

        # Validate auto-enter hotkey combination format
        auto_enter_combination = self.config['hotkey'].get('auto_enter_combination', 'alt')
        if not isinstance(auto_enter_combination, str) or not auto_enter_combination.strip():
            self.logger.warning(f"Invalid auto_enter_combination '{auto_enter_combination}'")
            self.config['hotkey']['auto_enter_combination'] = 'alt'
        else:
            self.config['hotkey']['auto_enter_combination'] = auto_enter_combination.strip().lower()
        
        # Smart conflict detection between auto-enter and main+stop_with_modifier
        auto_enter_combination = self.config['hotkey']['auto_enter_combination']
        stop_with_modifier = self.config['hotkey']['stop_with_modifier_enabled']
        
        conflict_detected = False
        conflict_reason = ""
        
        if stop_with_modifier:
            # Extract first modifier from main hotkey for stop-with-modifier comparison
            main_first_key = main_combination.split('+')[0] if '+' in main_combination else main_combination
            # Extract first key from auto-enter hotkey
            auto_enter_first_key = auto_enter_combination.split('+')[0] if '+' in auto_enter_combination else auto_enter_combination
            
            if main_first_key == auto_enter_first_key:
                conflict_detected = True
                conflict_reason = f"hotkey '{auto_enter_combination}' first key is shared with main hotkey and stop-with-modifier is enabled'"
        else:
            # No stop-with-modifier, just check for identical full combinations
            if auto_enter_combination == main_combination:
                conflict_detected = True
                conflict_reason = f"hotkey '{auto_enter_combination}' is same as main hotkey"
        
        if conflict_detected:
            self.logger.warning(f"   ✗ Auto-enter disabled: {conflict_reason}")
            self.config['hotkey']['auto_enter_enabled'] = False
        
        # Validate VAD configuration ranges
        self._validate_vad_config()
        
        # Validate audio_feedback enabled setting
        audio_feedback_enabled = self.config.get('audio_feedback', {}).get('enabled', True)
        if not isinstance(audio_feedback_enabled, bool):
            self.logger.warning(f"Invalid audio_feedback enabled value '{audio_feedback_enabled}', using True")
            if 'audio_feedback' not in self.config:
                self.config['audio_feedback'] = {}
            self.config['audio_feedback']['enabled'] = True
        else:
            if 'audio_feedback' not in self.config:
                self.config['audio_feedback'] = {}
            self.config['audio_feedback']['enabled'] = audio_feedback_enabled
        
        # Validate system_tray enabled setting
        system_tray_enabled = self.config.get('system_tray', {}).get('enabled', True)
        if not isinstance(system_tray_enabled, bool):
            self.logger.warning(f"Invalid system_tray enabled value '{system_tray_enabled}', using True")
            if 'system_tray' not in self.config:
                self.config['system_tray'] = {}
            self.config['system_tray']['enabled'] = True
        else:
            if 'system_tray' not in self.config:
                self.config['system_tray'] = {}
            self.config['system_tray']['enabled'] = system_tray_enabled
        
        # Save validation fixes to user file
        if self.use_user_settings:
            self.save_config_to_user_settings_file()
    
    def _validate_vad_config(self):
        """Validate VAD configuration values are within acceptable ranges"""
        if 'vad' not in self.config:
            return
            
        vad_config = self.config['vad']
        
        # Validate vad_precheck_enabled (boolean)
        vad_precheck_enabled = vad_config.get('vad_precheck_enabled', True)
        if not isinstance(vad_precheck_enabled, bool):
            self.logger.warning(f"Invalid vad_precheck_enabled value '{vad_precheck_enabled}', using True")
            self.config['vad']['vad_precheck_enabled'] = True
        else:
            self.config['vad']['vad_precheck_enabled'] = vad_precheck_enabled
        vad_fields = {
            'vad_onset_threshold': (0.0, 1.0, 'VAD onset threshold'),
            'vad_offset_threshold': (0.0, 1.0, 'VAD offset threshold'),
            'vad_min_speech_duration': (0.001, 5.0, 'VAD minimum speech duration')  # 1ms minimum, 5s maximum
        }
        
        for field, (min_val, max_val, description) in vad_fields.items():
            if field in vad_config:
                value = vad_config[field]
                if not isinstance(value, (int, float)):
                    self.logger.warning(f"Invalid {description}: '{value}' (must be numeric), using default")
                    del vad_config[field]
                elif not (min_val <= value <= max_val):
                    self.logger.warning(f"Invalid {description}: {value} (must be {min_val}-{max_val}), using default")
                    del vad_config[field]
    
    def _print_config_status(self):
        print("📁 Loading configuration...")

        if self.use_user_settings:
            print(f"   ✓ Using user settings from: {self.user_settings_path}")
        else:
            print(f"   ✗ Using default settings from: {self.config_path}")
    
    def print_stop_instructions_based_on_config(self):
        from .utils import beautify_hotkey
        
        main_hotkey = self.config['hotkey']['recording_hotkey']
        auto_enter_enabled = self.config['hotkey']['auto_enter_enabled']
        auto_enter_hotkey = self.config['hotkey']['auto_enter_combination']
        stop_with_modifier = self.config['hotkey']['stop_with_modifier_enabled']
        auto_paste_enabled = self.config['clipboard']['auto_paste']
        
        if stop_with_modifier:
            # Extract first modifier for display
            primary_key = main_hotkey.split('+')[0] if '+' in main_hotkey else main_hotkey
            primary_key = primary_key.upper()
        else:
            primary_key = beautify_hotkey(main_hotkey)
        
        if auto_enter_enabled:
            auto_enter_key = beautify_hotkey(auto_enter_hotkey)
        else:
            auto_enter_key = None
        
        if not auto_paste_enabled:
            print(f"   Press [{primary_key}] to stop recording and copy to clipboard.")
        elif not auto_enter_enabled:
            print(f"   Press [{primary_key}] to stop recording and auto-paste.")
        else:
            print(f"   Press [{primary_key}] to stop recording and auto-paste, [{auto_enter_key}] to auto-paste and send with (ENTER) key press.")

    # Getter methods for easy access to configuration sections
    
    def get_whisper_config(self) -> Dict[str, Any]:
        """Get Whisper AI configuration settings"""
        whisper_config = self.config['whisper'].copy()
        
        # Convert 'auto' language setting to None for whisper system compatibility
        if whisper_config.get('language') == 'auto':
            whisper_config['language'] = None
            
        return whisper_config
    
    def get_hotkey_config(self) -> Dict[str, Any]:
        """Get hotkey configuration settings"""
        return self.config['hotkey'].copy()
    
    def get_audio_config(self) -> Dict[str, Any]:
        """Get audio recording configuration settings"""
        return self.config['audio'].copy()
    
    def get_clipboard_config(self) -> Dict[str, Any]:
        """Get clipboard configuration settings"""
        return self.config['clipboard'].copy()
    
    def get_logging_config(self) -> Dict[str, Any]:
        """Get logging configuration settings"""
        return self.config['logging'].copy()
    
    def get_performance_config(self) -> Dict[str, Any]:
        """Get performance configuration settings"""
        return self.config['performance'].copy()
    
    def get_advanced_config(self) -> Dict[str, Any]:
        """Get advanced configuration settings"""
        return self.config['advanced'].copy()
    
    def get_vad_config(self) -> Dict[str, Any]:
        """Get Voice Activity Detection (VAD) configuration settings"""
        return self.config['vad'].copy()
    
    def get_system_tray_config(self) -> Dict[str, Any]:
        """Get system tray configuration settings"""
        return self.config['system_tray'].copy()
    
    def get_audio_feedback_config(self) -> Dict[str, Any]:
        """Get audio feedback configuration settings"""
        return self.config['audio_feedback'].copy()
    
    def get_setting(self, section: str, key: str, default: Any = None) -> Any:
        """
        Get a specific configuration setting
        
        Parameters:
        - section: Configuration section (e.g., 'whisper', 'hotkey')
        - key: Setting key within the section
        - default: Default value if setting not found
        """
        try:
            return self.config[section][key]
        except KeyError:
            self.logger.warning(f"Setting '{section}.{key}' not found, using default: {default}")
            return default
    
    def _prepare_user_config_header(self, config_data):
        yaml = YAML()
        yaml.preserve_quotes = True
        yaml.indent(mapping=2, sequence=4, offset=2)
        
        temp_output = StringIO()
        yaml.dump(config_data, temp_output)
        lines = temp_output.getvalue().split('\n')
        
        # Find end of header - first blank line is the cutoff
        data_start = 0
        for i, line in enumerate(lines):
            if not line.strip():  # Empty line found
                data_start = i
                break
        
        user_config = []
        user_config.append("# =============================================================================")
        user_config.append("# WHISPER KEY - PERSONAL CONFIGURATION")
        user_config.append("# =============================================================================")
        user_config.extend(lines[data_start:])
        
        return '\n'.join(user_config)

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

    def update_user_setting(self, section: str, key: str, value: Any):
        try:
            old_value = None
            if section in self.config and key in self.config[section]:
                old_value = self.config[section][key]
                        
                if old_value != value:
                    self.config[section][key] = value
                    self.save_config_to_user_settings_file()

                    print(f"⚙️ Updated {section} setting")
                
                    self.logger.debug(f"Updated setting {section}.{key}: {old_value} -> {value}")
            else:
                self.logger.error(f"Setting {section}:{key} does not exist")
            
        except Exception as e:
            self.logger.error(f"Error updating user setting {section}.{key}: {e}")
            raise
    
    def reload_config(self):
        self.logger.info("Reloading configuration...")
        self._load_config()
        self._validate_config()
        self.logger.info("Configuration reloaded successfully")

