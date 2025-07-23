"""
Configuration Manager

This module handles loading and validating configuration settings from config.yaml.
It provides a central place to manage all application settings and ensures they
have sensible defaults if the config file is missing or incomplete.

For beginners: This is like the "settings menu" of our app - it reads the 
configuration file and provides all the settings to other parts of the program.
"""

import os
import logging
import yaml
import shutil
from typing import Dict, Any, Optional
from pathlib import Path

class ConfigManager:
    """
    Manages configuration loading and validation for the application
    
    This class loads settings from config.yaml and provides them to other components
    with proper validation and fallback defaults.
    """
    
    def __init__(self, config_path: str = "config.yaml", use_user_settings: bool = True):
        """
        Initialize the configuration manager
        
        Parameters:
        - config_path: Path to the default YAML configuration file
        - use_user_settings: Whether to use user-specific settings from AppData
        """
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
                # Create empty user settings with defaults if no config.yaml exists
                self.logger.warning(f"Default config {self.default_config_path} not found, creating user settings with defaults")
                self._save_config_to_file(self.user_settings_path)
    
    def _load_config(self):
        """
        Load configuration from YAML file with fallback defaults
        """
        # Define default configuration
        self.default_config = {
            'whisper': {
                'model_size': 'tiny',
                'device': 'cpu',
                'compute_type': 'int8',
                'language': None,
                'beam_size': 5
            },
            'hotkey': {
                'combination': 'ctrl+shift+space'
            },
            'audio': {
                'sample_rate': 16000,
                'channels': 1,
                'dtype': 'float32',
                'max_duration': 30
            },
            'clipboard': {
                'auto_paste': False,
                'paste_method': 'key_simulation',
                'text_formatting': 'none'
            },
            'logging': {
                'level': 'INFO',
                'file': {
                    'enabled': True,
                    'filename': 'whisper_app.log',
                    'max_size_mb': 10,
                    'backup_count': 3
                },
                'console': {
                    'enabled': True,
                    'colored': True
                }
            },
            'performance': {
                'cpu_threads': 0,
                'clear_cache': False
            },
            'system_tray': {
                'enabled': True,
                'tooltip': 'Whisper Key',
                'notifications': False
            },
            'advanced': {
                'vad': {
                    'enabled': False,
                    'threshold': 0.5
                },
                'model_cache_dir': None,
                'debug': {
                    'save_audio_files': False,
                    'audio_output_dir': 'debug_audio'
                }
            }
        }
        
        # Start with defaults
        self.config = self.default_config.copy()
        
        # Try to load user configuration
        if os.path.exists(self.config_path):
            try:
                with open(self.config_path, 'r', encoding='utf-8') as f:
                    user_config = yaml.safe_load(f)
                
                if user_config:
                    # Merge user config with defaults (deep merge)
                    self.config = self._deep_merge(self.default_config, user_config)
                    self.logger.info(f"Loaded configuration from {self.config_path}")
                else:
                    self.logger.warning(f"Config file {self.config_path} is empty, using defaults")
                    
            except yaml.YAMLError as e:
                self.logger.error(f"Error parsing YAML config: {e}")
                self.logger.warning("Using default configuration")
            except Exception as e:
                self.logger.error(f"Error loading config file: {e}")
                self.logger.warning("Using default configuration")
        else:
            self.logger.info(f"Config file {self.config_path} not found, using defaults")
    
    def _deep_merge(self, default: Dict[str, Any], user: Dict[str, Any]) -> Dict[str, Any]:
        """
        Deep merge user configuration with defaults
        
        This ensures that if user only specifies some settings, the rest come from defaults.
        """
        result = default.copy()
        
        for key, value in user.items():
            if key in result and isinstance(result[key], dict) and isinstance(value, dict):
                result[key] = self._deep_merge(result[key], value)
            else:
                result[key] = value
        
        return result
    
    def _validate_config(self):
        """
        Validate configuration settings and fix invalid values
        """
        # Validate whisper model size
        valid_models = ['tiny', 'base', 'small', 'medium', 'large']
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
        
        # Validate audio sample rate
        if self.config['audio']['sample_rate'] <= 0:
            self.logger.warning(f"Invalid sample rate {self.config['audio']['sample_rate']}, using 16000")
            self.config['audio']['sample_rate'] = 16000
        
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
        
        # Validate text formatting
        valid_formatting = ['none', 'capitalize', 'sentence']
        if self.config['clipboard']['text_formatting'] not in valid_formatting:
            self.logger.warning(f"Invalid text formatting '{self.config['clipboard']['text_formatting']}', using 'none'")
            self.config['clipboard']['text_formatting'] = 'none'
        
        # Validate auto_paste setting
        if not isinstance(self.config['clipboard']['auto_paste'], bool):
            self.logger.warning(f"Invalid auto_paste value '{self.config['clipboard']['auto_paste']}', using False")
            self.config['clipboard']['auto_paste'] = False
        
        # Validate paste_method setting
        valid_paste_methods = ['key_simulation', 'windows_api']
        if self.config['clipboard']['paste_method'] not in valid_paste_methods:
            self.logger.warning(f"Invalid paste_method '{self.config['clipboard']['paste_method']}', using 'key_simulation'")
            self.config['clipboard']['paste_method'] = 'key_simulation'
    
    # Getter methods for easy access to configuration sections
    
    def get_whisper_config(self) -> Dict[str, Any]:
        """Get Whisper AI configuration settings"""
        return self.config['whisper'].copy()
    
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
        """
        try:
            with open(file_path, 'w', encoding='utf-8') as f:
                yaml.dump(self.config, f, default_flow_style=False, indent=2)
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
                    'name': 'Auto-paste',
                    'true_desc': 'enabled',
                    'false_desc': 'disabled'
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
                log_message = f"{ascii_prefix} {name} {description}"
                self.logger.info(log_message)
                
                # Use emoji version for console output (usually works fine)
                console_message = f"{emoji} {name} {description}"
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