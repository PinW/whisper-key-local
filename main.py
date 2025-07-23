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
from src.config_manager import ConfigManager
from src.audio_recorder import AudioRecorder
from src.hotkey_listener import HotkeyListener
from src.whisper_engine import WhisperEngine
from src.clipboard_manager import ClipboardManager
from src.state_manager import StateManager

def setup_logging(config_manager: ConfigManager):
    """
    Configure logging based on configuration settings
    
    Logging is like leaving breadcrumbs - it helps us understand what our 
    program is doing and find problems when they occur.
    """
    log_config = config_manager.get_logging_config()
    
    # Set up handlers based on configuration
    handlers = []
    
    # Add file handler if enabled
    if log_config['file']['enabled']:
        handlers.append(logging.FileHandler(log_config['file']['filename']))
    
    # Add console handler if enabled  
    if log_config['console']['enabled']:
        handlers.append(logging.StreamHandler())
    
    # Configure logging
    logging.basicConfig(
        level=getattr(logging, log_config['level']),
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=handlers
    )

def main():
    """
    Main application function that ties everything together
    """
    print("Starting Windows Whisper Speech-to-Text App...")
    print("This is a learning project - we'll explain each step!")
    
    try:
        # Load configuration first
        print("Loading configuration...")
        config_manager = ConfigManager()
        
        # Set up logging based on configuration
        setup_logging(config_manager)
        logger = logging.getLogger(__name__)
        
        # Get configuration for each component
        whisper_config = config_manager.get_whisper_config()
        audio_config = config_manager.get_audio_config()
        hotkey_config = config_manager.get_hotkey_config()
        clipboard_config = config_manager.get_clipboard_config()
        
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
        
        # The state manager coordinates everything
        state_manager = StateManager(
            audio_recorder=audio_recorder,
            whisper_engine=whisper_engine,
            clipboard_manager=clipboard_manager,
            clipboard_config=clipboard_config
        )
        
        # Set up hotkey listener (this detects when you press the recording key)
        hotkey_listener = HotkeyListener(
            state_manager=state_manager,
            hotkey=hotkey_config['combination']
        )
        
        logger.info("All components initialized successfully!")
        print(f"Application ready! Press {hotkey_config['combination'].upper().replace('+', ' + ')} to start recording.")
        
        # Show auto-paste status
        if clipboard_config.get('auto_paste', False):
            print("🚀 Auto-paste is ENABLED - transcribed text will be pasted automatically")
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
        
    except Exception as e:
        # This catches any unexpected errors
        logger.error(f"Unexpected error: {e}")
        print(f"Error occurred: {e}")

if __name__ == "__main__":
    # This line means "only run main() if this file is executed directly"
    # It's a Python convention you'll see everywhere
    main()