#!/usr/bin/env python3
"""
Main application entry point for Windows Whisper Speech-to-Text App

This is the main file that starts our application. It coordinates all the 
different components (audio recording, hotkeys, transcription, etc.) working together.

For beginners: This file is like the "conductor" of an orchestra - it doesn't 
play music itself, but tells all the musicians (our modules) when to start and stop.
"""

import logging
import time
import warnings
from src.config_manager import ConfigManager
from src.audio_recorder import AudioRecorder
from src.hotkey_listener import HotkeyListener
from src.whisper_engine import WhisperEngine
from src.clipboard_manager import ClipboardManager
from src.state_manager import StateManager
from src.system_tray import SystemTray

def setup_logging(config_manager: ConfigManager):
    """
    Configure logging based on configuration settings
    
    Logging is like leaving breadcrumbs - it helps us understand what our 
    program is doing and find problems when they occur.
    """
    log_config = config_manager.get_logging_config()
    
    # Create root logger
    root_logger = logging.getLogger()
    root_logger.setLevel(logging.DEBUG)  # Set to lowest level, handlers will filter
    
    # Clear any existing handlers
    root_logger.handlers.clear()
    
    # Create formatter
    formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    
    # Add file handler if enabled
    if log_config['file']['enabled']:
        file_handler = logging.FileHandler(log_config['file']['filename'])
        file_handler.setLevel(getattr(logging, log_config['level']))
        file_handler.setFormatter(formatter)
        root_logger.addHandler(file_handler)
    
    # Add console handler if enabled with separate level
    if log_config['console']['enabled']:
        console_handler = logging.StreamHandler()
        console_level = log_config['console'].get('level', 'WARNING')  # Default to WARNING if not set
        console_handler.setLevel(getattr(logging, console_level))
        console_handler.setFormatter(formatter)
        root_logger.addHandler(console_handler)

