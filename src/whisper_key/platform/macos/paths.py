import subprocess
from pathlib import Path

def get_app_data_path():
    return Path.home() / 'Library' / 'Application Support' / 'whisperkey'

def open_file(path):
    subprocess.run(['open', str(path)])

def setup_portaudio_path():
    pass
