#!/usr/bin/env python3

from .utils import setup_portaudio_path
setup_portaudio_path()

import argparse
import logging
import os
import signal
import sys
import threading

sys.stdout.reconfigure(encoding='utf-8', errors='replace')
sys.stdout.write("\033]0;Whisper Key\007")
sys.stdout.flush()

from .platform import app, permissions
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
from .model_registry import ModelRegistry
from .streaming_manager import StreamingManager
from .voice_commands import VoiceCommandManager
from .utils import get_user_app_data_path, get_version

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

def setup_audio_recorder(audio_config, state_manager, vad_manager, streaming_manager):
    return AudioRecorder(
        channels=audio_config['channels'],
        dtype=audio_config['dtype'],
        max_duration=audio_config['max_duration'],
        on_max_duration_reached=state_manager.handle_max_recording_duration_reached,
        on_vad_event=state_manager.handle_vad_event,
        vad_manager=vad_manager,
        streaming_manager=streaming_manager,
        on_streaming_result=state_manager.handle_streaming_result,
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

def setup_streaming(streaming_config, model_registry):
    return StreamingManager(
        streaming_enabled=streaming_config.get('streaming_enabled', False),
        streaming_model=streaming_config.get('streaming_model', 'standard'),
        model_registry=model_registry
    )

def setup_whisper_engine(whisper_config, vad_manager, model_registry):
    return WhisperEngine(
        model_key=whisper_config['model'],
        device=whisper_config['device'],
        compute_type=whisper_config['compute_type'],
        language=whisper_config['language'],
        beam_size=whisper_config['beam_size'],
        vad_manager=vad_manager,
        model_registry=model_registry
    )

def setup_clipboard_manager(clipboard_config):
    return ClipboardManager(
        auto_paste=clipboard_config['auto_paste'],
        delivery_method=clipboard_config['delivery_method'],
        paste_hotkey=clipboard_config['paste_hotkey'],
        paste_pre_paste_delay=clipboard_config['paste_pre_paste_delay'],
        paste_preserve_clipboard=clipboard_config['paste_preserve_clipboard'],
        paste_clipboard_restore_delay=clipboard_config['paste_clipboard_restore_delay'],
        type_also_copy_to_clipboard=clipboard_config['type_also_copy_to_clipboard'],
        type_auto_enter_delay=clipboard_config['type_auto_enter_delay'],
        type_auto_enter_delay_per_100_chars=clipboard_config['type_auto_enter_delay_per_100_chars'],
        macos_key_simulation_delay=clipboard_config['macos_key_simulation_delay']
    )

def setup_audio_feedback(audio_feedback_config):
    return AudioFeedback(
        enabled=audio_feedback_config['enabled'],
        start_sound=audio_feedback_config['start_sound'],
        stop_sound=audio_feedback_config['stop_sound'],
        cancel_sound=audio_feedback_config['cancel_sound']
    )

def setup_voice_commands(voice_commands_config):
    return VoiceCommandManager(
        enabled=voice_commands_config['enabled']
    )

def setup_console_manager(console_config, is_executable_mode):
    return ConsoleManager(
        config=console_config,
        is_executable_mode=is_executable_mode
    )

def setup_system_tray(tray_config, config_manager, state_manager, model_registry):
    return SystemTray(
        state_manager=state_manager,
        tray_config=tray_config,
        config_manager=config_manager,
        model_registry=model_registry
    )

def setup_signal_handlers(shutdown_event):
    def signal_handler(signum, frame):
        shutdown_event.set()

    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)

def setup_hotkey_listener(hotkey_config, state_manager, voice_commands_enabled=True):
    return HotkeyListener(
        state_manager=state_manager,
        recording_hotkey=hotkey_config['recording_hotkey'],
        stop_key=hotkey_config['stop_key'],
        auto_send_key=hotkey_config.get('auto_send_key'),
        cancel_combination=hotkey_config.get('cancel_combination'),
        command_hotkey=hotkey_config.get('command_hotkey') if voice_commands_enabled else None
    )

def shutdown_app(hotkey_listener: HotkeyListener, state_manager: StateManager, logger: logging.Logger):
    try:
        if hotkey_listener and hotkey_listener.is_active():
            logger.info("Stopping hotkey listener...")
            hotkey_listener.stop_listening()
    except Exception as ex:
        logger.error(f"Error stopping hotkey listener: {ex}")

    if state_manager:
        state_manager.shutdown()

def main():
    app.setup()

    parser = argparse.ArgumentParser()
    parser.add_argument('--test', action='store_true', help='Run as separate test instance')
    args = parser.parse_args()

    instance_name = "WhisperKeyLocal_test" if args.test else "WhisperKeyLocal"
    mutex_handle = guard_against_multiple_instances(instance_name)

    mode_label = " [TEST]" if args.test else ""
    print(f"Starting Whisper Key [{get_version()}]{mode_label}... Local Speech-to-Text App...")
    
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
        streaming_config = config_manager.get_streaming_config()
        voice_commands_config = config_manager.get_voice_commands_config()

        is_executable = is_built_executable()
        console_manager = setup_console_manager(console_config, is_executable)

        model_registry = ModelRegistry(
            whisper_models_config=whisper_config.get('models', {}),
            streaming_models_config=streaming_config.get('models', {})
        )
        vad_manager = setup_vad(vad_config)
        streaming_manager = setup_streaming(streaming_config, model_registry)
        whisper_engine = setup_whisper_engine(whisper_config, vad_manager, model_registry)
        streaming_manager.initialize()
        clipboard_manager = setup_clipboard_manager(clipboard_config)
        audio_feedback = setup_audio_feedback(audio_feedback_config)
        voice_command_manager = setup_voice_commands(voice_commands_config)

        state_manager = StateManager(
            audio_recorder=None,
            whisper_engine=whisper_engine,
            clipboard_manager=clipboard_manager,
            console_manager=console_manager,
            system_tray=None,
            config_manager=config_manager,
            audio_feedback=audio_feedback,
            vad_manager=vad_manager,
            voice_command_manager=voice_command_manager
        )
        audio_recorder = setup_audio_recorder(audio_config, state_manager, vad_manager, streaming_manager)
        system_tray = setup_system_tray(tray_config, config_manager, state_manager, model_registry)
        state_manager.attach_components(audio_recorder, system_tray)
        
        hotkey_listener = setup_hotkey_listener(hotkey_config, state_manager, voice_commands_config['enabled'])

        system_tray.start()

        if clipboard_config['auto_paste']:
            if not permissions.check_accessibility_permission():
                if not permissions.handle_missing_permission(config_manager):
                    app.run_event_loop(shutdown_event)
                    return
                clipboard_manager.update_auto_paste(False)

        print("🚀 Whisper Key ready!")
        config_manager.print_startup_hotkey_instructions()
        print("   [CTRL+C] to quit", flush=True)

        app.run_event_loop(shutdown_event)
            
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
