import os
import sys
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

def resolve_asset_path(relative_path: str) -> str:
    
    if not relative_path:
        return relative_path
    
    if os.path.isabs(relative_path):
        return relative_path
    
    # PyInstaller mode (existing)
    if getattr(sys, 'frozen', False):
        base_dir = Path(sys._MEIPASS)
        return str(base_dir / relative_path)
    
    # pip/pipx installation mode
    try:
        import importlib.resources as pkg_resources
        package = "whisper_key"
        resource_path = Path(relative_path)
        
        # Handle nested paths like "assets/sounds/record_start.wav"
        if resource_path.parts[0] == "assets":
            sub_package = ".".join([package] + list(resource_path.parts[:-1]))
            filename = resource_path.parts[-1]
            
            with pkg_resources.path(sub_package, filename) as path:
                return str(path)
        
        # Handle config files directly in package root
        elif resource_path.name in ["config.defaults.yaml"]:
            with pkg_resources.path(package, resource_path.name) as path:
                return str(path)
                
    except (ImportError, FileNotFoundError, AttributeError):
        pass
    
    # Development mode (existing fallback)
    package_dir = Path(__file__).parent
    
    # Check if the file exists in the package directory first
    package_path = package_dir / relative_path
    if package_path.exists():
        return str(package_path)
    
    # Fallback to old project root for compatibility
    project_root = package_dir.parent.parent
    return str(project_root / relative_path)