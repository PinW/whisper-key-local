import logging
import threading
import os
import signal
from typing import Optional, TYPE_CHECKING
from pathlib import Path

from .utils import resolve_asset_path

try:
    import pystray
    from PIL import Image
    TRAY_AVAILABLE = True
except ImportError:
    TRAY_AVAILABLE = False
    pystray = None
    Image = None

if TYPE_CHECKING:
    from .state_manager import StateManager
    from .config_manager import ConfigManager

class SystemTray:   
    def __init__(self,
                 state_manager: 'StateManager',
                 tray_config: dict = None,
                 config_manager: Optional['ConfigManager'] = None):

        self.state_manager = state_manager
        self.tray_config = tray_config or {}
        self.config_manager = config_manager
        self.logger = logging.getLogger(__name__)
               
        self.icon = None  # pystray object, holds menu, state, etc.
        self.is_running = False
        self.current_state = "idle"
        self.thread = None
        self.available = True
        
        if self._check_tray_availability():
            self._load_icons_to_cache()
    
    def _check_tray_availability(self) -> bool:
        if not self.tray_config['enabled']:
            self.logger.warning("   ✗ System tray disabled in configuration")
            self.available = False
            
        elif not TRAY_AVAILABLE:
            self.logger.warning("   ✗ System tray not available - pystray or Pillow not installed")
            self.available = False

        return self.available
    
    def _load_icons_to_cache(self):
        try:
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
                        self.icons[state] = Image.open(str(icon_path))
                    else:
                        self.icons[state] = self._create_fallback_icon(state)
                        self.logger.warning(f"Icon file not found, using fallback: {icon_path}")
                        
                except Exception as e:
                    self.logger.error(f"Failed to load icon {icon_path}: {e}")
                    self.icons[state] = self._create_fallback_icon(state)

        except Exception as e:
            self.logger.error(f"Failed to load system tray: {e}")
            self.available = False
        
    def _create_fallback_icon(self, state: str) -> Image.Image:
        colors = {
            'idle': (128, 128, 128),      # Gray
            'recording': (34, 139, 34),   # Green  
            'processing': (255, 165, 0)   # Orange
        }
        
        color = colors.get(state, (128, 128, 128))  # Default to gray
        icon = Image.new('RGBA', (16, 16), color + (255,))

        return icon
    
    def _create_menu(self):
        try:
            app_state = self.state_manager.get_application_state()
            is_model_loading = app_state.get('model_loading', False)

            auto_paste_enabled = self.config_manager.get_setting('clipboard', 'auto_paste')
            current_model = self.config_manager.get_setting('whisper', 'model_size')

            def is_current_model(model_name):
                return model_name == current_model
            
            def model_selection_enabled():
                return not is_model_loading
            
            model_sub_menu_items = [
                pystray.MenuItem("Tiny (75MB, fastest)", lambda icon, item: self._select_model("tiny"), radio=True, checked=lambda item: is_current_model("tiny"), enabled=model_selection_enabled()),
                pystray.MenuItem("Base (142MB, balanced)", lambda icon, item: self._select_model("base"), radio=True, checked=lambda item: is_current_model("base"), enabled=model_selection_enabled()),
                pystray.MenuItem("Small (466MB, accurate)", lambda icon, item: self._select_model("small"), radio=True, checked=lambda item: is_current_model("small"), enabled=model_selection_enabled()),
                pystray.MenuItem("Medium (1.5GB, very accurate)", lambda icon, item: self._select_model("medium"), radio=True, checked=lambda item: is_current_model("medium"), enabled=model_selection_enabled()),
                pystray.MenuItem("Large (2.9GB, best accuracy)", lambda icon, item: self._select_model("large"), radio=True, checked=lambda item: is_current_model("large"), enabled=model_selection_enabled()),
                pystray.MenuItem("Large-V3-Turbo (1.6GB, turbo)", lambda icon, item: self._select_model("large-v3-turbo"), radio=True, checked=lambda item: is_current_model("large-v3-turbo"), enabled=model_selection_enabled()),
                pystray.Menu.SEPARATOR,
                pystray.MenuItem("Tiny.En (English only)", lambda icon, item: self._select_model("tiny.en"), radio=True, checked=lambda item: is_current_model("tiny.en"), enabled=model_selection_enabled()),
                pystray.MenuItem("Base.En (English only)", lambda icon, item: self._select_model("base.en"), radio=True, checked=lambda item: is_current_model("base.en"), enabled=model_selection_enabled()),
                pystray.MenuItem("Small.En (English only)", lambda icon, item: self._select_model("small.en"), radio=True, checked=lambda item: is_current_model("small.en"), enabled=model_selection_enabled()),
                pystray.MenuItem("Medium.En (English only)", lambda icon, item: self._select_model("medium.en"), radio=True, checked=lambda item: is_current_model("medium.en"), enabled=model_selection_enabled())
            ]

            menu_items = [
                pystray.MenuItem("Auto-paste", lambda icon, item: self._set_transcription_mode(True), radio=True, checked=lambda item: auto_paste_enabled),
                pystray.MenuItem("Copy to clipboard", lambda icon, item: self._set_transcription_mode(False), radio=True, checked=lambda item: not auto_paste_enabled),
                pystray.Menu.SEPARATOR,
                pystray.MenuItem(f"Model: {current_model.title()}", pystray.Menu(*model_sub_menu_items)),
            ]

            is_executable = self.state_manager.console_manager.is_executable_mode
            if is_executable:
                menu_items.extend([
                    pystray.Menu.SEPARATOR,
                    pystray.MenuItem("Show Console", self._show_console, default=True),
                ])

            menu_items.extend([
                pystray.Menu.SEPARATOR,
                pystray.MenuItem("Exit", self._quit_application_from_tray)
            ])
            
            menu = pystray.Menu(*menu_items)

            return menu 
                
        except Exception as e:
            self.logger.error(f"Error in _create_menu: {e}")
            raise

    def _tray_toggle_recording(self, icon=None, item=None):
        self.state_manager.toggle_recording()

    def _show_console(self, icon=None, item=None):
        self.state_manager.show_console()

    def _set_transcription_mode(self, auto_paste: bool):        
        self.state_manager.update_transcription_mode(auto_paste)
        self.icon.menu = self._create_menu()

    def _select_model(self, model_size: str):        
        try:
            success = self.state_manager.request_model_change(model_size)
            
            if success:
                self.config_manager.update_user_setting('whisper', 'model_size', model_size)                
                self.icon.menu = self._create_menu()
            else:
                self.logger.warning(f"Request to change model to {model_size} was not accepted")
                
        except Exception as e:
            self.logger.error(f"Error selecting model {model_size}: {e}")

    def _quit_application_from_tray(self, icon=None, item=None):        
        os.kill(os.getpid(), signal.SIGINT)
    
    def update_state(self, new_state: str):
        if not TRAY_AVAILABLE or not self.is_running:
            return
        
        self.current_state = new_state
        
        try:
            self.icon.icon = self.icons[new_state]
            self.icon.menu = self._create_menu()
        except Exception as e:
            self.logger.error(f"Failed to update tray icon: {e}")
    
    def start(self):        
        if not self.available:
            return False
        
        if self.is_running:
            self.logger.warning("System tray is already running")
            return True
        
        try:
            idle_icon = self.icons.get("idle")    
            menu = self._create_menu()
            
            self.icon = pystray.Icon(
                name="whisper-key",
                icon=idle_icon,
                title="Whisper Key",
                menu=menu
            )
            
            self.thread = threading.Thread(target=self._run_tray, daemon=True)
            self.thread.start()
            
            self.is_running = True
            print("   ✓ System tray icon is running...")

            return True
            
        except Exception as e:
            self.logger.error(f"Failed to start system tray: {e}")
            return False
    
    def _run_tray(self):
        try:
            self.icon.run()  # pystray provided loop method
        except Exception as e:
            self.logger.error(f"System tray thread error: {e}")
        finally:
            self.is_running = False
            self.logger.debug("Tray icon thread ended")
    
    def stop(self):
        if not self.is_running:
            return
        
        try:
            self.icon.stop()
                
            # Wait for thread to finish to avoid deadlock
            if self.thread and self.thread.is_alive() and self.thread != threading.current_thread():
                self.thread.join(timeout=2.0)
                
            self.is_running = False
            
        except Exception as e:
            self.logger.error(f"Error stopping system tray: {e}")