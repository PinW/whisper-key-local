import os
import subprocess
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

    if is_installed_package():
        files = importlib.resources.files("whisper_key")
        return str(files / relative_path)

    return str(Path(__file__).parent / relative_path)

def setup_portaudio_path():
    # Called first in main.py - platform module imports break WASAPI
    if sys.platform != 'win32':
        return
    assets_dir = Path(resolve_asset_path('platform/windows/assets'))
    if assets_dir.exists():
        os.environ['PATH'] = str(assets_dir) + os.pathsep + os.environ.get('PATH', '')

def setup_nvidia_dll_path():
    if sys.platform != 'win32':
        return
    import site
    site_dirs = list(site.getsitepackages())
    site_dirs.append(site.getusersitepackages())

    nvidia_bin_dirs = []
    for site_dir in site_dirs:
        for bin_dir in sorted(Path(site_dir).glob('nvidia/*/bin')):
            if bin_dir.is_dir() and str(bin_dir) not in nvidia_bin_dirs:
                nvidia_bin_dirs.append(str(bin_dir))

    if nvidia_bin_dirs:
        os.environ['PATH'] = os.pathsep.join(nvidia_bin_dirs) + os.pathsep + os.environ.get('PATH', '')

def restart_or_exit(message_restart, message_exit):
    pyapp_exe = os.environ.get('PYAPP', '')
    if os.path.isfile(pyapp_exe):
        print(message_restart)
        subprocess.Popen([pyapp_exe], creationflags=subprocess.CREATE_NEW_CONSOLE)
    else:
        print(message_exit)
    sys.exit(0)


def get_version():
    if is_installed_package():
        import importlib.metadata
        return importlib.metadata.version("whisper-key-local")

    pyproject_path = Path(__file__).parent.parent.parent / "pyproject.toml"
    with open(pyproject_path, 'rb') as f:
        data = tomllib.load(f)
        return f"{data['project']['version']}-dev"