"""
Application State Manager

This module coordinates all the other components and manages the overall state 
of our application. It's like the "conductor" that tells each part when to work.

For beginners: Think of this as the "boss" of our app - it decides when to 
start recording, when to transcribe, and when to paste the results.
"""

import logging
import time
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
        self.last_transcription = None  # Store the last transcribed text
        self.logger = logging.getLogger(__name__)
        
        self.logger.info("StateManager initialized with all components")
        self.logger.info(f"Auto-paste enabled: {self.clipboard_config.get('auto_paste', False)}")
        
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
        if self.is_processing:
            self.logger.info("Currently processing previous recording, ignoring hotkey")
            print("⏳ Still processing previous recording...")
            return
        
        if self.audio_recorder.get_recording_status():
            # Currently recording, so stop and process
            self._stop_recording_and_process()
        else:
            # Not recording, so start
            self._start_recording()
    
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
            self.is_processing = True
            
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
            # Always reset processing flag so we can handle the next recording
            self.is_processing = False
            # Reset tray to idle state when done
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