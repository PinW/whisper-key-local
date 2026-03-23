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
from .audio_stream import AudioStreamManager
from .audio_recorder import AudioRecorder
from .hotkey_listener import HotkeyListener
from .whisper_engine import WhisperEngine
from .voice_activity_detection import VadManager
from .clipboard_manager import ClipboardManager
from .state_manager import StateManager, ListeningMode
from .continuous_listener import ContinuousListener
from .realtime_preview import RealtimePreview
from .system_tray import SystemTray
from .audio_feedback import AudioFeedback
from .instance_manager import guard_against_multiple_instances
from .model_registry import ModelRegistry
from .streaming_manager import StreamingManager
from .voice_commands import VoiceCommandManager
from .hardware_detection import detect_and_print as detect_hardware
from .onboarding import check_gpu
from .update_checker import check_for_updates
from .http_trigger import HttpTrigger
from .wake_word import HAS_OPENWAKEWORD, HAS_PORCUPINE, OpenWakeWordEngine, PorcupineEngine, WakeWordManager
from .preview_overlay import PreviewOverlay
from .utils import get_user_app_data_path, get_version

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

def setup_audio_recorder(audio_config, audio_stream_manager, state_manager, vad_manager, streaming_manager):
    return AudioRecorder(
        audio_stream_manager=audio_stream_manager,
        max_duration=audio_config['max_duration'],
        on_max_duration_reached=state_manager.handle_max_recording_duration_reached,
        on_vad_event=state_manager.handle_vad_event,
        vad_manager=vad_manager,
        streaming_manager=streaming_manager,
        on_streaming_result=state_manager.handle_streaming_result,
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

def setup_whisper_engine(whisper_config, vad_manager, model_registry, log_transcriptions=False):
    return WhisperEngine(
        model_key=whisper_config['model'],
        device=whisper_config['device'],
        compute_type=whisper_config['compute_type'],
        language=whisper_config['language'],
        beam_size=whisper_config['beam_size'],
        initial_prompt=whisper_config.get('initial_prompt', ''),
        hotwords=whisper_config.get('hotwords', []),
        vad_manager=vad_manager,
        model_registry=model_registry,
        log_transcriptions=log_transcriptions
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
        transcription_complete_enabled=audio_feedback_config['transcription_complete_enabled'],
        start_sound=audio_feedback_config['start_sound'],
        stop_sound=audio_feedback_config['stop_sound'],
        cancel_sound=audio_feedback_config['cancel_sound'],
        transcription_complete_sound=audio_feedback_config['transcription_complete_sound']
    )

def setup_voice_commands(voice_commands_config, clipboard_manager, log_transcriptions=False):
    return VoiceCommandManager(
        enabled=voice_commands_config['enabled'],
        clipboard_manager=clipboard_manager,
        log_transcriptions=log_transcriptions
    )

def setup_system_tray(tray_config, config_manager, state_manager, model_registry):
    return SystemTray(
        state_manager=state_manager,
        tray_config=tray_config,
        config_manager=config_manager,
        model_registry=model_registry
    )

def setup_wake_word_engine(wake_word_config, logger):
    engine_name = wake_word_config.get('engine', 'openwakeword')

    if engine_name == 'openwakeword':
        if not HAS_OPENWAKEWORD:
            logger.warning("openwakeword not installed — wake word unavailable")
            return None
        try:
            oww_config = wake_word_config.get('openwakeword', {})
            model_paths = oww_config.get('model_paths', []) or None
            threshold = oww_config.get('threshold', 0.5)
            return OpenWakeWordEngine(model_paths=model_paths, threshold=threshold)
        except Exception as e:
            logger.error(f"Failed to initialize OpenWakeWord engine: {e}")
            return None

    elif engine_name == 'porcupine':
        if not HAS_PORCUPINE:
            logger.warning("pvporcupine not installed — wake word unavailable")
            return None
        try:
            pv_config = wake_word_config.get('porcupine', {})
            access_key = pv_config.get('access_key', '')
            if not access_key:
                logger.warning("Porcupine access_key not configured — wake word unavailable")
                return None
            return PorcupineEngine(
                access_key=access_key,
                keyword_paths=pv_config.get('keyword_paths', []) or None,
                keywords=pv_config.get('keywords', []) or None,
                sensitivities=pv_config.get('sensitivities', []) or None,
            )
        except Exception as e:
            logger.error(f"Failed to initialize Porcupine engine: {e}")
            return None

    else:
        logger.warning(f"Unknown wake word engine: {engine_name}")
        return None

def run_gpu_onboarding(config_manager, whisper_config):
    gpu_status = config_manager.config.get('onboarding', {}).get('gpu', 'pending')
    if gpu_status != 'pending':
        return whisper_config
    gpu_class, gpu_name, ct2_works = detect_hardware(whisper_config['device'])
    check_gpu(gpu_class, gpu_name, ct2_works, whisper_config['device'], config_manager)
    return config_manager.get_whisper_config()


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
    parser.add_argument('--mode', choices=['hotkey', 'continuous', 'wake_word'], default=None)
    parser.add_argument('--preview', action='store_true', default=None)
    args = parser.parse_args()

    instance_name = "WhisperKeyLocal_test" if args.test else "WhisperKeyLocal"
    mutex_handle = guard_against_multiple_instances(instance_name)

    mode_label = " [TEST]" if args.test else ""
    print(f"Starting Whisper Key [{get_version()}]{mode_label}...")
    
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

        check_for_updates(config_manager, test_mode=args.test)

        whisper_config = config_manager.get_whisper_config()
        audio_config = config_manager.get_audio_config()
        hotkey_config = config_manager.get_hotkey_config()
        clipboard_config = config_manager.get_clipboard_config()
        tray_config = config_manager.get_system_tray_config()
        audio_feedback_config = config_manager.get_audio_feedback_config()
        vad_config = config_manager.get_vad_config()
        streaming_config = config_manager.get_streaming_config()
        voice_commands_config = config_manager.get_voice_commands_config()
        log_config = config_manager.get_logging_config()
        log_transcriptions = log_config.get('log_transcriptions', False)

        whisper_config = run_gpu_onboarding(config_manager, whisper_config)

        model_registry = ModelRegistry(
            whisper_models_config=whisper_config.get('models', {}),
            streaming_models_config=streaming_config.get('models', {})
        )
        vad_manager = setup_vad(vad_config)
        streaming_manager = setup_streaming(streaming_config, model_registry)
        whisper_engine = setup_whisper_engine(whisper_config, vad_manager, model_registry, log_transcriptions)
        streaming_manager.initialize()
        clipboard_manager = setup_clipboard_manager(clipboard_config)
        audio_feedback = setup_audio_feedback(audio_feedback_config)
        voice_command_manager = setup_voice_commands(voice_commands_config, clipboard_manager, log_transcriptions)

        audio_stream_manager = AudioStreamManager(device=audio_config['input_device'])
        listening_config = config_manager.get_listening_config()

        state_manager = StateManager(
            audio_recorder=None,
            whisper_engine=whisper_engine,
            clipboard_manager=clipboard_manager,
            system_tray=None,
            config_manager=config_manager,
            audio_feedback=audio_feedback,
            vad_manager=vad_manager,
            voice_command_manager=voice_command_manager,
            audio_stream_manager=audio_stream_manager,
        )

        continuous_listener = ContinuousListener(
            audio_stream_manager=audio_stream_manager,
            vad_manager=vad_manager,
            on_speech_audio=state_manager.handle_continuous_audio,
            is_busy=state_manager.is_busy,
            pre_buffer_duration_sec=listening_config.get('pre_buffer_duration_sec', 0.3),
            post_speech_silence_ms=listening_config.get('post_speech_silence_ms', 800),
            max_speech_duration_sec=listening_config.get('max_speech_duration_sec', 60.0),
            min_speech_duration_sec=listening_config.get('min_speech_duration_sec', 0.5),
        )
        state_manager.continuous_listener = continuous_listener

        realtime_preview = RealtimePreview(
            whisper_engine=whisper_engine,
            audio_stream_manager=audio_stream_manager,
            on_preview_text=state_manager.handle_streaming_result,
            preview_interval_sec=listening_config.get('preview_interval_sec', 1.5),
            preview_max_audio_seconds=listening_config.get('preview_max_audio_seconds', 30.0),
        )
        state_manager.realtime_preview = realtime_preview

        if listening_config.get('preview_show_overlay', False):
            try:
                preview_overlay = PreviewOverlay()
                state_manager.preview_overlay = preview_overlay
            except Exception as e:
                logger.warning(f"Failed to create preview overlay: {e}")

        wake_word_config = config_manager.get_wake_word_config()
        wake_word_engine = setup_wake_word_engine(wake_word_config, logger)
        if wake_word_engine:
            wake_word_manager = WakeWordManager(
                audio_stream_manager=audio_stream_manager,
                vad_manager=vad_manager,
                engine=wake_word_engine,
                on_wake_word=state_manager.handle_wake_word,
                is_busy=state_manager.is_busy,
                cooldown_sec=wake_word_config.get('cooldown_sec', 2.0),
                vad_pre_filter=wake_word_config.get('vad_pre_filter', True),
            )
            state_manager.wake_word_manager = wake_word_manager

        audio_recorder = setup_audio_recorder(audio_config, audio_stream_manager, state_manager, vad_manager, streaming_manager)
        system_tray = setup_system_tray(tray_config, config_manager, state_manager, model_registry)
        state_manager.attach_components(audio_recorder, system_tray)

        if args.mode is not None:
            state_manager.set_listening_mode(ListeningMode(args.mode))
        if args.preview is True:
            state_manager.set_preview_enabled(True)

        http_trigger_config = config_manager.config.get('http_trigger', {})
        if http_trigger_config.get('enabled', True):
            http_host = http_trigger_config.get('host', '0.0.0.0')
            http_port = http_trigger_config.get('port', 5757)
            try:
                http_trigger = HttpTrigger(state_manager, host=http_host, port=http_port)
                http_trigger.start()
            except Exception as e:
                logger.warning(f"Failed to start HTTP trigger: {e}")
                http_trigger = None
        else:
            http_trigger = None

        hotkey_listener = setup_hotkey_listener(hotkey_config, state_manager, voice_commands_config['enabled'])

        system_tray.start()

        if clipboard_config['auto_paste']:
            if not permissions.check_accessibility_permission():
                if not permissions.handle_missing_permission(config_manager):
                    app.run_event_loop(shutdown_event)
                    return
                clipboard_manager.update_auto_paste(False)

        audio_stream_manager.start()

        if state_manager.listening_mode == ListeningMode.CONTINUOUS:
            continuous_listener.activate()

        if state_manager.listening_mode == ListeningMode.WAKE_WORD:
            if state_manager.wake_word_manager:
                state_manager.wake_word_manager.activate()
            else:
                logger.warning("Wake word mode configured but engine unavailable; falling back to hotkey")
                state_manager.listening_mode = ListeningMode.HOTKEY

        if state_manager.preview_enabled:
            realtime_preview.activate()

        print("🚀 Whisper Key ready!")
        config_manager.print_startup_hotkey_instructions()
        if http_trigger:
            print(f"   [HTTP] trigger on http://{http_host}:{http_port}")
        mode_info = state_manager.get_mode_info()
        preview_label = "on" if mode_info["preview"] else "off"
        print(f"   [MODE] {mode_info['mode']} (preview: {preview_label})")
        print("   [CTRL+C] to quit", flush=True)

        app.run_event_loop(shutdown_event)
            
    except KeyboardInterrupt:
        logger.info("Application shutting down...")
        print("\nShutting down application...")
        
    except Exception as e:
        logger.error(f"Unexpected error: {e}", exc_info=True)
        print(f"Error occurred: {e}")
        
    finally:
        shutdown_app(hotkey_listener, state_manager, logger)

if __name__ == "__main__":
    main()
