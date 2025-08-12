#!/usr/bin/env python3

import logging
import os
import time
from src.config_manager import ConfigManager
from src.audio_recorder import AudioRecorder
from src.hotkey_listener import HotkeyListener
from src.whisper_engine import WhisperEngine
from src.clipboard_manager import ClipboardManager
from src.state_manager import StateManager
from src.system_tray import SystemTray
from src.audio_feedback import AudioFeedback
from src.instance_manager import guard_against_multiple_instances
from src.utils import beautify_hotkey, OptionalComponent, resolve_asset_path

def setup_logging(config_manager: ConfigManager):
    log_config = config_manager.get_logging_config()
    
    root_logger = logging.getLogger()
    root_logger.setLevel(logging.DEBUG)  # Set to lowest level, handlers will filter
    
    root_logger.handlers.clear()
    
    formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    
    if log_config['file']['enabled']:
        log_file_path = resolve_asset_path(log_config['file']['filename'])
        file_handler = logging.FileHandler(log_file_path, encoding='utf-8')
        file_handler.setLevel(getattr(logging, log_config['level']))
        file_handler.setFormatter(formatter)
        root_logger.addHandler(file_handler)
    
    if log_config['console']['enabled']:
        console_handler = logging.StreamHandler()
        console_level = log_config['console'].get('level', 'WARNING')
        console_handler.setLevel(getattr(logging, console_level))
        console_handler.setFormatter(formatter)
        root_logger.addHandler(console_handler)

def setup_audio_recorder(audio_config):
    return AudioRecorder(
        channels=audio_config['channels'],
        dtype=audio_config['dtype'],
        max_duration=audio_config['max_duration']
    )

def setup_whisper_engine(whisper_config):
    return WhisperEngine(
        model_size=whisper_config['model_size'],
        device=whisper_config['device'],
        compute_type=whisper_config['compute_type'],
        language=whisper_config['language'],
        beam_size=whisper_config['beam_size'],
        vad_enabled=whisper_config['vad_precheck_enabled']
    )

def setup_clipboard_manager(clipboard_config):
    return ClipboardManager(
        key_simulation_delay=clipboard_config['key_simulation_delay'],
        auto_paste=clipboard_config['auto_paste'],
        paste_method=clipboard_config['paste_method']
    )

def setup_audio_feedback(audio_feedback_config):
    return AudioFeedback(
        enabled=audio_feedback_config['enabled'],
        start_sound=audio_feedback_config['start_sound'],
        stop_sound=audio_feedback_config['stop_sound']
    )

def setup_system_tray(tray_config, hotkey_config, config_manager, state_manager=None):
    return SystemTray(
        state_manager=state_manager,
        tray_config=tray_config,
        hotkey_config=hotkey_config,
        config_manager=config_manager
    )


def setup_hotkey_listener(hotkey_config, state_manager):
    return HotkeyListener(
        state_manager=state_manager,
        hotkey=hotkey_config['combination'],
        auto_enter_hotkey=hotkey_config.get('auto_enter_combination'),
        auto_enter_enabled=hotkey_config.get('auto_enter_enabled', True),
        stop_with_modifier_enabled=hotkey_config.get('stop_with_modifier_enabled', False)
    )

def shutdown_app(hotkey_listener: HotkeyListener, state_manager: StateManager, logger: logging.Logger):
    # Stop hotkey listener first to prevent new events during shutdown
    try:
        if 'hotkey_listener' in locals() and hotkey_listener.is_active():
            logger.info("Stopping hotkey listener...")
            hotkey_listener.stop_listening()
    except Exception as ex:
        logger.error(f"Error stopping hotkey listener: {ex}")
    
    try:
        state_manager.shutdown()
    except:
        pass  # StateManager may not be initialized if error occurred early

def main():   
    guard_against_multiple_instances()
    
    print("Starting Whisper Key... Local Speech-to-Text App...")
    
    try:
        config_manager = ConfigManager()
        setup_logging(config_manager)
        logger = logging.getLogger(__name__)
        
        whisper_config = config_manager.get_whisper_config()
        audio_config = config_manager.get_audio_config()
        hotkey_config = config_manager.get_hotkey_config()
        clipboard_config = config_manager.get_clipboard_config()
        tray_config = config_manager.get_system_tray_config()
        audio_feedback_config = config_manager.get_audio_feedback_config()
               
        audio_recorder = setup_audio_recorder(audio_config)      
        whisper_engine = setup_whisper_engine(whisper_config)
        clipboard_manager = setup_clipboard_manager(clipboard_config)
        audio_feedback = setup_audio_feedback(audio_feedback_config)

        state_manager = StateManager(
            audio_recorder=audio_recorder,
            whisper_engine=whisper_engine,
            clipboard_manager=clipboard_manager,
            clipboard_config=clipboard_config,
            system_tray=None,  # OptionalComponent will handle this safely
            config_manager=config_manager,
            audio_feedback=audio_feedback
        )
        system_tray = setup_system_tray(tray_config, hotkey_config, config_manager, state_manager)
        state_manager.system_tray = OptionalComponent(system_tray)
        
        hotkey_listener = setup_hotkey_listener(hotkey_config, state_manager)
        
        if system_tray.is_available():
            system_tray.start()
        
        print(f"🚀 Application ready! Press {beautify_hotkey(hotkey_config['combination'])} to start recording.")        
        print("Press Ctrl+C to quit.")
        
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
        logger.error(f"Unexpected error: {e}")
        print(f"Error occurred: {e}")
        
    finally:
        shutdown_app(hotkey_listener, state_manager, logger)

if __name__ == "__main__":
    main()