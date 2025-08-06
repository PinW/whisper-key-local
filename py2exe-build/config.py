# build/config.py
import pathlib
import glob

# --- General Project Info ---
APP_NAME = "WhisperKey"
APP_VERSION = "0.1.0"
ENTRY_POINT = "whisper-key.py"
ROOT_DIR = pathlib.Path(__file__).parent.parent

# --- Build Output ---
DIST_DIR = ROOT_DIR / f"dist/{APP_NAME}-v{APP_VERSION}"

# --- py2exe Configuration ---
PY2EXE_OPTIONS = {
    "includes": [
        "win32gui", "win32con", "win32clipboard", "global_hotkeys",
        "pystray", "PIL", "sounddevice", "pyperclip",
        # Explicitly include our src modules
        "src.config_manager", "src.audio_recorder", "src.hotkey_listener",
        "src.whisper_engine", "src.clipboard_manager", "src.state_manager",
        "src.system_tray", "src.audio_feedback", "src.utils"
    ],
    "packages": ["faster_whisper", "src"],
    "excludes": ["importlib_metadata"],  # Try to reduce duplicate warnings
    "optimize": 2,
    "skip_archive": True,  # Don't create library.zip - extract all files (Python 3.12+ compatible)
}

# --- Asset Bundling (using glob for automation) ---
DATA_FILES = [
    # config.defaults.yaml at the root
    ("", [str(ROOT_DIR / "config.defaults.yaml")]),
    # All .png assets
    ("assets", glob.glob(str(ROOT_DIR / "assets/*.png"))),
    # All .wav sound files
    ("assets/sounds", glob.glob(str(ROOT_DIR / "assets/sounds/*.wav"))),
]

# Add sounddevice DLL extraction - maintain exact directory structure
import site
import os
for site_dir in site.getsitepackages():
    sounddevice_data = os.path.join(site_dir, "_sounddevice_data")
    if os.path.exists(sounddevice_data):
        # Include sounddevice data files maintaining exact directory structure
        for root, dirs, files in os.walk(sounddevice_data):
            if files:
                rel_path = os.path.relpath(root, site_dir)
                file_paths = [os.path.join(root, f) for f in files]
                DATA_FILES.append((rel_path, file_paths))
        break