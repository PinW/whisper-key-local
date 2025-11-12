#!/usr/bin/env python3

import logging
import os
import signal
import sys
import threading

from .config_manager import ConfigManager
from .audio_recorder import AudioRecorder
from .hotkey_listener import HotkeyListener
from .whisper_engine import WhisperEngine
from .voice_activity_detection import VadManager
from .clipboard_manager import ClipboardManager
from .state_manager import StateManager
from .system_tray import SystemTray
from .audio_feedback import AudioFeedback
from .console_manager import ConsoleManager
from .instance_manager import guard_against_multiple_instances
from .utils import beautify_hotkey, OptionalComponent, get_user_app_data_path

def is_built_executable():
    return getattr(sys, 'frozen', False) and hasattr(sys, '_MEIPASS')

def setup_logging(config_manager: ConfigManager):
    log_config = config_manager.get_logging_config()
    
    root_logger = logging.getLogger()
    root_logger.setLevel(logging.DEBUG)  # Set to lowest level, handlers will filter
    
    root_logger.handlers.clear()
    
    formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    
    if log_config['file']['enabled']:
        whisperkey_dir = get_user_app_data_path()
        log_file_path = os.path.join(whisperkey_dir, log_config['file']['filename'])
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

def setup_exception_handler():
    def exception_handler(exc_type, exc_value, exc_traceback):
        if issubclass(exc_type, KeyboardInterrupt):
            sys.__excepthook__(exc_type, exc_value, exc_traceback)
            return
        
        logging.getLogger().error("Uncaught exception", 
                                 exc_info=(exc_type, exc_value, exc_traceback))
    
    sys.excepthook = exception_handler

def setup_audio_recorder(audio_config, state_manager, vad_manager):
    return AudioRecorder(
        channels=audio_config['channels'],
        dtype=audio_config['dtype'],
        max_duration=audio_config['max_duration'],
        on_max_duration_reached=state_manager.handle_max_recording_duration_reached,
        on_vad_event=state_manager.handle_vad_event,
        vad_manager=vad_manager,
        device=audio_config['input_device']
    )

def setup_vad(vad_config):
    return VadManager(
        vad_precheck_enabled=vad_config['vad_precheck_enabled'],
        vad_realtime_enabled=vad_config['vad_realtime_enabled'],
        vad_onset_threshold=vad_config['vad_onset_threshold'],
        vad_offset_threshold=vad_config['vad_offset_threshold'],
        vad_min_speech_duration=vad_config['vad_min_speech_duration'],
        vad_silence_timeout_seconds=vad_config['vad_silence_timeout_seconds']
    )

def setup_whisper_engine(whisper_config, vad_manager):
    return WhisperEngine(
        model_size=whisper_config['model_size'],
        device=whisper_config['device'],
        compute_type=whisper_config['compute_type'],
        language=whisper_config['language'],
        beam_size=whisper_config['beam_size'],
        vad_manager=vad_manager
    )

def setup_clipboard_manager(clipboard_config):
    return ClipboardManager(
        key_simulation_delay=clipboard_config['key_simulation_delay'],
        auto_paste=clipboard_config['auto_paste'],
        preserve_clipboard=clipboard_config['preserve_clipboard']
    )

def setup_audio_feedback(audio_feedback_config):
    return AudioFeedback(
        enabled=audio_feedback_config['enabled'],
        start_sound=audio_feedback_config['start_sound'],
        stop_sound=audio_feedback_config['stop_sound'],
        cancel_sound=audio_feedback_config['cancel_sound']
    )

def setup_console_manager(console_config, is_executable_mode):
    return ConsoleManager(
        config=console_config,
        is_executable_mode=is_executable_mode
    )

def setup_system_tray(tray_config, config_manager, state_manager=None):
    return SystemTray(
        state_manager=state_manager,
        tray_config=tray_config,
        config_manager=config_manager
    )

def setup_signal_handlers(shutdown_event):
    def signal_handler(signum, frame):
        shutdown_event.set()
    
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)

def setup_hotkey_listener(hotkey_config, state_manager):
    return HotkeyListener(
        state_manager=state_manager,
        recording_hotkey=hotkey_config['recording_hotkey'],
        auto_enter_hotkey=hotkey_config.get('auto_enter_combination'),
        auto_enter_enabled=hotkey_config.get('auto_enter_enabled', True),
        stop_with_modifier_enabled=hotkey_config.get('stop_with_modifier_enabled', False),
        cancel_combination=hotkey_config.get('cancel_combination')
    )

def shutdown_app(hotkey_listener: HotkeyListener, state_manager: StateManager, logger: logging.Logger):
    # Stop hotkey listener first to prevent new events during shutdown
    try:
        if hotkey_listener and hotkey_listener.is_active():
            logger.info("Stopping hotkey listener...")
            hotkey_listener.stop_listening()
    except Exception as ex:
        logger.error(f"Error stopping hotkey listener: {ex}")
    
    if state_manager:
        state_manager.shutdown()

def main():   
    mutex_handle = guard_against_multiple_instances()
    
    print("Starting Whisper Key... Local Speech-to-Text App...")
    
    shutdown_event = threading.Event()
    setup_signal_handlers(shutdown_event)
    
    hotkey_listener = None
    state_manager = None
    logger = None
    
    try:
        config_manager = ConfigManager()
        setup_logging(config_manager)
        logger = logging.getLogger(__name__)
        setup_exception_handler()
        
        whisper_config = config_manager.get_whisper_config()
        audio_config = config_manager.get_audio_config()
        hotkey_config = config_manager.get_hotkey_config()
        clipboard_config = config_manager.get_clipboard_config()
        tray_config = config_manager.get_system_tray_config()
        audio_feedback_config = config_manager.get_audio_feedback_config()
        vad_config = config_manager.get_vad_config()
        console_config = config_manager.get_console_config()

        is_executable = is_built_executable()
        console_manager = setup_console_manager(console_config, is_executable)

        vad_manager = setup_vad(vad_config)
        whisper_engine = setup_whisper_engine(whisper_config, vad_manager)
        clipboard_manager = setup_clipboard_manager(clipboard_config)
        audio_feedback = setup_audio_feedback(audio_feedback_config)

        state_manager = StateManager(
            audio_recorder=None,
            whisper_engine=whisper_engine,
            clipboard_manager=clipboard_manager,
            console_manager=console_manager,
            system_tray=None,
            config_manager=config_manager,
            audio_feedback=audio_feedback,
            vad_manager=vad_manager
        )
        audio_recorder = setup_audio_recorder(audio_config, state_manager, vad_manager)
        system_tray = setup_system_tray(tray_config, config_manager, state_manager)
        state_manager.audio_recorder = audio_recorder
        state_manager.system_tray = OptionalComponent(system_tray)
        
        hotkey_listener = setup_hotkey_listener(hotkey_config, state_manager)
        
        system_tray.start()

        print(f"🚀 Application ready! Press {beautify_hotkey(hotkey_config['recording_hotkey'])} to start recording.")
        print("Press Ctrl+C to quit.")

        while not shutdown_event.wait(timeout=0.1):
            pass
            
    except KeyboardInterrupt:
        logger.info("Application shutting down...")
        print("\nShutting down application...")
        
    except Exception as e:
        logger.error(f"Unexpected error: {e}")
        print(f"Error occurred: {e}")
        
    finally:
        shutdown_app(hotkey_listener, state_manager, logger)

if __name__ == "__main__":
    main()