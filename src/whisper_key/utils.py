import os
import sys
import importlib.resources
from contextlib import contextmanager
from pathlib import Path

class OptionalComponent:
    def __init__(self, component):
        self._component = component
    
    def __getattr__(self, name):
        if self._component and hasattr(self._component, name):
            attr = getattr(self._component, name)
            return attr
        else:
            # Return a no-op function for missing methods/attributes
            return lambda *args, **kwargs: None


def beautify_hotkey(hotkey_string: str) -> str:
    if not hotkey_string:
        return ""
    
    return hotkey_string.replace('+', '+').upper()

def is_installed_package():
    # Check if running from an installed package
    return 'site-packages' in __file__

def get_user_app_data_path():
    appdata = os.getenv('APPDATA')
    whisperkey_dir = os.path.join(appdata, 'whisperkey')
    os.makedirs(whisperkey_dir, exist_ok=True)
    return whisperkey_dir

def resolve_asset_path(relative_path: str) -> str:
    
    if not relative_path or os.path.isabs(relative_path):
        return relative_path
    
    if getattr(sys, 'frozen', False): # PyInstaller
        return str(Path(sys._MEIPASS) / relative_path)
    
    if is_installed_package(): # pip / pipx
        files = importlib.resources.files("whisper_key")
        return str(files / relative_path)
    
    return str(Path(__file__).parent / relative_path) # Development