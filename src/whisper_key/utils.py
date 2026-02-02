import os
import sys
import importlib.resources
import tomllib
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

def parse_hotkey(hotkey_string: str) -> list:
    if not hotkey_string:
        return []
    return hotkey_string.lower().split('+')

def is_installed_package():
    # Check if running from an installed package
    return 'site-packages' in __file__

def get_user_app_data_path():
    from .platform import paths
    whisperkey_dir = paths.get_app_data_path()
    whisperkey_dir.mkdir(parents=True, exist_ok=True)
    return str(whisperkey_dir)

def open_file(path):
    from .platform import paths
    paths.open_file(path)

def resolve_asset_path(relative_path: str) -> str:
    
    if not relative_path or os.path.isabs(relative_path):
        return relative_path
    
    if getattr(sys, 'frozen', False): # PyInstaller
        return str(Path(sys._MEIPASS) / relative_path)
    
    if is_installed_package(): # pip / pipx
        files = importlib.resources.files("whisper_key")
        return str(files / relative_path)
    
    return str(Path(__file__).parent / relative_path) # Development

def add_portaudio_dll_to_search_path():
    if sys.platform != 'win32':
        return
    assets_dir = Path(resolve_asset_path('assets'))
    if assets_dir.exists():
        os.environ['PATH'] = str(assets_dir) + os.pathsep + os.environ.get('PATH', '')

def get_version():
    if getattr(sys, 'frozen', False): # PyInstaller
        version_file = resolve_asset_path("assets/version.txt")
        with open(version_file, 'r') as f:
            return f.read().strip()

    if is_installed_package(): # pip
        import importlib.metadata
        return importlib.metadata.version("whisper-key-local")

    # Development
    pyproject_path = Path(__file__).parent.parent.parent / "pyproject.toml"
    with open(pyproject_path, 'rb') as f:
        data = tomllib.load(f)
        return f"{data['project']['version']}-dev"