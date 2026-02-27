import logging
import time
import threading
import platform
from typing import Optional

import sounddevice as sd

from .audio_recorder import AudioRecorder
from .whisper_engine import WhisperEngine
from .clipboard_manager import ClipboardManager
from .system_tray import SystemTray
from .config_manager import ConfigManager
from .audio_feedback import AudioFeedback
from .console_manager import ConsoleManager
from .utils import OptionalComponent
from .voice_activity_detection import VadEvent, VadManager
from .voice_commands import VoiceCommandManager

class StateManager:
    def __init__(self,
                 audio_recorder: AudioRecorder,
                 whisper_engine: WhisperEngine,
                 clipboard_manager: ClipboardManager,
                 config_manager: ConfigManager,
                 vad_manager: VadManager,
                 console_manager: ConsoleManager,
                 system_tray: Optional[SystemTray] = None,
                 audio_feedback: Optional[AudioFeedback] = None,
                 voice_command_manager: Optional[VoiceCommandManager] = None):

        self.audio_recorder = audio_recorder
        self.whisper_engine = whisper_engine
        self.clipboard_manager = clipboard_manager
        self.console_manager = console_manager
        self.system_tray = OptionalComponent(system_tray)
        self.config_manager = config_manager
        self.audio_feedback = OptionalComponent(audio_feedback)
        self.vad_manager = vad_manager
        self.voice_command_manager = voice_command_manager

        self.is_processing = False
        self.is_model_loading = False
        self.last_transcription = None
        self._pending_model_change = None
        self._pending_device_change = None
        self._command_mode = False
        self._state_lock = threading.Lock()
        self._streaming_display_active = False

        self.logger = logging.getLogger(__name__)
        self._current_audio_host = None
        self._initialize_audio_host()

    def attach_components(self,
                          audio_recorder: AudioRecorder,
                          system_tray: Optional[SystemTray]):
        self.audio_recorder = audio_recorder
        self.system_tray = OptionalComponent(system_tray)
        self._ensure_audio_device_for_host(self._current_audio_host)
    
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
            if self._streaming_display_active:
                print(f"\r   {text:<70}")
                self._streaming_display_active = False
        else:
            display_text = text if len(text) < 67 else "..." + text[-64:]
            print(f"\r   {display_text:<70}", end="", flush=True)
            self._streaming_display_active = True

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
    
    def toggle_recording(self):
        was_recording = self.stop_recording(use_auto_enter=False)
        
        if not was_recording:
            current_state = self.get_current_state()
            if self.can_start_recording():
                self._start_recording()
            else:
                if self.is_processing:
                    print("⏳ Still processing previous recording...")
                elif self.is_model_loading:
                    print("⏳ Still loading model...")
                else:
                    print(f"⏳ Cannot record while {current_state}...")

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

    def _start_recording(self):
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

            duration = self.audio_recorder.get_audio_duration(audio_data)
            print(f"   ✓ Recorded {duration:.1f} seconds, transcribing...")

            self.system_tray.update_state("processing")

            transcribed_text = self.whisper_engine.transcribe_audio(audio_data)

            if not transcribed_text:
                return

            if command_mode:
                self._handle_command_transcription(transcribed_text)
                return

            success = self.clipboard_manager.deliver_transcription(
                transcribed_text, use_auto_enter
            )

            if success:
                self.last_transcription = transcribed_text
            
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

    def _handle_command_transcription(self, text: str):
        self.logger.info(f"Command mode transcription: '{text}'")
        print(f"   Heard: \"{text}\"")

        if not self.voice_command_manager.enabled:
            self.logger.warning("Voice commands disabled")
            return

        matched = self.voice_command_manager.match_command(text)
        if matched:
            self.voice_command_manager.execute_command(matched)
        else:
            print("   No matching command found")

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

        if self.audio_recorder.get_recording_status():
            self.audio_recorder.stop_recording()
        
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

    def show_console(self):
        self.console_manager.show_console()

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
        return AudioRecorder.get_available_audio_devices(host_name)

    def get_current_audio_device_id(self):
        return self.audio_recorder.get_device_id()

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

        if device_id == self.audio_recorder.device:
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

            channels = self.audio_recorder.channels
            dtype = self.audio_recorder.dtype
            max_duration = self.audio_recorder.max_duration
            on_max_duration = self.audio_recorder.on_max_duration_reached
            vad_manager = self.audio_recorder.vad_manager
            streaming_manager = self.audio_recorder.streaming_manager
            on_streaming_result = self.audio_recorder.on_streaming_result

            new_recorder = AudioRecorder(
                on_vad_event=self.handle_vad_event,
                channels=channels,
                dtype=dtype,
                max_duration=max_duration,
                on_max_duration_reached=on_max_duration,
                vad_manager=vad_manager,
                streaming_manager=streaming_manager,
                on_streaming_result=on_streaming_result,
                device=device_id if device_id != -1 else None
            )

            self.audio_recorder = new_recorder

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
        if not host_name or not self.audio_recorder:
            return

        try:
            current_device_id = self.audio_recorder.get_device_id()
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

        if success:
            self.config_manager.update_user_setting('audio', 'input_device', fallback_device_id)

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
