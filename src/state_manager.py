import logging
import time
import threading
from typing import Optional

from .audio_recorder import AudioRecorder
from .whisper_engine import WhisperEngine
from .clipboard_manager import ClipboardManager
from .system_tray import SystemTray
from .config_manager import ConfigManager
from .audio_feedback import AudioFeedback
from .utils import OptionalComponent

class StateManager:
    def __init__(self, 
                 audio_recorder: AudioRecorder,
                 whisper_engine: WhisperEngine,
                 clipboard_manager: ClipboardManager,
                 config_manager: ConfigManager,
                 system_tray: Optional[SystemTray] = None,
                 audio_feedback: Optional[AudioFeedback] = None):

        self.audio_recorder = audio_recorder
        self.whisper_engine = whisper_engine
        self.clipboard_manager = clipboard_manager
        self.system_tray = OptionalComponent(system_tray)
        self.config_manager = config_manager
        self.audio_feedback = OptionalComponent(audio_feedback)
        
        self.is_processing = False
        self.is_model_loading = False
        self.last_transcription = None
        self._pending_model_change = None  # Store pending model change request
        self._state_lock = threading.Lock()  # Thread safety for state operations

        self.logger = logging.getLogger(__name__)
    
    def handle_max_recording_duration_reached(self, audio_data):
        """Called when audio recorder reaches max duration with audio data"""
        self.logger.info("Max recording duration reached - starting transcription")
        self._transcription_pipeline(audio_data, use_auto_enter=False)
    
    def stop_recording(self, use_auto_enter: bool = False) -> bool:
        currently_recording = self.audio_recorder.get_recording_status()
        
        if currently_recording:
            audio_data = self.audio_recorder.stop_recording()
            self._transcription_pipeline(audio_data, use_auto_enter)
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

    def _start_recording(self):
        success = self.audio_recorder.start_recording()
        
        if success:
            self.config_manager.print_stop_instructions_based_on_config()
            self.audio_feedback.play_start_sound()
            self.system_tray.update_state("recording")
    
    def _transcription_pipeline(self, audio_data, use_auto_enter: bool = False):
        try:
            # Prevent multiple threads from starting simultaneous transcription
            with self._state_lock:
                self.is_processing = True

            self.audio_feedback.play_stop_sound()
            print("🎤 Recording stopped! Transcribing...")

            if audio_data is None:
                return
            
            transcribed_text = self.whisper_engine.transcribe_audio(audio_data)
            
            if not transcribed_text:
                return
            
            self.system_tray.update_state("processing")

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
            
            # Execute pending model change outside of lock to avoid deadlock
            if 'pending_model' in locals() and pending_model:
                self.logger.info(f"Executing pending model change to: {pending_model}")
                print(f"🔄 Processing complete, now switching to {pending_model} model...")
                self._execute_model_change(pending_model)
                self._pending_model_change = None
            else:
                self.system_tray.update_state("idle")
    
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
        print("Whisper Key is shutting down... good bye!")

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
    
    def request_model_change(self, new_model_size: str) -> bool:
        current_state = self.get_current_state()
        
        if new_model_size == self.whisper_engine.model_size:
            return True
        
        if current_state == "model_loading":
            print("⏳ Model already loading, please wait...")
            return False
        
        if current_state == "recording":
            print(f"🛑 Cancelling recording to switch to {new_model_size} model...")
            self.audio_recorder.cancel_recording()
            self.audio_feedback.play_stop_sound()
            self.system_tray.update_state("idle")          
            self._execute_model_change(new_model_size)
            return True
        
        if current_state == "processing":
            print(f"⏳ Queueing model change to {new_model_size} until transcription completes...")
            self._pending_model_change = new_model_size
            return True
        
        if current_state == "idle":
            self._execute_model_change(new_model_size)
            return True
        
        self.logger.warning(f"Unexpected state for model change: {current_state}")
        return False
    
    def update_transcription_mode(self, value):            
        self.config_manager.update_user_setting('clipboard', 'auto_paste', value)
        self.clipboard_manager.update_auto_paste(value)

    def _execute_model_change(self, new_model_size: str):
        def progress_callback(message: str):
            if "ready" in message.lower() or "already loaded" in message.lower():
                print(f"✅ Successfully switched to {new_model_size} model")
                self.set_model_loading(False)
            elif "failed" in message.lower():
                print(f"❌ Failed to change model: {message}")
                self.set_model_loading(False)
            else:
                print(f"🔄 {message}")
                self.set_model_loading(True)
        
        try:
            self.set_model_loading(True)
            print(f"🔄 Switching to {new_model_size} model...")
            
            self.whisper_engine.change_model(new_model_size, progress_callback)
            
        except Exception as e:
            self.logger.error(f"Failed to initiate model change: {e}")
            print(f"❌ Failed to change model: {e}")
            self.set_model_loading(False)