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
from src.audio_recorder import AudioRecorder
from src.hotkey_listener import HotkeyListener
from src.whisper_engine import WhisperEngine
from src.clipboard_manager import ClipboardManager
from src.state_manager import StateManager

def setup_logging():
    """
    Configure logging to help us debug issues
    
    Logging is like leaving breadcrumbs - it helps us understand what our 
    program is doing and find problems when they occur.
    """
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.FileHandler('whisper_app.log'),
            logging.StreamHandler()  # This prints to console too
        ]
    )

def main():
    """
    Main application function that ties everything together
    """
    print("Starting Windows Whisper Speech-to-Text App...")
    print("This is a learning project - we'll explain each step!")
    
    # Set up logging first so we can track what happens
    setup_logging()
    logger = logging.getLogger(__name__)
    
    try:
        # Initialize all our components
        # Think of this like setting up all the tools before starting work
        
        logger.info("Initializing application components...")
        
        # Create our main components (we'll build these next)
        audio_recorder = AudioRecorder()
        whisper_engine = WhisperEngine()
        clipboard_manager = ClipboardManager()
        
        # The state manager coordinates everything
        state_manager = StateManager(
            audio_recorder=audio_recorder,
            whisper_engine=whisper_engine,
            clipboard_manager=clipboard_manager
        )
        
        # Set up hotkey listener (this detects when you press the recording key)
        hotkey_listener = HotkeyListener(state_manager=state_manager)
        
        logger.info("All components initialized successfully!")
        print("Application ready! Press Ctrl+Shift+Space to start recording.")
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