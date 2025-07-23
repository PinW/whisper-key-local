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

class SystemTray:
    """
    A class that manages the system tray icon and its functionality
    
    This class handles:
    - Showing different icons based on app state (idle/recording/processing)
    - Providing a context menu with app controls
    - Running in a separate thread to avoid blocking the main app
    """
    
    def __init__(self, state_manager: Optional['StateManager'] = None, config: dict = None):
        """
        Initialize the system tray manager
        
        Parameters:
        - state_manager: Reference to the main StateManager for status updates
        - config: Configuration dictionary for tray settings
        
        For beginners: We pass in the state_manager so this tray can know what 
        the app is currently doing and show the right icon.
        """
        self.state_manager = state_manager
        self.config = config or {}
        self.logger = logging.getLogger(__name__)
        
        # Tray state
        self.icon = None
        self.is_running = False
        self.current_state = "idle"
        self.thread = None
        
        # Check if system tray is available
        if not TRAY_AVAILABLE:
            self.logger.warning("System tray not available - pystray or Pillow not installed")
            return
        
        # Load tray icons
        self._load_icons()
        
        self.logger.info("SystemTray initialized")
    
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
        # Get current hotkey from config for display
        hotkey_text = "Unknown"
        if self.state_manager:
            try:
                # Try to get hotkey info from state manager or config
                hotkey_text = self.config.get('hotkey', {}).get('combination', 'ctrl+`')
            except:
                pass

        # Determine current state for menu logic
        is_processing = False
        is_recording = False
        if self.state_manager:
            try:
                status = self.state_manager.get_application_status()
                is_processing = status.get('processing', False)
                is_recording = status.get('recording', False)
            except Exception as e:
                self.logger.error(f"Error getting state for tray menu: {e}")

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

        menu_items = [
            # Title & Hotkey display
            pystray.MenuItem(f"Whisper Key: {hotkey_text.upper()}", None, enabled=False),
            pystray.Menu.SEPARATOR,  # Separator
            # Dynamic Start/Stop Recording action
            pystray.MenuItem(action_label, self._tray_toggle_recording, enabled=action_enabled),
            pystray.Menu.SEPARATOR,  # Separator
            # Action items
            pystray.MenuItem("Exit", self._quit_application)
        ]
        return pystray.Menu(*menu_items)

    def _tray_toggle_recording(self, icon=None, item=None):
        """
        Called when the Start/Stop Recording menu item is clicked.
        """
        if self.state_manager:
            try:
                self.state_manager.toggle_recording()
            except Exception as e:
                self.logger.error(f"Error toggling recording from tray: {e}")

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
        if not TRAY_AVAILABLE:
            self.logger.warning("Cannot start system tray - dependencies not available")
            return False
        
        if self.is_running:
            self.logger.warning("System tray already running")
            return True
        
        try:
            # Create the tray icon
            self.icon = pystray.Icon(
                name="whisper-key",
                icon=self.icons.get("idle"),
                title="Whisper Key",
                menu=self._create_menu()
            )
            
            # Start the tray icon in a separate thread
            self.thread = threading.Thread(target=self._run_tray, daemon=True)
            self.thread.start()
            
            self.is_running = True
            self.logger.info("System tray started successfully")
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to start system tray: {e}")
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