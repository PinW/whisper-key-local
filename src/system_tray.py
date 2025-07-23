"""
System Tray Manager

This module handles the system tray icon functionality for our speech-to-text app.
It shows the current status (idle, recording, processing) and provides a context menu
for quick access to app controls.

For beginners: A system tray icon is that small icon you see in the bottom-right 
corner of Windows (next to the clock). It lets you know the app is running and 
gives you quick access to controls without opening a main window.
"""

import logging
import threading
import time
import os
from typing import Optional, Callable, TYPE_CHECKING
from pathlib import Path

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
    
    def __init__(self, state_manager: Optional['StateManager'] = None, config: dict = None, 
                 config_manager: Optional['ConfigManager'] = None):
        """
        Initialize the system tray manager
        
        Parameters:
        - state_manager: Reference to the main StateManager for status updates
        - config: Configuration dictionary for tray settings
        - config_manager: Reference to ConfigManager for reading/writing settings
        
        For beginners: We pass in the state_manager so this tray can know what 
        the app is currently doing and show the right icon. We also pass the
        config_manager so we can read and change user settings from the menu.
        """
        self.state_manager = state_manager
        self.config = config or {}
        self.config_manager = config_manager
        self.logger = logging.getLogger(__name__)
        
        # Log initialization parameters for debugging
        self.logger.debug(f"SystemTray.__init__ called with:")
        self.logger.debug(f"  state_manager: {type(state_manager).__name__ if state_manager else 'None'}")
        self.logger.debug(f"  config keys: {list(self.config.keys()) if self.config else 'None'}")
        self.logger.debug(f"  config_manager: {type(config_manager).__name__ if config_manager else 'None'}")
        
        # Tray state
        self.icon = None
        self.is_running = False
        self.current_state = "idle"
        self.thread = None
        
        # Check if system tray is available
        if not TRAY_AVAILABLE:
            self.logger.warning("System tray not available - pystray or Pillow not installed")
            self.logger.debug(f"TRAY_AVAILABLE = {TRAY_AVAILABLE}, pystray = {pystray}, Image = {Image}")
            return
        
        self.logger.debug("System tray dependencies are available")
        
        # Load tray icons
        try:
            self.logger.debug("Loading tray icons...")
            self._load_icons()
            self.logger.debug(f"Loaded {len(self.icons)} icons: {list(self.icons.keys())}")
        except Exception as e:
            self.logger.error(f"Failed to load tray icons: {e}")
            raise
        
        self.logger.info("SystemTray initialized successfully")
    
    def _load_icons(self):
        """
        Load the icon files for different states
        
        This method loads the PNG files we created for showing different app states.
        """
        self.icons = {}
        
        # Define the path to our assets directory
        project_root = Path(__file__).parent.parent
        assets_dir = project_root / "assets"
        
        # Icon files for different states
        icon_files = {
            "idle": "tray_idle.png",
            "recording": "tray_recording.png", 
            "processing": "tray_processing.png"
        }
        
        # Load each icon file
        for state, filename in icon_files.items():
            icon_path = assets_dir / filename
            
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
            
            # Get current hotkey from config for display
            hotkey_text = "Unknown"
            try:
                if self.state_manager:
                    self.logger.debug("Getting hotkey from state_manager config")
                    hotkey_text = self.config.get('hotkey', {}).get('combination', 'ctrl+`')
                else:
                    self.logger.debug("No state_manager available, using default hotkey")
                    hotkey_text = self.config.get('hotkey', {}).get('combination', 'ctrl+`')
                
                self.logger.debug(f"Hotkey text: {hotkey_text}")
            except Exception as e:
                self.logger.error(f"Error getting hotkey text: {e}")
                hotkey_text = "ctrl+`"

            # Determine current state for menu logic
            is_processing = False
            is_recording = False
            try:
                if self.state_manager:
                    self.logger.debug("Getting application status from state_manager")
                    status = self.state_manager.get_application_status()
                    is_processing = status.get('processing', False)
                    is_recording = status.get('recording', False)
                    self.logger.debug(f"App status - processing: {is_processing}, recording: {is_recording}")
                else:
                    self.logger.debug("No state_manager available, using default states")
            except Exception as e:
                self.logger.error(f"Error getting application status: {e}")

            # Dynamic action label and enabled state
            if is_processing:
                action_label = "Processing..."
                action_enabled = False
            elif is_recording:
                action_label = "Stop Recording"
                action_enabled = True
            else:
                action_label = "Start Recording"
                action_enabled = True
            
            self.logger.debug(f"Action label: '{action_label}', enabled: {action_enabled}")

            # Get auto-paste setting for checkmark display
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

            # Create menu items
            try:
                self.logger.debug("Creating menu items...")
                menu_items = [
                    # Title & Hotkey display
                    pystray.MenuItem(f"Whisper Key: {hotkey_text.upper()}", None, enabled=False),
                    pystray.Menu.SEPARATOR,  # Separator
                    # Dynamic Start/Stop Recording action as primary
                    pystray.MenuItem(action_label, self._tray_toggle_recording, enabled=action_enabled, default=True),
                    pystray.Menu.SEPARATOR,  # Separator
                    # Settings
                    pystray.MenuItem("Auto-paste transcriptions", self._toggle_auto_paste, checked=lambda item: auto_paste_enabled),
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

    def _toggle_auto_paste(self, icon=None, item=None):
        """
        Called when the Auto-paste transcriptions menu item is clicked.
        
        This method toggles the auto-paste setting and saves it to user settings.
        """
        if not self.config_manager:
            self.logger.warning("Cannot toggle auto-paste: config_manager not available")
            return
        
        try:
            # Get current setting
            current_value = self.config_manager.get_setting('clipboard', 'auto_paste', False)
            new_value = not current_value
            
            # Update the setting (ConfigManager will handle user-friendly logging)
            self.config_manager.update_user_setting('clipboard', 'auto_paste', new_value)
            
            # Update the state manager's clipboard config so changes take effect immediately
            if self.state_manager:
                self.state_manager.clipboard_config['auto_paste'] = new_value
            
            # Refresh the menu to show the new checkmark state
            if self.icon:
                self.icon.menu = self._create_menu()
                
        except Exception as e:
            self.logger.error(f"Error toggling auto-paste setting: {e}")

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
        
        if not TRAY_AVAILABLE:
            self.logger.warning("Cannot start system tray - dependencies not available")
            self.logger.debug(f"TRAY_AVAILABLE = {TRAY_AVAILABLE}")
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
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to start system tray: {e}")
            import traceback
            self.logger.error(f"Traceback: {traceback.format_exc()}")
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
                
            # Wait for thread to finish (with timeout)
            if self.thread and self.thread.is_alive():
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
        return TRAY_AVAILABLE
    
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