import logging
import time
import threading
import platform
from enum import Enum
from typing import Optional

import sounddevice as sd

from .audio_recorder import AudioRecorder
from .audio_stream import AudioStreamManager, WHISPER_SAMPLE_RATE
from .whisper_engine import WhisperEngine
from .clipboard_manager import ClipboardManager
from .system_tray import SystemTray
from .config_manager import ConfigManager
from .audio_feedback import AudioFeedback
from .utils import OptionalComponent
from .voice_activity_detection import VadEvent, VadManager
from .voice_commands import VoiceCommandManager
from .continuous_listener import ContinuousListener
from .realtime_preview import RealtimePreview
from .wake_word import WakeWordManager


class ListeningMode(Enum):
    HOTKEY = "hotkey"
    CONTINUOUS = "continuous"
    WAKE_WORD = "wake_word"

class StateManager:
    def __init__(self,
                 audio_recorder: AudioRecorder,
                 whisper_engine: WhisperEngine,
                 clipboard_manager: ClipboardManager,
                 config_manager: ConfigManager,
                 vad_manager: VadManager,
                 system_tray: Optional[SystemTray] = None,
                 audio_feedback: Optional[AudioFeedback] = None,
                 voice_command_manager: Optional[VoiceCommandManager] = None,
                 audio_stream_manager: Optional[AudioStreamManager] = None,
                 continuous_listener: Optional[ContinuousListener] = None):

        self.audio_recorder = audio_recorder
        self.whisper_engine = whisper_engine
        self.clipboard_manager = clipboard_manager
        self.system_tray = OptionalComponent(system_tray)
        self.config_manager = config_manager
        self.audio_feedback = OptionalComponent(audio_feedback)
        self.vad_manager = vad_manager
        self.voice_command_manager = voice_command_manager
        self.audio_stream_manager = audio_stream_manager
        self.continuous_listener = continuous_listener
        self.realtime_preview = None
        self.wake_word_manager: Optional[WakeWordManager] = None

        self.is_processing = False
        self.is_model_loading = False
        self.last_transcription = None
        self._pending_model_change = None
        self._pending_device_change = None
        self._command_mode = False
        self._state_lock = threading.Lock()
        self._streaming_display_active = False
        self._last_preview_text = ""
        self._preview_active = False
        self.preview_overlay = None

        listening_config = self.config_manager.get_listening_config()
        self.listening_mode = ListeningMode(listening_config.get('mode', 'hotkey'))
        self.preview_enabled = listening_config.get('preview_enabled', False)
        self.preview_show_tooltip = listening_config.get('preview_show_tooltip', True)
        self.preview_show_overlay = listening_config.get('preview_show_overlay', False)

        self.logger = logging.getLogger(__name__)
        self._current_audio_host = None
        self._initialize_audio_host()

    def attach_components(self,
                          audio_recorder: AudioRecorder,
                          system_tray: Optional[SystemTray]):
        self.audio_recorder = audio_recorder
        self.system_tray = OptionalComponent(system_tray)
        self._ensure_audio_device_for_host(self._current_audio_host)
    
    def handle_continuous_audio(self, audio_data):
        self._transcription_pipeline(audio_data, use_auto_enter=False)
        if self.listening_mode == ListeningMode.CONTINUOUS:
            print("   [CONTINUOUS] listening for speech...")

    def handle_wake_word(self):
        self.logger.info("Wake word triggered — starting recording")
        self.start_recording()

    def is_busy(self) -> bool:
        with self._state_lock:
            return self.is_processing or self.is_model_loading or self.audio_recorder.get_recording_status()

    def handle_max_recording_duration_reached(self, audio_data):
        self.logger.info("Max recording duration reached - starting transcription")
        self._transcription_pipeline(audio_data, use_auto_enter=False)

    def handle_vad_event(self, event: VadEvent):
        if event == VadEvent.SILENCE_TIMEOUT:
            self.logger.info("VAD silence timeout detected - stopping recording")
            timeout_seconds = int(self.vad_manager.vad_silence_timeout_seconds)
            self._clear_streaming_display()
            print(f"⏰ Stopping recording after {timeout_seconds} seconds of silence...")
            audio_data = self.audio_recorder.stop_recording()
            self._transcription_pipeline(audio_data, use_auto_enter=False)

    def handle_streaming_result(self, text: str, is_final: bool):
        if is_final:
            self._last_preview_text = text
            self._preview_active = False
            if self._streaming_display_active:
                print(f"\r   {text:<70}")
                self._streaming_display_active = False
            if self.preview_show_tooltip:
                self.system_tray.update_tooltip_preview(None)
            if self.preview_show_overlay and self.preview_overlay:
                self.preview_overlay.update_text(text)
                threading.Timer(2.0, self.preview_overlay.hide).start()
        else:
            self._last_preview_text = text
            self._preview_active = True
            display_text = text if len(text) < 67 else "..." + text[-64:]
            print(f"\r   {display_text:<70}", end="", flush=True)
            self._streaming_display_active = True
            if self.preview_show_tooltip:
                self.system_tray.update_tooltip_preview(text)
            if self.preview_show_overlay and self.preview_overlay:
                self.preview_overlay.update_text(text)

    def get_last_preview_text(self) -> dict:
        return {
            "text": self._last_preview_text,
            "active": self._preview_active,
        }

    def _clear_streaming_display(self):
        if self._streaming_display_active:
            print("\r" + " " * 75 + "\r", end="", flush=True)
            self._streaming_display_active = False
    
    def stop_recording(self, use_auto_enter: bool = False) -> bool:
        currently_recording = self.audio_recorder.get_recording_status()

        if currently_recording:
            self._clear_streaming_display()
            audio_data = self.audio_recorder.stop_recording()
            self._transcription_pipeline(audio_data, use_auto_enter)
            return True
        else:
            return False
    
    def cancel_active_recording(self):
        self._clear_streaming_display()
        self._command_mode = False
        self.audio_recorder.cancel_recording()
        self.audio_feedback.play_cancel_sound()
        self.system_tray.update_state("idle")
    
    def cancel_recording_hotkey_pressed(self) -> bool:
        current_state = self.get_current_state()
        
        if current_state == "recording":
            print("🎤 Recording cancelled!")            
            self.cancel_active_recording()
            return True
        else:
            return False
    
    def start_recording(self):
        if not self.can_start_recording():
            current_state = self.get_current_state()
            if self.is_processing:
                print("⏳ Still processing previous recording...")
            elif self.is_model_loading:
                print("⏳ Still loading model...")
            else:
                print(f"⏳ Cannot record while {current_state}...")
            return

        self._begin_recording()

    def start_command_recording(self):
        if not self.can_start_recording():
            return

        with self._state_lock:
            self._command_mode = True

        self.logger.info("Starting command mode recording")
        success = self.audio_recorder.start_recording()
        if success:
            print("\n🎤 Command mode activated! Speak a command...")
            self.config_manager.print_command_stop_instructions()
            self.audio_feedback.play_start_sound()
            self.system_tray.update_state("recording")

    def _begin_recording(self):
        success = self.audio_recorder.start_recording()

        if success:
            print("\n🎤 Recording started! Speak now...")
            self.config_manager.print_stop_instructions_based_on_config()
            self.audio_feedback.play_start_sound()
            self.system_tray.update_state("recording")
    
    def _transcription_pipeline(self, audio_data, use_auto_enter: bool = False):
        try:
            with self._state_lock:
                self.is_processing = True
                command_mode = self._command_mode
                self._command_mode = False

            self.audio_feedback.play_stop_sound()

            if audio_data is None:
                return

            duration = len(audio_data) / WHISPER_SAMPLE_RATE
            print(f"   ✓ Recorded {duration:.1f} seconds, transcribing...")

            self.system_tray.update_state("processing")

            transcribed_text = self.whisper_engine.transcribe_audio(audio_data)

            if not transcribed_text:
                return

            if command_mode:
                self._handle_command_transcription(transcribed_text, use_auto_enter)
                return

            success = self.clipboard_manager.deliver_transcription(
                transcribed_text, use_auto_enter
            )

            if success:
                self.last_transcription = transcribed_text
                self.audio_feedback.play_transcription_complete_sound()
            
        except Exception as e:
            self.logger.error(f"Error in processing workflow: {e}")
            print(f"❌ Error processing recording: {e}")
        
        finally:
            with self._state_lock:
                self.is_processing = False
                pending_model = self._pending_model_change
                pending_device = self._pending_device_change

            if pending_device:
                device_id, device_name = pending_device
                self.logger.info(f"Executing pending device change to: {device_name}")
                self._execute_audio_device_change(device_id, device_name)
                self._pending_device_change = None

            if pending_model:
                self.logger.info(f"Executing pending model change to: {pending_model}")
                print(f"🔄 Processing complete, now switching to [{pending_model}] model...")
                self._execute_model_change(pending_model)
                self._pending_model_change = None

            if not (pending_device or pending_model):
                self.system_tray.update_state("idle")

    def _handle_command_transcription(self, text: str, use_auto_enter: bool = False):
        log_config = self.config_manager.get_logging_config()
        if log_config.get('log_transcriptions', False):
            self.logger.info(f"Command mode transcription: '{text}'")
        else:
            self.logger.info("Command mode transcription received")

        if not self.voice_command_manager.enabled:
            self.logger.warning("Voice commands disabled")
            return

        matched = self.voice_command_manager.match_command(text)
        if matched:
            self.voice_command_manager.execute_command(matched, use_auto_enter)
        else:
            print("   ✗ No matching command found")

    def set_listening_mode(self, mode: ListeningMode):
        old_mode = self.listening_mode
        self.listening_mode = mode
        self.config_manager.update_listening_mode(mode.value)
        self.logger.info(f"Listening mode changed to {mode.value}")

        if self.continuous_listener:
            if mode == ListeningMode.CONTINUOUS:
                self.continuous_listener.activate()
            elif old_mode == ListeningMode.CONTINUOUS:
                self.continuous_listener.deactivate()

        if self.wake_word_manager:
            if mode == ListeningMode.WAKE_WORD:
                self.wake_word_manager.activate()
            elif old_mode == ListeningMode.WAKE_WORD:
                self.wake_word_manager.deactivate()

        if mode == ListeningMode.WAKE_WORD and not self.wake_word_manager:
            self.logger.warning("Wake word mode requested but no engine available; falling back to hotkey")
            self.listening_mode = ListeningMode.HOTKEY
            self.config_manager.update_listening_mode(ListeningMode.HOTKEY.value)
            print("   [WAKE WORD] engine not available — falling back to hotkey mode")

    def set_preview_enabled(self, enabled: bool):
        old = self.preview_enabled
        self.preview_enabled = enabled
        self.config_manager.update_listening_preview(enabled)
        self.logger.info(f"Preview {'enabled' if enabled else 'disabled'}")
        if self.realtime_preview:
            if enabled and not old:
                self.realtime_preview.activate()
            elif not enabled and old:
                self.realtime_preview.deactivate()

    def set_overlay_enabled(self, enabled: bool):
        self.preview_show_overlay = enabled
        self.config_manager.update_user_setting('listening', 'preview_show_overlay', enabled)
        self.logger.info(f"Overlay {'enabled' if enabled else 'disabled'}")
        if self.preview_overlay:
            if enabled:
                self.preview_overlay.update_config()
            else:
                self.preview_overlay.hide()

    def set_overlay_monitor(self, value):
        self.config_manager.update_overlay_setting('monitor', value)
        self.logger.info(f"Overlay monitor set to {value}")
        if self.preview_overlay and self.preview_show_overlay:
            self.preview_overlay.update_config()

    def set_overlay_position(self, value: str):
        self.config_manager.update_overlay_setting('position', value)
        self.logger.info(f"Overlay position set to {value}")
        if self.preview_overlay and self.preview_show_overlay:
            self.preview_overlay.update_config()

    def get_overlay_config(self) -> dict:
        overlay = self.config_manager.get_overlay_config()
        overlay['overlay_enabled'] = self.preview_show_overlay
        return overlay

    def get_mode_info(self) -> dict:
        return {
            "mode": self.listening_mode.value,
            "preview": self.preview_enabled,
            "overlay": self.preview_show_overlay,
            "overlay_monitor": self.config_manager.get_overlay_config().get('monitor', 'follow_focus'),
        }

    def get_application_state(self) -> dict:
        status = {
            "recording": self.audio_recorder.get_recording_status(),
            "processing": self.is_processing,
            "model_loading": self.is_model_loading,
        }

        return status
    
    def manual_transcribe_test(self, duration_seconds: int = 5):
        try:
            print(f"🎤 Recording for {duration_seconds} seconds...")
            print("Speak now!")
            
            self.audio_recorder.start_recording()
            
            time.sleep(duration_seconds)
            
            audio_data = self.audio_recorder.stop_recording()
            self._transcription_pipeline(audio_data)
            
        except Exception as e:
            self.logger.error(f"Manual test failed: {e}")
            print(f"❌ Test failed: {e}")
    
    def shutdown(self):
        print("Whisper Key is shutting down... goodbye!")

        if self.continuous_listener:
            self.continuous_listener.deactivate()

        if self.wake_word_manager:
            self.wake_word_manager.cleanup()

        if self.audio_recorder.get_recording_status():
            self.audio_recorder.stop_recording()

        if self.audio_stream_manager:
            self.audio_stream_manager.stop()

        self.system_tray.stop()
    
    def set_model_loading(self, loading: bool):
        with self._state_lock:
            old_state = self.is_model_loading
            self.is_model_loading = loading
            
            if old_state != loading:
                if loading:
                    self.system_tray.update_state("processing")
                else:
                    self.system_tray.update_state("idle")
    
    def is_transcription_recording(self) -> bool:
        return self.audio_recorder.get_recording_status() and not self._command_mode

    def can_start_recording(self) -> bool:
        with self._state_lock:
            return not (self.is_processing or self.is_model_loading or self.audio_recorder.get_recording_status())
    
    def get_current_state(self) -> str:
        with self._state_lock:
            if self.is_model_loading:
                return "model_loading"
            elif self.is_processing:
                return "processing"
            elif self.audio_recorder.get_recording_status():
                return "recording"
            else:
                return "idle"
    
    def request_model_change(self, new_model_key: str) -> bool:
        current_state = self.get_current_state()
        
        if new_model_key == self.whisper_engine.model_key:
            return True
        
        if current_state == "model_loading":
            print("⏳ Model already loading, please wait...")
            return False
        
        if current_state == "recording":
            print(f"🎤 Cancelling recording to switch to [{new_model_key}] model...")
            self.cancel_active_recording()
            self._execute_model_change(new_model_key)
            return True
        
        if current_state == "processing":
            print(f"⏳ Queueing model change to [{new_model_key}] until transcription completes...")
            self._pending_model_change = new_model_key
            return True
        
        if current_state == "idle":
            self._execute_model_change(new_model_key)
            return True
        
        self.logger.warning(f"Unexpected state for model change: {current_state}")
        return False
    
    def update_transcription_mode(self, value):
        self.config_manager.update_user_setting('clipboard', 'auto_paste', value)
        self.clipboard_manager.update_auto_paste(value)

    def _execute_model_change(self, new_model_key: str):
        def progress_callback(message: str):
            if "ready" in message.lower() or "already loaded" in message.lower():
                print(f"✅ Successfully switched to [{new_model_key}] model")
                self.set_model_loading(False)
            elif "failed" in message.lower():
                print(f"❌ Failed to change model: {message}")
                self.set_model_loading(False)
            else:
                print(f"🔄 {message}")
                self.set_model_loading(True)
        
        try:
            self.set_model_loading(True)
            print(f"🔄 Switching to [{new_model_key}] model...")
            
            self.whisper_engine.change_model(new_model_key, progress_callback)
            
        except Exception as e:
            self.logger.error(f"Failed to initiate model change: {e}")
            print(f"❌ Failed to change model: {e}")
            self.set_model_loading(False)

    def get_available_audio_devices(self, host_filter: Optional[str] = None):
        host_name = host_filter if host_filter is not None else self._current_audio_host
        return AudioStreamManager.get_available_audio_devices(host_name)

    def get_current_audio_device_id(self):
        return self.audio_stream_manager.get_device_id()

    def get_available_audio_hosts(self):
        try:
            hostapis = sd.query_hostapis()
            devices = sd.query_devices()
        except Exception as e:
            self.logger.error(f"Failed to query audio hosts: {e}")
            return []

        hosts_with_input = {}
        for index, host in enumerate(hostapis):
            hosts_with_input[index] = {
                'name': host['name'],
                'index': index,
                'has_input': False
            }

        for device in devices:
            if device.get('max_input_channels', 0) > 0:
                host_index = device['hostapi']
                if host_index in hosts_with_input:
                    hosts_with_input[host_index]['has_input'] = True

        return [
            {'name': host['name'], 'index': host['index']}
            for host in hosts_with_input.values()
            if host['has_input']
        ]

    def get_current_audio_host(self) -> Optional[str]:
        return self._current_audio_host

    def set_audio_host(self, host_name: str) -> bool:
        if not host_name:
            return False

        available_hosts = self.get_available_audio_hosts()
        normalized_lookup = {host['name'].lower(): host for host in available_hosts}
        host_entry = normalized_lookup.get(host_name.lower())

        if not host_entry:
            self.logger.warning(f"Requested audio host '{host_name}' is not available")
            return False

        canonical_name = host_entry['name']
        if canonical_name == self._current_audio_host:
            return True

        self._current_audio_host = canonical_name
        self.config_manager.update_audio_host(canonical_name)
        self.logger.info(f"Audio host changed to {canonical_name}")

        self._ensure_audio_device_for_host(canonical_name)
        self.system_tray.refresh_menu()
        return True

    def request_audio_device_change(self, device_id: int, device_name: str):
        current_state = self.get_current_state()

        if device_id == self.audio_stream_manager.device:
            return True

        if current_state == "recording":
            print(f"🎤 Cancelling recording to switch audio device...")
            self.cancel_active_recording()
            self._execute_audio_device_change(device_id, device_name)
            return True

        if current_state == "processing":
            print(f"⏳ Queueing audio device change until transcription completes...")
            self._pending_device_change = (device_id, device_name)
            return True

        if current_state == "idle":
            self._execute_audio_device_change(device_id, device_name)
            return True

        self.logger.warning(f"Unexpected state for device change: {current_state}")
        return False

    def _execute_audio_device_change(self, device_id: int, device_name: str):
        try:
            print(f"🎤 Switching to: {device_name}")
            self.audio_stream_manager.restart_stream(
                device=device_id if device_id != -1 else None
            )
            print(f"✅ Successfully switched audio device to: {device_name}")
        except Exception as e:
            self.logger.error(f"Failed to change audio device: {e}")
            print(f"❌ Failed to switch audio device: {e}")

    def _initialize_audio_host(self):
        try:
            configured_host = self.config_manager.get_setting('audio', 'host')
        except KeyError:
            configured_host = None

        available_hosts = self.get_available_audio_hosts()
        resolved_host = self._resolve_audio_host(configured_host, available_hosts)

        self._current_audio_host = resolved_host

        if resolved_host != configured_host:
            self.config_manager.update_audio_host(resolved_host)

    def _resolve_audio_host(self, configured_host: Optional[str], available_hosts):
        if not available_hosts:
            return None

        normalized_lookup = {
            host['name'].lower(): host['name']
            for host in available_hosts
        }

        if configured_host:
            match = normalized_lookup.get(configured_host.lower())
            if match:
                return match

        preferred_host = self._preferred_platform_host()
        if preferred_host:
            preferred_match = normalized_lookup.get(preferred_host.lower())
            if preferred_match:
                return preferred_match

        return available_hosts[0]['name']

    def _preferred_platform_host(self) -> Optional[str]:
        system_name = platform.system().lower()
        if system_name == 'windows':
            return 'WASAPI'
        return None

    def _ensure_audio_device_for_host(self, host_name: Optional[str]):
        if not host_name or not self.audio_stream_manager:
            return

        try:
            current_device_id = self.audio_stream_manager.get_device_id()
        except Exception as e:
            self.logger.error(f"Unable to read current audio device: {e}")
            return

        if self._device_matches_host(current_device_id, host_name):
            return

        fallback_device_id = self._get_default_device_for_host(host_name)
        if fallback_device_id is None:
            self.logger.warning(f"No input devices available for host {host_name}")
            return

        device_name = self._get_device_name(fallback_device_id)
        success = self.request_audio_device_change(fallback_device_id, device_name)

        if not success:
            self.logger.warning(f"Failed to switch to fallback device {fallback_device_id} for host {host_name}")

    def _device_matches_host(self, device_id: int, host_name: str) -> bool:
        try:
            device_info = sd.query_devices(device_id)
            host_info = sd.query_hostapis(device_info['hostapi'])
            return host_info['name'].lower() == host_name.lower()
        except Exception:
            return False

    def _get_default_device_for_host(self, host_name: str) -> Optional[int]:
        try:
            target_index = None
            target_host = None
            hostapis = sd.query_hostapis()
            for idx, host in enumerate(hostapis):
                if host['name'].lower() == host_name.lower():
                    target_index = idx
                    target_host = host
                    break
            else:
                return None

            default_input = target_host.get('default_input_device', -1)
            if default_input is not None and default_input >= 0:
                device_info = sd.query_devices(default_input)
                if device_info.get('max_input_channels', 0) > 0:
                    return default_input

            all_devices = sd.query_devices()
            for idx, device in enumerate(all_devices):
                if device['hostapi'] == target_index and device.get('max_input_channels', 0) > 0:
                    return idx
        except Exception as e:
            self.logger.error(f"Failed to determine default device for host {host_name}: {e}")

        return None

    def _get_device_name(self, device_id: int) -> str:
        try:
            device_info = sd.query_devices(device_id)
            return device_info.get('name', f"Device {device_id}")
        except Exception:
            return f"Device {device_id}"
