from pathlib import Path

def get_app_data_path():
    return Path.home() / '.whisperkey'

def open_file(path):
    import subprocess
    subprocess.run(['xdg-open', str(path)])