"""
Configuration Manager

This module handles loading and validating configuration settings from config.yaml.
It provides a central place to manage all application settings and ensures they
have sensible defaults if the config file is missing or incomplete.

configuration file and provides all the settings to other parts of the program.
"""

import os
import logging
from ruamel.yaml import YAML
import shutil
from typing import Dict, Any, Optional
from .utils import resolve_asset_path
from pathlib import Path

def deep_merge_config(default_config: Dict[str, Any], user_config: Dict[str, Any]) -> Dict[str, Any]:
    """
    Deep merge user configuration on top of default configuration
    
    Parameters:
    - default_config: The base configuration with all default values
    - user_config: User's configuration that may have missing keys
    
    Returns:
    - Merged configuration with user values overlaid on defaults
    
    settings override the defaults, but missing user settings keep the defaults.
    """
    result = default_config.copy()
    
    for key, value in user_config.items():
        if key in result and isinstance(result[key], dict) and isinstance(value, dict):
            # Recursively merge nested dictionaries
            result[key] = deep_merge_config(result[key], value)
        else:
            # Override with user value
            result[key] = value
    
    return result

class ConfigManager:
    """
    Manages configuration loading and validation for the application
    
    This class loads settings from config.yaml and provides them to other components
    with proper validation and fallback defaults.
    """
    
    def __init__(self, config_path: str = None, use_user_settings: bool = True):
        """
        Initialize the configuration manager
        
        Parameters:
        - config_path: Path to the default YAML configuration file (None for auto-detection)
        - use_user_settings: Whether to use user-specific settings from AppData
        """
        # Auto-detect config path relative to the main script
        if config_path is None:
            config_path = resolve_asset_path("config.defaults.yaml")
        
        self.default_config_path = config_path
        self.use_user_settings = use_user_settings
        self.config = {}
        self.logger = logging.getLogger(__name__)
        
        # Determine actual config path to use
        if use_user_settings:
            self.user_settings_path = self._get_user_settings_path()
            self.config_path = self.user_settings_path
            # Create user settings if they don't exist
            self._ensure_user_settings_exist()
        else:
            self.config_path = config_path
        
        # Print status for user
        self._print_config_status()

        # Load the configuration
        self._load_config()
        
        # Validate configuration
        self._validate_config()
        
        self.logger.info("Configuration loaded successfully")
    
    def _get_user_settings_path(self) -> str:
        r"""
        Get the path to user settings file in Windows AppData
        
        Returns the path to user_settings.yaml in %APPDATA%\whisperkey\
        """
        # Get Windows AppData path
        appdata = os.getenv('APPDATA')
        if not appdata:
            # Fallback for non-Windows systems or if APPDATA not set
            home = os.path.expanduser('~')
            appdata = os.path.join(home, 'AppData', 'Roaming')
        
        # Create whisperkey directory path
        whisperkey_dir = os.path.join(appdata, 'whisperkey')
        user_settings_file = os.path.join(whisperkey_dir, 'user_settings.yaml')
        
        return user_settings_file
    
    def _ensure_user_settings_exist(self):
        """
        Ensure user settings directory and file exist
        
        Creates the directory and copies default config if user_settings.yaml doesn't exist
        """
        user_settings_dir = os.path.dirname(self.user_settings_path)
        
        # Create directory if it doesn't exist
        if not os.path.exists(user_settings_dir):
            try:
                os.makedirs(user_settings_dir, exist_ok=True)
                self.logger.info(f"Created user settings directory: {user_settings_dir}")
            except Exception as e:
                self.logger.error(f"Failed to create user settings directory: {e}")
                raise
        
        # Copy default config if user settings don't exist
        if not os.path.exists(self.user_settings_path):
            if os.path.exists(self.default_config_path):
                try:
                    shutil.copy2(self.default_config_path, self.user_settings_path)
                    self.logger.info(f"Created initial user settings from {self.default_config_path}")
                except Exception as e:
                    self.logger.error(f"Failed to create initial user settings: {e}")
                    raise
            else:
                # If no default config.yaml exists, we can't create user settings
                # This is a critical error since we need config.yaml as our source of truth
                error_msg = f"Default config {self.default_config_path} not found - cannot create user settings"
                self.logger.error(error_msg)
                raise FileNotFoundError(error_msg)
    
    def _load_config(self):
        """
        Load configuration using two-stage loading:
        Stage 1: Load default config.yaml as baseline
        Stage 2: Load user config and merge on top of defaults
        """

        # Stage 1: Load default configuration from config.yaml
        default_config = self._load_default_config()
        
        # Stage 2: Load user configuration and merge with defaults
        if self.use_user_settings and os.path.exists(self.config_path):
            try:
                yaml = YAML()
                with open(self.config_path, 'r', encoding='utf-8') as f:
                    user_config = yaml.load(f)
                
                if user_config:
                    # Deep merge user config on top of defaults
                    self.config = deep_merge_config(default_config, user_config)
                    self.logger.info(f"Loaded user configuration from {self.config_path}")
                else:
                    # Empty user config, use defaults
                    self.config = default_config
                    self.logger.warning(f"User config file {self.config_path} is empty, using defaults")
                    
            except yaml.YAMLError as e:
                self.logger.error(f"Error parsing user YAML config: {e}")
                self.logger.warning("Using default configuration")
                self.config = default_config
            except Exception as e:
                self.logger.error(f"Error loading user config file: {e}")
                self.logger.warning("Using default configuration")
                self.config = default_config
        else:
            # No user config or not using user settings, use defaults
            self.config = default_config
            if self.use_user_settings:
                self.logger.info(f"User config file {self.config_path} not found, using defaults")
            else:
                self.logger.info("Using default configuration (user settings disabled)")
    
    def _load_default_config(self) -> Dict[str, Any]:
        """
        Load the default configuration from config.yaml
        
        Returns:
        - Default configuration dictionary loaded from config.yaml
        
        This ensures config.yaml is the single source of truth for all defaults.
        """
        try:
            yaml = YAML()
            with open(self.default_config_path, 'r', encoding='utf-8') as f:
                default_config = yaml.load(f)
            
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
        
        # Validate text formatting
        valid_formatting = ['none', 'capitalize', 'sentence']
        text_formatting = self.config['clipboard'].get('text_formatting', 'none')
        if text_formatting not in valid_formatting:
            self.logger.warning(f"Invalid text formatting '{text_formatting}', using 'none'")
            self.config['clipboard']['text_formatting'] = 'none'
        else:
            self.config['clipboard']['text_formatting'] = text_formatting
        
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
        main_combination = self.config['hotkey'].get('combination', 'ctrl+win')
        if not isinstance(main_combination, str) or not main_combination.strip():
            self.logger.warning(f"Invalid main hotkey combination '{main_combination}', using 'ctrl+win'")
            self.config['hotkey']['combination'] = 'ctrl+win'
            main_combination = 'ctrl+win'
        else:
            # Clean up the combination (strip whitespace, convert to lowercase)
            cleaned_combination = main_combination.strip().lower()
            if cleaned_combination != main_combination:
                self.config['hotkey']['combination'] = cleaned_combination
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
            self.save_user_settings()
    
    def _validate_vad_config(self):
        """Validate VAD configuration values are within acceptable ranges"""
        if 'advanced' not in self.config:
            return
            
        advanced_config = self.config['advanced']
        vad_fields = {
            'vad_onset_threshold': (0.0, 1.0, 'VAD onset threshold'),
            'vad_offset_threshold': (0.0, 1.0, 'VAD offset threshold'),
            'vad_min_speech_duration': (0.001, 5.0, 'VAD minimum speech duration')  # 1ms minimum, 5s maximum
        }
        
        for field, (min_val, max_val, description) in vad_fields.items():
            if field in advanced_config:
                value = advanced_config[field]
                if not isinstance(value, (int, float)):
                    self.logger.warning(f"Invalid {description}: '{value}' (must be numeric), removing from config")
                    del advanced_config[field]
                elif not (min_val <= value <= max_val):
                    self.logger.warning(f"Invalid {description}: {value} (must be {min_val}-{max_val}), removing from config")
                    del advanced_config[field]
    
    def _print_config_status(self):
        print("📁 Loading configuration...")

        if self.use_user_settings:
            settings_path = self.get_user_settings_path()
            print(f"   ✓ Using user settings from: {settings_path}")
        else:
            print(f"   ✗ Using default settings from: {self.config_path}")
    
    def print_stop_instructions(self):
        from .utils import beautify_hotkey
        
        hotkey_config = self.get_hotkey_config()
        clipboard_config = self.get_clipboard_config()
        
        main_hotkey = hotkey_config['combination']
        auto_enter_enabled = hotkey_config['auto_enter_enabled']
        auto_enter_hotkey = hotkey_config['auto_enter_combination']
        stop_with_modifier = hotkey_config['stop_with_modifier_enabled']
        auto_paste_enabled = clipboard_config['auto_paste']
        
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
    
    def get_system_tray_config(self) -> Dict[str, Any]:
        """Get system tray configuration settings"""
        return self.config['system_tray'].copy()
    
    def get_audio_feedback_config(self) -> Dict[str, Any]:
        """Get audio feedback configuration settings"""
        return self.config['audio_feedback'].copy()
    
    def get_full_config(self) -> Dict[str, Any]:
        """Get the complete configuration"""
        return self.config.copy()
    
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
    
    def _save_config_to_file(self, file_path: str):
        """
        Helper method to save configuration to a specific file
        Preserves YAML comments and formatting using ruamel.yaml
        """
        try:
            yaml = YAML()
            yaml.preserve_quotes = True
            yaml.indent(mapping=2, sequence=4, offset=2)
            
            # Read the original file to preserve structure and comments
            original_data = None
            if os.path.exists(file_path):
                with open(file_path, 'r', encoding='utf-8') as f:
                    original_data = yaml.load(f)
            
            # Always use clean config structure to avoid preserving formatting issues
            # This ensures proper section organization and prevents structural corruption
            data_to_save = self.config
            
            # Write back with preserved formatting
            with open(file_path, 'w', encoding='utf-8') as f:
                # If this is the user settings file, write custom header and clean data
                if file_path == getattr(self, 'user_settings_path', None):
                    # Write personal header
                    f.write("# =============================================================================\n")
                    f.write("# WHISPER KEY - PERSONAL CONFIGURATION\n") 
                    f.write("# =============================================================================\n")
                    f.write("# Overrides default configs at:\n")
                    f.write("# config.defaults.yaml (in application folder)\n")
                    f.write("#")
                    
                    # Hack: dump to string first, then skip the first 8 lines (old header)
                    from io import StringIO
                    temp_output = StringIO()
                    yaml.dump(data_to_save, temp_output)
                    lines = temp_output.getvalue().split('\n')
                    
                    # Skip first 8 lines (old header) and write the rest
                    for line in lines[8:]:
                        f.write(line + '\n')
                else:
                    # For other files, use normal dump with comment preservation
                    yaml.dump(data_to_save, f)
            
            self.logger.info(f"Configuration saved to {file_path}")
        except Exception as e:
            self.logger.error(f"Error saving configuration to {file_path}: {e}")
            raise
    
    def save_config(self, output_path: Optional[str] = None):
        """
        Save current configuration to YAML file
        
        This can be useful for creating a config file with current settings.
        """
        output_file = output_path or self.config_path
        self._save_config_to_file(output_file)
    
    def save_user_settings(self):
        """
        Save current configuration to user settings file
        
        Only works if user settings are enabled
        """
        if not self.use_user_settings:
            self.logger.warning("User settings not enabled, cannot save user settings")
            return
        
        self._save_config_to_file(self.user_settings_path)
    
    def _get_setting_display_info(self, section: str, key: str, value: Any) -> dict:
        """
        Get display information for a setting change (emoji, description, etc.)
        
        This centralizes the mapping of settings to user-friendly descriptions.
        """
        # Setting display mappings - add new settings here as needed
        setting_info = {
            'clipboard': {
                'auto_paste': {
                    'emoji': '📋',
                    'ascii': '[Clipboard]',
                    'name': '',
                    'true_desc': 'Auto-pasting transcriptions...',
                    'false_desc': 'Copying transcriptions to clipboard...'
                }
            },
            'whisper': {
                'model_size': {
                    'emoji': '🧠',
                    'ascii': '[AI]',
                    'name': 'AI Model',
                    'format': 'value'  # Just show the value
                }
            },
            'hotkey': {
                'combination': {
                    'emoji': '⌨️',
                    'ascii': '[Hotkey]',
                    'name': 'Hotkey',
                    'format': 'value'
                },
                'auto_enter_combination': {
                    'emoji': '🚀',
                    'ascii': '[Auto-Enter]',
                    'name': 'Auto-Enter Hotkey',
                    'format': 'value'
                },
                'auto_enter_enabled': {
                    'emoji': '🚀',
                    'ascii': '[Auto-Enter]',
                    'name': 'Auto-Enter Mode',
                    'true_desc': 'enabled',
                    'false_desc': 'disabled'
                },
                'stop_with_modifier_enabled': {
                    'emoji': '⏹️',
                    'ascii': '[Stop with Modifier]',
                    'name': 'Stop with Modifier',
                    'true_desc': 'enabled',
                    'false_desc': 'disabled'
                }
            },
            'audio': {
                'sample_rate': {
                    'emoji': '🎵',
                    'ascii': '[Audio]',
                    'name': 'Audio Quality',
                    'format': 'value'
                }
            }
        }
        
        # Get section info
        section_info = setting_info.get(section, {})
        key_info = section_info.get(key, {})
        
        # Default fallback
        if not key_info:
            return {
                'emoji': '⚙️',
                'ascii': '[Setting]',
                'name': f'{section}.{key}',
                'description': str(value)
            }
        
        # Handle boolean settings
        if isinstance(value, bool):
            if 'true_desc' in key_info and 'false_desc' in key_info:
                description = key_info['true_desc'] if value else key_info['false_desc']
            else:
                description = 'enabled' if value else 'disabled'
        # Handle other value types
        else:
            if key_info.get('format') == 'value':
                description = str(value)
            else:
                description = str(value)
        
        return {
            'emoji': key_info.get('emoji', '⚙️'),
            'ascii': key_info.get('ascii', '[Setting]'),
            'name': key_info.get('name', key),
            'description': description
        }

    def update_user_setting(self, section: str, key: str, value: Any):
        """
        Update a specific user setting and save to file
        
        Parameters:
        - section: Configuration section (e.g., 'whisper', 'hotkey')
        - key: Setting key within the section
        - value: New value for the setting
        """
        if not self.use_user_settings:
            self.logger.warning("User settings not enabled, cannot update user setting")
            return
        
        try:
            # Store old value for comparison
            old_value = None
            if section in self.config and key in self.config[section]:
                old_value = self.config[section][key]
            
            # Update the setting
            if section not in self.config:
                self.config[section] = {}
            
            self.config[section][key] = value
            
            # Get display information for this setting
            display_info = self._get_setting_display_info(section, key, value)
            
            # Get display components
            emoji = display_info['emoji']
            ascii_prefix = display_info['ascii']
            name = display_info['name']
            description = display_info['description']
            
            # Create user-friendly messages
            if old_value != value:  # Only log if value actually changed
                # Use ASCII version for logging (avoids Unicode encoding errors on Windows)
                log_message = " ".join(filter(None, [ascii_prefix, name, description]))
                self.logger.info(log_message)
                
                # Use emoji version for console output (usually works fine)
                console_message = " ".join(filter(None, [emoji, name, description]))
                print(console_message)
            
            # Technical log for debugging
            self.logger.debug(f"Updated setting {section}.{key}: {old_value} -> {value}")
            
            # Save to user settings file
            self.save_user_settings()
            
        except Exception as e:
            self.logger.error(f"Error updating user setting {section}.{key}: {e}")
            raise
    
    def get_user_settings_path(self) -> Optional[str]:
        """
        Get the path to the user settings file
        
        Returns None if user settings are not enabled
        """
        if self.use_user_settings:
            return self.user_settings_path
        return None
    
    def reload_config(self):
        """
        Reload configuration from file
        
        Useful if the config file has been modified while the app is running.
        """
        self.logger.info("Reloading configuration...")
        self._load_config()
        self._validate_config()
        self.logger.info("Configuration reloaded successfully")
    
    def _update_yaml_data(self, original_data: Dict[str, Any], new_data: Dict[str, Any]):
        """
        Update original YAML data with new values while preserving structure
        
        This recursively updates the original data structure with new values,
        maintaining comments and formatting from the original file.
        """
        for key, value in new_data.items():
            if key in original_data and isinstance(original_data[key], dict) and isinstance(value, dict):
                # Recursively update nested dictionaries
                self._update_yaml_data(original_data[key], value)
            else:
                # Update with new value
                original_data[key] = value