def main():
    """
    Main application function that ties everything together
    """
    print("Starting Whisper Key... Windows Whisper Speech-to-Text App...")
    
    try:
        # Load configuration first (will use user settings from AppData)
        print("Loading configuration...")
        config_manager = ConfigManager()
        
        
        # Show where settings are loaded from
        if config_manager.use_user_settings:
            settings_path = config_manager.get_user_settings_path()
            print(f"📁 Using user settings from: {settings_path}")
        else:
            print(f"📁 Using default settings from: {config_manager.config_path}")
        
        # Set up logging based on configuration
        setup_logging(config_manager)
        logger = logging.getLogger(__name__)
        
        # Get configuration for each component
        whisper_config = config_manager.get_whisper_config()
        audio_config = config_manager.get_audio_config()
        hotkey_config = config_manager.get_hotkey_config()
        clipboard_config = config_manager.get_clipboard_config()
        tray_config = config_manager.config.get('system_tray', {})
        
        logger.info("Initializing application components...")
        
        # Create our main components with configuration
        audio_recorder = AudioRecorder(
            sample_rate=audio_config['sample_rate'],
            channels=audio_config['channels'],
            dtype=audio_config['dtype'],
            max_duration=audio_config['max_duration']
        )
        
        whisper_engine = WhisperEngine(
            model_size=whisper_config['model_size'],
            device=whisper_config['device'],
            compute_type=whisper_config['compute_type'],
            language=whisper_config['language'],
            beam_size=whisper_config['beam_size']
        )
        
        clipboard_manager = ClipboardManager()
        
        # Initialize system tray (optional - may not be available)
        system_tray = None
        if tray_config.get('enabled', True):  # Default to enabled
            try:
                logger.debug("Initializing system tray...")
                logger.debug(f"Tray config: {tray_config}")
                logger.debug(f"Hotkey config: {hotkey_config}")
                logger.debug(f"Config manager type: {type(config_manager)}")
                
                # Create tray with reference to full configuration for hotkey display
                tray_full_config = {
                    'hotkey': hotkey_config,
                    'system_tray': tray_config
                }
                logger.debug(f"Creating SystemTray with config: {tray_full_config}")
                
                system_tray = SystemTray(state_manager=None, config=tray_full_config, config_manager=config_manager)
                logger.debug("SystemTray object created")
                
                if system_tray.is_available():
                    logger.info("System tray initialized successfully")
                else:
                    logger.warning("System tray dependencies not available")
                    print("⚠️  System tray not available (pystray/Pillow not installed)")
                    system_tray = None
                    
            except Exception as e:
                logger.error(f"Failed to initialize system tray: {e}")
                import traceback
                logger.error(f"SystemTray initialization traceback: {traceback.format_exc()}")
                print(f"⚠️  System tray initialization failed: {e}")
                system_tray = None
        else:
            logger.info("System tray disabled in configuration")
            print("📟 System tray disabled in configuration")
        
        # The state manager coordinates everything
        state_manager = StateManager(
            audio_recorder=audio_recorder,
            whisper_engine=whisper_engine,
            clipboard_manager=clipboard_manager,
            clipboard_config=clipboard_config,
            system_tray=system_tray,
            config_manager=config_manager
        )
        
        # Set up hotkey listener (this detects when you press the recording key)
        hotkey_listener = HotkeyListener(
            state_manager=state_manager,
            hotkey=hotkey_config['combination'],
            auto_enter_hotkey=hotkey_config.get('auto_enter_combination'),
            auto_enter_enabled=hotkey_config.get('auto_enter_enabled', True),
            stop_with_modifier_enabled=hotkey_config.get('stop_with_modifier_enabled', False)
        )
        
        # Start system tray if available
        if system_tray:
            try:
                logger.debug("Setting state_manager reference on system_tray")
                # Set state manager reference for tray to access app status
                system_tray.state_manager = state_manager
                logger.debug("Starting system tray...")
                
                tray_started = system_tray.start()
                if tray_started:
                    logger.info("System tray started successfully")
                    print("🔄 System tray icon is now running")
                else:
                    logger.warning("Failed to start system tray")
                    print("⚠️  System tray failed to start")
                    
            except Exception as e:
                logger.error(f"Exception during system tray start: {e}")
                import traceback
                logger.error(f"SystemTray start traceback: {traceback.format_exc()}")
                print(f"⚠️  System tray start failed with exception: {e}")
        
        logger.info("All components initialized successfully!")
        print(f"Application ready! Press {hotkey_config['combination'].upper().replace('+', ' + ')} to start recording.")
        
        # Show auto-paste status
        if clipboard_config.get('auto_paste', False):
            paste_method = clipboard_config.get('paste_method', 'key_simulation')
            method_name = "key simulation (Ctrl+V)" if paste_method == "key_simulation" else "Windows API"
            print(f"🚀 Auto-paste is ENABLED using {method_name}")
        else:
            print("📋 Auto-paste is DISABLED - you'll need to paste manually with Ctrl+V")
        
        print("Press Ctrl+C to quit.")
        
        # Keep the application running
        # This is called a "main loop" - the program stays alive waiting for events
        while True:
            time.sleep(0.1)  # Small pause to prevent using too much CPU
            
            # Keep reference to hotkey_listener so it doesn't get garbage collected
            if not hotkey_listener.is_active():
                logger.error("Hotkey listener stopped unexpectedly!")
                break
            
    except KeyboardInterrupt:
        # This happens when user presses Ctrl+C
        logger.info("Application shutting down...")
        print("\nShutting down application...")
        
        # Stop hotkey listener first to prevent new events during shutdown
        try:
            if 'hotkey_listener' in locals() and hotkey_listener.is_active():
                logger.info("Stopping hotkey listener...")
                hotkey_listener.stop_listening()
        except Exception as e:
            logger.error(f"Error stopping hotkey listener: {e}")
        
        # Clean shutdown of state manager (includes system tray)
        try:
            state_manager.shutdown()
        except:
            pass  # StateManager may not be initialized if error occurred early
        
    except Exception as e:
        # This catches any unexpected errors
        logger.error(f"Unexpected error: {e}")
        print(f"Error occurred: {e}")
        
        # Stop hotkey listener first to prevent new events during shutdown
        try:
            if 'hotkey_listener' in locals() and hotkey_listener.is_active():
                logger.info("Stopping hotkey listener...")
                hotkey_listener.stop_listening()
        except Exception as ex:
            logger.error(f"Error stopping hotkey listener: {ex}")
        
        # Clean shutdown on error
        try:
            state_manager.shutdown()
        except:
            pass  # StateManager may not be initialized if error occurred early

if __name__ == "__main__":
    # This line means "only run main() if this file is executed directly"
    # It's a Python convention you'll see everywhere
    main()