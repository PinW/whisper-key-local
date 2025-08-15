import os
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

def resolve_asset_path(asset_path: str) -> str:
    """
    Resolve asset file path relative to project root for PyInstaller compatibility.
    """
    if not asset_path:
        return asset_path
    
    if os.path.isabs(asset_path):
        return asset_path
    
    project_root = Path(os.path.dirname(os.path.abspath(__file__))).parent
    resolved_path = project_root / asset_path
    return str(resolved_path)