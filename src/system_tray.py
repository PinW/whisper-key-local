"""
System Tray Manager

This module handles the system tray icon functionality for our speech-to-text app.
It shows the current status (idle, recording, processing) and provides a context menu
for quick access to app controls.

corner of Windows (next to the clock). It lets you know the app is running and 
gives you quick access to controls without opening a main window.
"""

import logging
import threading
import time
import os
from typing import Optional, Callable, TYPE_CHECKING
from pathlib import Path

from .utils import beautify_hotkey, resolve_asset_path

# System tray imports
try:
    import pystray
    from PIL import Image
    TRAY_AVAILABLE = True
except ImportError:
    TRAY_AVAILABLE = False
    pystray = None
    Image = None

# Type checking imports (won't cause circular imports)
if TYPE_CHECKING:
    from .state_manager import StateManager
    from .config_manager import ConfigManager

class SystemTray:
    """
    A class that manages the system tray icon and its functionality
    
    This class handles:
    - Showing different icons based on app state (idle/recording/processing)
    - Providing a context menu with app controls
    - Running in a separate thread to avoid blocking the main app
    """
    
    def __init__(self, state_manager: Optional['StateManager'] = None, 
                 tray_config: dict = None,
                 config_manager: Optional['ConfigManager'] = None):
        """
        Initialize the system tray manager
        
        Parameters:
        - state_manager: Reference to the main StateManager for status updates
        - tray_config: System tray configuration dictionary
        - config_manager: Reference to ConfigManager for reading/writing settings
        
        the app is currently doing and show the right icon. We also pass the
        config_manager so we can read and change user settings from the menu.
        """
        self.state_manager = state_manager
        self.tray_config = tray_config or {}
        self.config_manager = config_manager
        self.logger = logging.getLogger(__name__)
        
        # Log initialization parameters for debugging
        self.logger.debug(f"SystemTray.__init__ called with:")
        self.logger.debug(f"  state_manager: {type(state_manager).__name__ if state_manager else 'None'}")
        self.logger.debug(f"  tray_config keys: {list(self.tray_config.keys()) if self.tray_config else 'None'}")
        self.logger.debug(f"  config_manager: {type(config_manager).__name__ if config_manager else 'None'}")
        
        # Tray state
        self.icon = None
        self.is_running = False
        self.current_state = "idle"
        self.thread = None
        self.available = True
        
        # Check if system tray is available and print status
        if not self.tray_config.get('enabled', True):
            self.logger.info("System tray disabled in configuration")
            print("   ✗ System tray disabled in configuration")
            self.available = False
        elif not TRAY_AVAILABLE:
            self.logger.warning("System tray not available - pystray or Pillow not installed")
            print("   ⚠️ System tray not available")
            self.available = False
        else:
            # Load tray icons
            try:
                self._load_icons()
                self.logger.info("SystemTray initialized successfully")
            except Exception as e:
                self.logger.error(f"Failed to load tray icons: {e}")
                print(f"   ⚠️ System tray initialization failed: {e}")
                self.available = False
    
    def _load_icons(self):
        """
        Load the icon files for different states
        
        This method loads the PNG files we created for showing different app states.
        """
        self.icons = {}
        
        icon_files = {
            "idle": "assets/tray_idle.png",
            "recording": "assets/tray_recording.png", 
            "processing": "assets/tray_processing.png"
        }
        
        for state, asset_path in icon_files.items():
            icon_path = Path(resolve_asset_path(asset_path))
            
            try:
                if icon_path.exists():
                    # Load the actual PNG file
                    self.icons[state] = Image.open(str(icon_path))
                    self.logger.debug(f"Loaded icon for {state}: {icon_path}")
                else:
                    # Create a fallback colored square if file doesn't exist
                    self.icons[state] = self._create_fallback_icon(state)
                    self.logger.warning(f"Icon file not found, using fallback: {icon_path}")
                    
            except Exception as e:
                # Create fallback icon if loading fails
                self.logger.error(f"Failed to load icon {icon_path}: {e}")
                self.icons[state] = self._create_fallback_icon(state)
    
    def _create_fallback_icon(self, state: str) -> Image.Image:
        """
        Create a simple fallback icon if the PNG files aren't available
        
        This creates basic colored squares as emergency icons.
        """
        # Color scheme matching our icon generator
        colors = {
            'idle': (100, 149, 237),     # Blue
            'recording': (220, 20, 60),   # Red  
            'processing': (255, 165, 0)   # Orange
        }
        
        color = colors.get(state, (128, 128, 128))  # Default to gray
        
        # Create a 16x16 colored square
        icon = Image.new('RGBA', (16, 16), color + (255,))
        return icon
    
    def _create_menu(self):
        """
        Create the context menu that appears when you right-click the tray icon
        """
        try:
            self.logger.debug("Creating tray menu...")
            

            # Determine current state for menu logic
            is_processing = False
            is_recording = False
            is_model_loading = False
            model_loading_progress = ""
            try:
                if self.state_manager:
                    self.logger.debug("Getting application status from state_manager")
                    status = self.state_manager.get_application_status()
                    is_processing = status.get('processing', False)
                    is_recording = status.get('recording', False)
                    is_model_loading = status.get('model_loading', False)
                    model_loading_progress = status.get('model_loading_progress', "")
                    self.logger.debug(f"App status - processing: {is_processing}, recording: {is_recording}, model_loading: {is_model_loading}, progress: {model_loading_progress}")
                else:
                    self.logger.debug("No state_manager available, using default states")
            except Exception as e:
                self.logger.error(f"Error getting application status: {e}")

            # Dynamic action label and enabled state
            if is_recording:
                action_label = "Stop Recording"
                action_enabled = True
            elif is_processing or is_model_loading:
                action_label = "Start Recording"
                action_enabled = False
            else:
                action_label = "Start Recording"
                action_enabled = True
            
            self.logger.debug(f"Action label: '{action_label}', enabled: {action_enabled}")

            # Get auto-paste setting for radio button display
            auto_paste_enabled = False
            try:
                if self.config_manager:
                    self.logger.debug("Getting auto-paste setting from config_manager")
                    auto_paste_enabled = self.config_manager.get_setting('clipboard', 'auto_paste', False)
                    self.logger.debug(f"Auto-paste enabled: {auto_paste_enabled}")
                else:
                    self.logger.debug("No config_manager available, auto-paste disabled")
            except Exception as e:
                self.logger.error(f"Error reading auto-paste setting: {e}")


            # Get current model size for radio buttons
            current_model = "tiny"
            try:
                if self.config_manager:
                    self.logger.debug("Getting model size from config_manager")
                    current_model = self.config_manager.get_setting('whisper', 'model_size', 'tiny')
                    self.logger.debug(f"Current model: {current_model}")
                else:
                    self.logger.debug("No config_manager available, using default model")
            except Exception as e:
                self.logger.error(f"Error reading model size setting: {e}")

            # Create model selection submenu
            # Create helper function to dynamically check current model
            def is_current_model(model_name):
                if not self.config_manager:
                    return model_name == "tiny"  # Default fallback
                try:
                    current = self.config_manager.get_setting('whisper', 'model_size', 'tiny')
                    return current == model_name
                except:
                    return model_name == "tiny"
            
            # Helper function to check if model selection should be enabled
            def model_selection_enabled():
                return not is_model_loading
            
            model_menu_items = [
                pystray.MenuItem("Tiny (75MB, fastest)", lambda icon, item: self._select_model("tiny"), radio=True, checked=lambda item: is_current_model("tiny"), enabled=model_selection_enabled()),
                pystray.MenuItem("Base (142MB, balanced)", lambda icon, item: self._select_model("base"), radio=True, checked=lambda item: is_current_model("base"), enabled=model_selection_enabled()),
                pystray.MenuItem("Small (466MB, accurate)", lambda icon, item: self._select_model("small"), radio=True, checked=lambda item: is_current_model("small"), enabled=model_selection_enabled()),
                pystray.MenuItem("Medium (1.5GB, very accurate)", lambda icon, item: self._select_model("medium"), radio=True, checked=lambda item: is_current_model("medium"), enabled=model_selection_enabled()),
                pystray.MenuItem("Large (2.9GB, best accuracy)", lambda icon, item: self._select_model("large"), radio=True, checked=lambda item: is_current_model("large"), enabled=model_selection_enabled()),
                pystray.Menu.SEPARATOR,
                pystray.MenuItem("Tiny.En (English only)", lambda icon, item: self._select_model("tiny.en"), radio=True, checked=lambda item: is_current_model("tiny.en"), enabled=model_selection_enabled()),
                pystray.MenuItem("Base.En (English only)", lambda icon, item: self._select_model("base.en"), radio=True, checked=lambda item: is_current_model("base.en"), enabled=model_selection_enabled()),
                pystray.MenuItem("Small.En (English only)", lambda icon, item: self._select_model("small.en"), radio=True, checked=lambda item: is_current_model("small.en"), enabled=model_selection_enabled()),
                pystray.MenuItem("Medium.En (English only)", lambda icon, item: self._select_model("medium.en"), radio=True, checked=lambda item: is_current_model("medium.en"), enabled=model_selection_enabled())
            ]

            # Create menu items
            try:
                self.logger.debug("Creating menu items...")
                menu_items = [
                    # Transcription Mode
                    pystray.MenuItem("Auto-paste", lambda icon, item: self._set_transcription_mode(True), radio=True, checked=lambda item: auto_paste_enabled),
                    pystray.MenuItem("Copy to clipboard", lambda icon, item: self._set_transcription_mode(False), radio=True, checked=lambda item: not auto_paste_enabled),
                    pystray.Menu.SEPARATOR,  # Separator below transcription mode options
                    pystray.MenuItem(f"Model: {current_model.title()}", pystray.Menu(*model_menu_items)),
                    pystray.Menu.SEPARATOR,  # Separator
                    # Dynamic Start/Stop Recording action as primary
                    pystray.MenuItem(action_label, self._tray_toggle_recording, enabled=action_enabled, default=True),
                    pystray.Menu.SEPARATOR,  # Separator
                    # Action items
                    pystray.MenuItem("Exit", self._quit_application)
                ]
                self.logger.debug(f"Created {len(menu_items)} menu items")
                
                # Create the menu
                menu = pystray.Menu(*menu_items)
                self.logger.debug("pystray.Menu created successfully")
                return menu
                
            except Exception as e:
                self.logger.error(f"Error creating menu items: {e}")
                raise
                
        except Exception as e:
            self.logger.error(f"Error in _create_menu: {e}")
            import traceback
            self.logger.error(f"Traceback: {traceback.format_exc()}")
            raise

    def _tray_toggle_recording(self, icon=None, item=None):
        """
        Called when the Start/Stop Recording menu item is clicked.
        """
        if self.state_manager:
            try:
                self.state_manager.toggle_recording()
            except Exception as e:
                self.logger.error(f"Error toggling recording from tray: {e}")

    def _set_transcription_mode(self, auto_paste: bool):
        """
        Called when a transcription mode radio button is clicked.
        
        This method sets the auto-paste setting based on the selected mode.
        
        Parameters:
        - auto_paste: True for auto-paste mode, False for copy-to-clipboard mode
        """
        if not self.config_manager:
            self.logger.warning("Cannot set transcription mode: config_manager not available")
            return
        
        try:
            # Update the setting (ConfigManager will handle user-friendly logging)
            self.config_manager.update_user_setting('clipboard', 'auto_paste', auto_paste)
            
            # Update the clipboard manager so changes take effect immediately
            if self.state_manager:
                self.state_manager.update_clipboard_setting('auto_paste', auto_paste)
            
            # Refresh the menu to show the new radio button state
            if self.icon:
                self.icon.menu = self._create_menu()
                
        except Exception as e:
            self.logger.error(f"Error setting transcription mode: {e}")

    def _select_model(self, model_size: str):
        """
        Select a new Whisper AI model size from the system tray menu.
        
        This method updates the model_size setting and requests a state-aware model change
        through the StateManager which handles all the safety logic.
        
        Parameters:
        - model_size: The new model size ("tiny", "base", "small", "medium", "large")
        """
        if not self.config_manager:
            self.logger.warning("Cannot select model: config_manager not available")
            return
        
        if not self.state_manager:
            self.logger.warning("Cannot select model: state_manager not available")
            return
        
        try:
            # Get current model to check if it's actually changing
            current_model = self.config_manager.get_setting('whisper', 'model_size', 'tiny')
            
            if current_model == model_size:
                self.logger.debug(f"Model already set to {model_size}, no change needed")
                return
            
            self.logger.info(f"Requesting model change from {current_model} to {model_size}")
            
            # Request state-aware model change through StateManager
            # This handles all the safety logic: recording cancellation, queueing during processing, etc.
            success = self.state_manager.request_model_change(model_size)
            
            if success:
                # Update the setting only if model change was accepted/initiated
                self.config_manager.update_user_setting('whisper', 'model_size', model_size)
                
                # Refresh the menu to show the new radio button selection
                if self.icon:
                    self.icon.menu = self._create_menu()
            else:
                self.logger.info(f"Model change to {model_size} was not accepted in current state")
                
        except Exception as e:
            self.logger.error(f"Error selecting model {model_size}: {e}")

    def _quit_application(self, icon=None, item=None):
        """
        Quit the entire application (called from menu)
        
        This provides a clean way to exit the app from the system tray.
        """
        self.logger.info("Exit requested from system tray")
        print("Exiting application from system tray...")
        
        # Stop the tray icon
        self.stop()
        
        # In a real application, you'd trigger a clean shutdown
        # For now, we'll raise KeyboardInterrupt to simulate Ctrl+C
        import os
        import signal
        os.kill(os.getpid(), signal.SIGINT)
    
    def update_state(self, new_state: str):
        """
        Update the tray icon to reflect a new application state
        
        Parameters:
        - new_state: The new state ("idle", "recording", "processing")
        
        This method is called by the StateManager when the app status changes.
        """
        if not TRAY_AVAILABLE or not self.is_running:
            return
        
        old_state = self.current_state
        self.current_state = new_state
        
        # Update the icon if we have one loaded
        if self.icon and new_state in self.icons:
            try:
                self.icon.icon = self.icons[new_state]
                self.icon.title = f"Whisper Key - {new_state.title()}"
                # Refresh the menu to update the Start/Stop action
                self.icon.menu = self._create_menu()
                self.logger.debug(f"Tray icon updated: {old_state} -> {new_state}")
            except Exception as e:
                self.logger.error(f"Failed to update tray icon: {e}")
    
    def start(self):
        """
        Start the system tray icon in a separate thread
        
        This method starts the tray functionality without blocking the main application.
        """
        self.logger.debug("SystemTray.start() called")
        
        if not self.available:
            self.logger.debug("SystemTray not available - skipping start")
            return False
        
        if self.is_running:
            self.logger.warning("System tray already running")
            return True
        
        try:
            # Validate icons are loaded
            if not hasattr(self, 'icons') or not self.icons:
                self.logger.error("No icons loaded - cannot create tray icon")
                return False
            
            self.logger.debug(f"Available icons: {list(self.icons.keys())}")
            idle_icon = self.icons.get("idle")
            if idle_icon is None:
                self.logger.error("Idle icon not found in loaded icons")
                return False
            
            self.logger.debug(f"Using idle icon: {type(idle_icon)}")
            
            # Create menu first (separate from icon creation for better error isolation)
            try:
                self.logger.debug("Creating tray menu...")
                menu = self._create_menu()
                self.logger.debug("Tray menu created successfully")
            except Exception as menu_error:
                self.logger.error(f"Failed to create tray menu: {menu_error}")
                raise
            
            # Create the tray icon
            try:
                self.logger.debug("Creating pystray.Icon...")
                self.icon = pystray.Icon(
                    name="whisper-key",
                    icon=idle_icon,
                    title="Whisper Key",
                    menu=menu
                )
                self.logger.debug("pystray.Icon created successfully")
            except Exception as icon_error:
                self.logger.error(f"Failed to create pystray.Icon: {icon_error}")
                raise
            
            # Start the tray icon in a separate thread
            try:
                self.logger.debug("Starting tray thread...")
                self.thread = threading.Thread(target=self._run_tray, daemon=True)
                self.thread.start()
                self.logger.debug("Tray thread started successfully")
            except Exception as thread_error:
                self.logger.error(f"Failed to start tray thread: {thread_error}")
                raise
            
            self.is_running = True
            self.logger.info("System tray started successfully")
            print("   ✓ System tray icon is running...")
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to start system tray: {e}")
            print("   ⚠️ System tray failed to start")
            return False
    
    def _run_tray(self):
        """
        Run the system tray icon (called in separate thread)
        
        This is the main loop for the tray icon - it handles clicks, menu actions, etc.
        """
        try:
            self.logger.debug("Starting tray icon thread")
            self.icon.run()  # This blocks until icon.stop() is called
        except Exception as e:
            self.logger.error(f"System tray thread error: {e}")
        finally:
            self.is_running = False
            self.logger.debug("Tray icon thread ended")
    
    def stop(self):
        """
        Stop the system tray icon and clean up
        
        This method safely shuts down the tray icon and its thread.
        """
        if not self.is_running:
            return
        
        try:
            if self.icon:
                self.icon.stop()
                
            # Wait for thread to finish (with timeout) - but don't join current thread
            if self.thread and self.thread.is_alive() and self.thread != threading.current_thread():
                self.thread.join(timeout=2.0)
                
            self.is_running = False
            self.logger.info("System tray stopped")
            
        except Exception as e:
            self.logger.error(f"Error stopping system tray: {e}")
    
    def is_available(self) -> bool:
        """
        Check if system tray functionality is available
        
        Returns True if pystray and Pillow are installed and working.
        """
        return self.available
    
    def get_status_info(self) -> dict:
        """
        Get information about the system tray status (for debugging)
        
        Returns a dictionary with tray status information.
        """
        return {
            "available": TRAY_AVAILABLE,
            "running": self.is_running,
            "current_state": self.current_state,
            "icons_loaded": len(self.icons) if hasattr(self, 'icons') else 0,
            "thread_alive": self.thread.is_alive() if self.thread else False
        }