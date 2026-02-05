import os
import sys
from pathlib import Path

def get_app_data_path():
    return Path(os.getenv('APPDATA')) / 'whisperkey'

def open_file(path):
    os.startfile(path)

def setup_portaudio_path():
    from ...utils import resolve_asset_path
    assets_dir = Path(resolve_asset_path('platform/windows/assets'))
    if assets_dir.exists():
        os.environ['PATH'] = str(assets_dir) + os.pathsep + os.environ.get('PATH', '')
