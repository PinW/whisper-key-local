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
from typing import Dict, Any, Optional
from pathlib import Path

class ConfigManager:
    """
    Manages configuration loading and validation for the application
    
    This class loads settings from config.yaml and provides them to other components
    with proper validation and fallback defaults.
    """
    
    def __init__(self, config_path: str = "config.yaml"):
        """
        Initialize the configuration manager
        
        Parameters:
        - config_path: Path to the YAML configuration file
        """
        self.config_path = config_path
        self.config = {}
        self.logger = logging.getLogger(__name__)
        
        # Load the configuration
        self._load_config()
        
        # Validate configuration
        self._validate_config()
        
        self.logger.info("Configuration loaded successfully")
    
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
    
    def save_config(self, output_path: Optional[str] = None):
        """
        Save current configuration to YAML file
        
        This can be useful for creating a config file with current settings.
        """
        output_file = output_path or self.config_path
        
        try:
            with open(output_file, 'w', encoding='utf-8') as f:
                yaml.dump(self.config, f, default_flow_style=False, indent=2)
            self.logger.info(f"Configuration saved to {output_file}")
        except Exception as e:
            self.logger.error(f"Error saving configuration: {e}")
            raise
    
    def reload_config(self):
        """
        Reload configuration from file
        
        Useful if the config file has been modified while the app is running.
        """
        self.logger.info("Reloading configuration...")
        self._load_config()
        self._validate_config()
        self.logger.info("Configuration reloaded successfully")