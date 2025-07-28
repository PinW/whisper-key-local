"""
Application State Manager

This module coordinates all the other components and manages the overall state 
of our application. It's like the "conductor" that tells each part when to work.

For beginners: Think of this as the "boss" of our app - it decides when to 
start recording, when to transcribe, and when to paste the results.
"""

import logging
import time
import threading
from typing import Optional
from .audio_recorder import AudioRecorder
from .whisper_engine import WhisperEngine
from .clipboard_manager import ClipboardManager
from .system_tray import SystemTray
from .config_manager import ConfigManager

class StateManager:
    """
    A class that manages the overall state and workflow of our application
    
    This class coordinates the recording → transcription → clipboard workflow.
    """
    
    def __init__(self, audio_recorder: AudioRecorder, whisper_engine: WhisperEngine, 
                 clipboard_manager: ClipboardManager, clipboard_config: dict,
                 system_tray: Optional[SystemTray] = None, config_manager: Optional[ConfigManager] = None):
        """
        Initialize the state manager with all our components
        
        Parameters:
        - audio_recorder: The AudioRecorder instance for capturing audio
        - whisper_engine: The WhisperEngine instance for transcription
        - clipboard_manager: The ClipboardManager instance for clipboard operations
        - clipboard_config: Configuration settings for clipboard behavior
        - system_tray: Optional SystemTray instance for status display
        - config_manager: Optional ConfigManager instance for settings management
        
        For beginners: We pass in all the other components so this class can 
        control them and make them work together.
        """
        self.audio_recorder = audio_recorder
        self.whisper_engine = whisper_engine
        self.clipboard_manager = clipboard_manager
        self.clipboard_config = clipboard_config
        self.system_tray = system_tray
        self.config_manager = config_manager
        
        # Application state variables
        self.is_processing = False  # Are we currently doing transcription?
        self.is_model_loading = False  # Are we currently loading/changing Whisper model?
        self.last_transcription = None  # Store the last transcribed text
        self._pending_model_change = None  # Store pending model change request during processing
        self._state_lock = threading.Lock()  # Thread safety for state operations
        self._model_loading_progress = ""  # Track model loading progress message
        self.logger = logging.getLogger(__name__)
        
        self.logger.info("StateManager initialized with all components")
        self.logger.info(f"Auto-paste enabled: {self.clipboard_config.get('auto_paste', False)}")
        self.logger.info(f"Initial state: recording={self.audio_recorder.get_recording_status()}, processing={self.is_processing}, model_loading={self.is_model_loading}")
        
        # Initialize system tray to idle state
        if self.system_tray:
            self.system_tray.update_state("idle")
    
    def toggle_recording(self):
        """
        Toggle between recording and stopping (called when hotkey is pressed)
        
        This is the main workflow controller:
        - If not recording: start recording
        - If recording: stop recording and process the audio
        
        For beginners: "Toggle" means switch between two states - like a light 
        switch that turns on when off, and off when on.
        """
        current_state = self.get_current_state()
        current_recording = self.audio_recorder.get_recording_status()
        self.logger.debug(f"toggle_recording called - state={current_state}, recording={current_recording}")
        
        if current_recording:
            # Currently recording, check if we can stop
            if self.can_stop_recording():
                self._stop_recording_and_process()
            else:
                self.logger.info(f"Cannot stop recording in current state: {current_state}")
                print(f"⏳ Cannot stop recording while {current_state}...")
        else:
            # Not recording, check if we can start
            if self.can_start_recording():
                self._start_recording()
            else:
                self.logger.info(f"Cannot start recording in current state: {current_state}")
                if self.is_processing:
                    print("⏳ Still processing previous recording...")
                elif self.is_model_loading:
                    print("⏳ Still loading model...")
                else:
                    print(f"⏳ Cannot record while {current_state}...")
    
    def _start_recording(self):
        """
        Start the recording process
        
        Private method (starts with _) for internal use only.
        """
        try:
            self.logger.info("Starting recording...")
            print("🎤 Recording started! Speak now...")
            print("Press the hotkey again to stop recording.")
            
            success = self.audio_recorder.start_recording()
            
            if success:
                # Update system tray to show recording state only if recording actually started
                if self.system_tray:
                    self.system_tray.update_state("recording")
            else:
                print("❌ Failed to start recording!")
                self.logger.error("Failed to start audio recording")
                # Reset tray to idle state on failure
                if self.system_tray:
                    self.system_tray.update_state("idle")
            
        except Exception as e:
            self.logger.error(f"Error starting recording: {e}")
            print(f"❌ Error starting recording: {e}")
    
    def _stop_recording_and_process(self):
        """
        Stop recording and process the audio through the entire pipeline
        
        This is where the magic happens:
        1. Stop recording and get audio data
        2. Send audio to Whisper for transcription
        3. Copy transcribed text to clipboard
        
        For beginners: This is like an assembly line - each step processes 
        the output from the previous step.
        """
        try:
            # Atomic state transition to processing
            with self._state_lock:
                self.is_processing = True
                self.logger.info(f"State transition: processing={self.is_processing} (starting transcription workflow)")
            
            self.logger.info("Stopping recording and processing...")
            print("🛑 Recording stopped! Processing audio...")
            
            # Update system tray to show processing state
            if self.system_tray:
                self.system_tray.update_state("processing")
            
            # Step 1: Get the recorded audio
            audio_data = self.audio_recorder.stop_recording()
            
            if audio_data is None:
                print("❌ No audio data recorded!")
                self.is_processing = False
                # Reset tray to idle state on failure
                if self.system_tray:
                    self.system_tray.update_state("idle")
                return
            
            # Step 2: Transcribe the audio using Whisper AI
            print("🧠 Transcribing speech...")
            transcribed_text = self.whisper_engine.transcribe_audio(audio_data)
            
            if not transcribed_text:
                print("❌ No speech detected or transcription failed!")
                self.logger.warning("Transcription returned empty result")
                self.is_processing = False
                # Reset tray to idle state on failure
                if self.system_tray:
                    self.system_tray.update_state("idle")
                return
            
            # Step 3: Handle clipboard/paste based on configuration
            auto_paste_enabled = self.clipboard_config.get('auto_paste', False)
            
            if auto_paste_enabled:
                print("🚀 Auto-pasting text...")
                paste_method = self.clipboard_config.get('paste_method', 'key_simulation')
                preserve_clipboard = self.clipboard_config.get('preserve_clipboard', False)
                
                if preserve_clipboard:
                    success = self.clipboard_manager.preserve_and_paste(transcribed_text, paste_method)
                else:
                    success = self.clipboard_manager.copy_and_paste(transcribed_text, paste_method)
                
                if success:
                    # Store for future reference
                    self.last_transcription = transcribed_text
                    self.logger.info("Complete workflow with auto-paste successful")
                else:
                    # Auto-paste failed, but text is still in clipboard
                    self.last_transcription = transcribed_text
                    self.logger.warning("Auto-paste failed, falling back to manual paste")
                    print("✅ Text copied to clipboard. Use Ctrl+V to paste manually.")
            else:
                print("📋 Copying to clipboard...")
                success = self.clipboard_manager.copy_and_notify(transcribed_text)
                
                if success:
                    # Store for future reference
                    self.last_transcription = transcribed_text
                    self.logger.info("Complete workflow successful")
                    print("✅ Ready to paste! Use Ctrl+V in any application.")
                else:
                    print("❌ Failed to copy to clipboard!")
                    self.logger.error("Failed to copy transcription to clipboard")
            
        except Exception as e:
            self.logger.error(f"Error in recording/processing workflow: {e}")
            print(f"❌ Error processing recording: {e}")
        
        finally:
            # Atomic state transition and pending model change handling
            with self._state_lock:
                # Always reset processing flag so we can handle the next recording
                self.is_processing = False
                self.logger.info(f"State transition: processing={self.is_processing} (transcription workflow complete)")
                
                # Check for pending model change
                pending_model = self._pending_model_change
                if pending_model:
                    self._pending_model_change = None
                    self.logger.info(f"Executing pending model change to: {pending_model}")
            
            # Execute pending model change outside of lock to avoid deadlock
            if 'pending_model' in locals() and pending_model:
                print(f"🔄 Processing complete, now switching to {pending_model} model...")
                self._execute_model_change(pending_model)
            else:
                # Reset tray to idle state when done (only if no model change pending)
                if self.system_tray:
                    self.system_tray.update_state("idle")
    
    def get_application_status(self) -> dict:
        """
        Get current status of all components (for debugging/monitoring)
        
        Returns a dictionary with status information about all parts of our app.
        """
        status = {
            "recording": self.audio_recorder.get_recording_status(),
            "processing": self.is_processing,
            "model_loading": self.is_model_loading,
            "model_loading_progress": self._model_loading_progress,
            "last_transcription": self.last_transcription,
            "whisper_model_info": self.whisper_engine.get_model_info(),
            "clipboard_info": self.clipboard_manager.get_clipboard_info()
        }
        
        # Add system tray info if available
        if self.system_tray:
            status["system_tray"] = self.system_tray.get_status_info()
        
        return status
    
    def manual_transcribe_test(self, duration_seconds: int = 5):
        """
        Manual test function to record and transcribe (for testing/debugging)
        
        This is useful for testing our components without using hotkeys.
        
        Parameters:
        - duration_seconds: How long to record (default 5 seconds)
        """
        try:
            print(f"🎤 Recording for {duration_seconds} seconds...")
            print("Speak now!")
            
            # Start recording
            self.audio_recorder.start_recording()
            
            # Wait for specified duration
            time.sleep(duration_seconds)
            
            # Stop and process
            self._stop_recording_and_process()
            
        except Exception as e:
            self.logger.error(f"Manual test failed: {e}")
            print(f"❌ Test failed: {e}")
    
    def shutdown(self):
        """
        Clean shutdown of all components
        
        This ensures everything is properly closed when the app exits.
        """
        self.logger.info("Shutting down StateManager...")
        
        # Stop recording if active
        if self.audio_recorder.get_recording_status():
            self.audio_recorder.stop_recording()
        
        # Stop system tray if running
        if self.system_tray:
            self.system_tray.stop()
        
        # Note: Other components don't need special shutdown procedures
        # but we could add them here if needed
        
        self.logger.info("StateManager shutdown complete")
    
    def set_model_loading(self, loading: bool, progress_message: str = ""):
        """
        Set the model loading state and update system tray
        
        Parameters:
        - loading: True when starting model load, False when complete
        - progress_message: Optional progress message to display
        """
        with self._state_lock:
            old_state = self.is_model_loading
            self.is_model_loading = loading
            self._model_loading_progress = progress_message if loading else ""
            
            if old_state != loading:
                self.logger.info(f"Model loading state changed: {old_state} -> {loading}")
                if progress_message:
                    self.logger.info(f"Model loading progress: {progress_message}")
                
                # Update system tray state
                if self.system_tray:
                    if loading:
                        # Use processing icon during model loading
                        self.system_tray.update_state("processing")
                    else:
                        # Return to idle when model loading complete
                        self.system_tray.update_state("idle")
            elif loading and progress_message:
                # Update progress message without changing state
                self.logger.debug(f"Model loading progress: {progress_message}")
    
    def get_model_loading_progress(self) -> str:
        """
        Get the current model loading progress message
        
        Returns:
        - Progress message string, empty if not loading
        """
        with self._state_lock:
            return self._model_loading_progress
    
    def cancel_model_loading(self):
        """
        Cancel any ongoing model loading operation
        """
        if self.is_model_loading:
            self.logger.info("Cancelling ongoing model loading...")
            print("🛑 Cancelling model loading...")
            
            # Cancel the loading in WhisperEngine
            self.whisper_engine.cancel_model_loading()
            
            # Reset state
            self.set_model_loading(False)
            print("✅ Model loading cancelled")
    
    def can_start_recording(self) -> bool:
        """
        Check if recording can be started based on current state
        
        Returns:
        - True if recording can start, False otherwise
        """
        with self._state_lock:
            return not (self.is_processing or self.is_model_loading or self.audio_recorder.get_recording_status())
    
    def can_change_model(self) -> bool:
        """
        Check if model can be changed based on current state
        
        Returns:
        - True if model can be changed, False otherwise
        """
        with self._state_lock:
            return not self.is_model_loading
    
    def can_stop_recording(self) -> bool:
        """
        Check if recording can be stopped based on current state
        
        Returns:
        - True if recording can be stopped, False otherwise
        """
        with self._state_lock:
            return self.audio_recorder.get_recording_status() and not self.is_processing and not self.is_model_loading
    
    def get_current_state(self) -> str:
        """
        Get a human-readable description of the current application state
        
        Returns:
        - String describing current state ("idle", "recording", "processing", "model_loading")
        """
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
        """
        Request a model change with proper state management and safety checks
        
        Handles different scenarios based on current state:
        - idle: Change model immediately
        - recording: Cancel recording and change model
        - processing: Queue model change for after completion
        - model_loading: Ignore request (return False)
        
        Parameters:
        - new_model_size: The new model size to switch to
        
        Returns:
        - True if model change was initiated or queued, False if ignored
        """
        current_state = self.get_current_state()
        self.logger.info(f"Model change requested: {self.whisper_engine.model_size} -> {new_model_size}, current_state={current_state}")
        
        if new_model_size == self.whisper_engine.model_size:
            self.logger.info(f"Already using model size: {new_model_size}")
            return True
        
        if current_state == "model_loading":
            self.logger.info("Cancelling current model loading to switch to new model")
            print(f"🔄 Cancelling current loading to switch to {new_model_size} model...")
            
            # Cancel current loading and start new one
            self.cancel_model_loading()
            self._execute_model_change(new_model_size)
            return True
        
        if current_state == "recording":
            self.logger.info("Cancelling active recording to change model")
            print(f"🛑 Cancelling recording to switch to {new_model_size} model...")
            
            # Cancel the recording
            if hasattr(self.audio_recorder, 'cancel_recording'):
                self.audio_recorder.cancel_recording()
            else:
                # Fallback - stop recording without processing
                self.audio_recorder.stop_recording()
            
            # Update system tray to idle since we cancelled recording
            if self.system_tray:
                self.system_tray.update_state("idle")
            
            # Now change the model
            self._execute_model_change(new_model_size)
            return True
        
        if current_state == "processing":
            self.logger.info("Queueing model change until processing completes")
            print(f"⏳ Queueing model change to {new_model_size} until transcription completes...")
            self._pending_model_change = new_model_size
            return True
        
        if current_state == "idle":
            self.logger.info("Changing model immediately")
            self._execute_model_change(new_model_size)
            return True
        
        # Fallback - should not reach here
        self.logger.warning(f"Unexpected state for model change: {current_state}")
        return False
    
    def _execute_model_change(self, new_model_size: str):
        """
        Execute the actual model change with proper state management
        
        Parameters:
        - new_model_size: The new model size to switch to
        """
        def progress_callback(message: str):
            """
            Handle progress updates from async model loading
            """
            if "ready" in message.lower() or "already loaded" in message.lower():
                # Model loading complete
                print(f"✅ Successfully switched to {new_model_size} model")
                self.set_model_loading(False)
            elif "failed" in message.lower():
                # Model loading failed
                print(f"❌ Failed to change model: {message}")
                self.set_model_loading(False)
            else:
                # Progress update
                print(f"🔄 {message}")
                self.set_model_loading(True, message)
        
        try:
            self.set_model_loading(True, "Preparing model change...")
            print(f"🔄 Switching to {new_model_size} model...")
            
            # Use async model loading with progress callbacks
            self.whisper_engine.change_model(new_model_size, progress_callback)
            
        except Exception as e:
            self.logger.error(f"Failed to initiate model change: {e}")
            print(f"❌ Failed to change model: {e}")
            self.set_model_loading(False)