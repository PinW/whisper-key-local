import logging
import time
import threading
from typing import Optional

from .audio_recorder import AudioRecorder
from .audio_devices import AudioDeviceManager
from .whisper_engine import WhisperEngine
from .clipboard_manager import ClipboardManager
from .system_tray import SystemTray
from .config_manager import ConfigManager
from .text_postprocessor import TextPostProcessor
from .audio_feedback import AudioFeedback
from .utils import OptionalComponent
from .voice_activity_detection import VadEvent, VadManager
from .voice_commands import VoiceCommandManager
from .terminal_title import TerminalTitle

class StateManager:
    def __init__(self,
                 audio_recorder: AudioRecorder,
                 whisper_engine: WhisperEngine,
                 clipboard_manager: ClipboardManager,
                 config_manager: ConfigManager,
                 vad_manager: VadManager,
                 text_postprocessor: TextPostProcessor,
                 audio_devices: AudioDeviceManager,
                 system_tray: Optional[SystemTray] = None,
                 audio_feedback: Optional[AudioFeedback] = None,
                 voice_command_manager: Optional[VoiceCommandManager] = None,
                 terminal_title: Optional[TerminalTitle] = None):

        self.audio_recorder = audio_recorder
        self.audio_devices = audio_devices
        self.whisper_engine = whisper_engine
        self.clipboard_manager = clipboard_manager
        self.system_tray = OptionalComponent(system_tray)
        self.config_manager = config_manager
        self.audio_feedback = OptionalComponent(audio_feedback)
        self.vad_manager = vad_manager
        self.text_postprocessor = text_postprocessor
        self.voice_command_manager = voice_command_manager
        self.terminal_title = OptionalComponent(terminal_title)

        self.is_processing = False
        self.is_model_loading = False
        self.last_transcription = None
        self._pending_model_change = None
        self._audio_lock = threading.RLock()
        self._audio_transition = False
        self._recording_failed = threading.Event()
        self._shutting_down = False
        self._command_mode = False
        self._state_lock = threading.Lock()
        self._streaming_display_active = False

        self.logger = logging.getLogger(__name__)

    def attach_components(self,
                          audio_recorder: AudioRecorder,
                          system_tray: Optional[SystemTray]):
        self.audio_recorder = audio_recorder
        self.system_tray = OptionalComponent(system_tray)

    def handle_recording_error(self):
        self._recording_failed.set()
        self.audio_devices.request_refresh()

    def _audio_busy(self):
        recorder = self.audio_recorder
        with self._state_lock:
            is_processing = self.is_processing
        return (
            self._audio_transition or is_processing
            or recorder.is_recording
            or (recorder.recording_thread is not None and recorder.recording_thread.is_alive())
        )

    def refresh_audio_devices(self):
        refresh_menu = False
        recording_failed = False
        with self._audio_lock:
            if self._shutting_down:
                return
            self.audio_devices.observe_changes()
            if self._audio_busy():
                self.audio_devices.announce_deferred_change()
                return
            if self._recording_failed.is_set():
                self._recording_failed.clear()
                with self._state_lock:
                    self._command_mode = False
                recording_failed = True
            refresh_menu = self._apply_audio_selection()
        if recording_failed:
            self._update_ui_state('idle')
        elif refresh_menu:
            self.system_tray.refresh_menu()

    def _start_audio_recording(self, command_mode=False):
        with self._audio_lock:
            if self._shutting_down or self._audio_busy():
                return False
            self._apply_audio_selection(allow_refresh=False)
            if not self.audio_devices.ready_to_record():
                return False
            with self._state_lock:
                if self.is_processing or self.is_model_loading:
                    return False
                self._command_mode = command_mode
                started = self.audio_recorder.start_recording()
                if not started:
                    self._command_mode = False
                return started

    def _update_ui_state(self, state: str):
        self.system_tray.update_state(state)
        self.terminal_title.update_state(state)

    def handle_max_recording_duration_reached(self, audio_data):
        self.logger.info("Max recording duration reached - starting transcription")
        self._transcription_pipeline(audio_data, use_auto_enter=False)

    def handle_vad_event(self, event: VadEvent):
        if event == VadEvent.SILENCE_TIMEOUT:
            self.logger.info("VAD silence timeout detected - stopping recording")
            timeout_seconds = int(self.vad_manager.vad_silence_timeout_seconds)
            self.stop_recording(
                use_auto_enter=False,
                stop_message=f"⏰ Stopping recording after {timeout_seconds} seconds of silence...",
            )

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
    
    def stop_recording(self, use_auto_enter: bool = False, stop_message: Optional[str] = None) -> bool:
        with self._audio_lock:
            if not self.audio_recorder.is_recording or self._audio_transition:
                return False
            self._audio_transition = True
        try:
            self._clear_streaming_display()
            if stop_message:
                print(stop_message)
            audio_data = self.audio_recorder.stop_recording()
            self._transcription_pipeline(audio_data, use_auto_enter)
            return True
        finally:
            with self._audio_lock:
                self._audio_transition = False
    
    def cancel_active_recording(self):
        with self._audio_lock:
            if self._audio_transition:
                return
            self._audio_transition = True
        try:
            self._clear_streaming_display()
            self.audio_recorder.cancel_recording()
            with self._state_lock:
                self._command_mode = False
            self.audio_feedback.play_cancel_sound()
            self._update_ui_state("idle")
        finally:
            with self._audio_lock:
                self._audio_transition = False
    
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
            if current_state == 'processing':
                print("⏳ Still processing previous recording...")
            elif current_state == 'model_loading':
                print("⏳ Still loading model...")
            else:
                print(f"⏳ Cannot record while {current_state}...")
            return

        self._begin_recording()

    def start_command_recording(self):
        if not self.can_start_recording():
            return

        self.logger.info("Starting command mode recording")
        success = self._start_audio_recording(command_mode=True)
        if success:
            print("\n🎤 Command mode activated! Speak a command...")
            self.config_manager.print_command_stop_instructions()
            self.audio_feedback.play_start_sound()
            self._update_ui_state("recording")

    def _begin_recording(self):
        success = self._start_audio_recording()

        if success:
            print("\n🎤 Recording started! Speak now...")
            self.config_manager.print_stop_instructions_based_on_config()
            self.audio_feedback.play_start_sound()
            self._update_ui_state("recording")
    
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

            self._update_ui_state("processing")

            transcribed_text = self.whisper_engine.transcribe_audio(audio_data)

            if not transcribed_text:
                return

            transcribed_text = self.text_postprocessor.process(transcribed_text)
            print(f"   ✓ Transcribed: '{transcribed_text}'")
            self._log_transcription(transcribed_text)

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

            if pending_model:
                self.logger.info(f"Executing pending model change to: {pending_model}")
                print(f"🔄 Processing complete, now switching to [{pending_model}] model...")
                self._execute_model_change(pending_model)
                self._pending_model_change = None

            if not pending_model:
                self._update_ui_state("idle")

    def _log_transcription(self, text: str):
        log_config = self.config_manager.get_logging_config()
        if log_config.get('log_transcriptions', False):
            self.logger.info(f"Transcribed text: '{text}'")
        else:
            self.logger.info(f"Transcribed {len(text)} chars")

    def _handle_command_transcription(self, text: str, use_auto_enter: bool = False):
        if not self.voice_command_manager.enabled:
            self.logger.warning("Voice commands disabled")
            return

        matched = self.voice_command_manager.match_command(text)
        if matched:
            self.voice_command_manager.execute_command(matched, use_auto_enter)
        else:
            print("   ✗ No matching command found")

    def get_application_state(self) -> dict:
        with self._state_lock:
            return {
                "recording": self.audio_recorder.get_recording_status(),
                "processing": self.is_processing,
                "model_loading": self.is_model_loading,
            }
    
    def manual_transcribe_test(self, duration_seconds: int = 5):
        try:
            print(f"🎤 Recording for {duration_seconds} seconds...")
            print("Speak now!")
            
            if not self._start_audio_recording():
                return
            
            time.sleep(duration_seconds)
            
            self.stop_recording()
            
        except Exception as e:
            self.logger.error(f"Manual test failed: {e}")
            print(f"❌ Test failed: {e}")
    
    def shutdown(self):        
        print("Whisper Key is shutting down... goodbye!")

        with self._audio_lock:
            self._shutting_down = True
        self.audio_devices.stop()

        if self.audio_recorder and self.audio_recorder.get_recording_status():
            self.audio_recorder.stop_recording()

        self.system_tray.stop()
        self.terminal_title.stop()
    
    def set_model_loading(self, loading: bool):
        with self._state_lock:
            old_state = self.is_model_loading
            self.is_model_loading = loading
            
        if old_state != loading:
            if loading:
                self._update_ui_state("processing")
            else:
                self._update_ui_state("idle")
    
    def is_transcription_recording(self) -> bool:
        with self._state_lock:
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
        with self._audio_lock:
            return self.audio_devices.input_devices(host_filter)

    def get_current_audio_device_id(self):
        with self._audio_lock:
            return self.audio_recorder.get_device_id()

    def get_available_audio_hosts(self):
        with self._audio_lock:
            return self.audio_devices.available_hosts()

    def get_current_audio_host(self) -> Optional[str]:
        return self.audio_devices.selected_host

    def get_audio_source_selection(self):
        with self._audio_lock:
            return self.audio_devices.source_mode, self.audio_devices.selected_host, self.audio_devices.selected_name

    def get_default_audio_sources(self):
        return self.audio_devices.default_sources()

    def request_default_audio_source(self, source_mode):
        return self._request_audio_change(self.audio_devices.select_default, source_mode)

    def _apply_audio_selection(self, allow_refresh=True):
        if not self.audio_devices.update(allow_refresh=allow_refresh):
            return False
        try:
            self.audio_recorder.resolve_device(self.audio_devices.device_id)
            self.audio_devices.selection_applied()
        except Exception as error:
            self.audio_recorder.resolve_device(-1)
            self.audio_devices.change_failed(error)
        return True

    def set_audio_host(self, host_name: str) -> bool:
        return self._request_audio_change(self.audio_devices.select_host, host_name)

    def request_audio_device_change(self, device_name: str, host_name: str):
        return self._request_audio_change(self.audio_devices.select_device, device_name, host_name)

    def _request_audio_change(self, select_source, *arguments):
        with self._audio_lock:
            if self._shutting_down or not select_source(*arguments):
                return False
            if not self.audio_devices.selection_pending:
                return True
            cancel_recording = self.audio_recorder.is_recording and not self._audio_transition
            if self._audio_busy() and not cancel_recording:
                print('🎤 Audio source will switch when the current recording and transcription finish.')
            elif not self._audio_busy():
                self._apply_audio_selection(allow_refresh=False)
        if cancel_recording:
            print('🎤 Cancelling recording to switch audio device...')
            self.cancel_active_recording()
            with self._audio_lock:
                if not self._audio_busy():
                    self._apply_audio_selection(allow_refresh=False)
        self.system_tray.refresh_menu()
        return True
