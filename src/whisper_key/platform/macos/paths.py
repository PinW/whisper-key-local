import subprocess
from pathlib import Path

def get_app_data_path():
    return Path.home() / '.whisperkey'

def open_file(path):
    subprocess.run(['open', str(path)])
