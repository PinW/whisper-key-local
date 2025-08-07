# py-build/config.py
import pathlib

# Project Information
APP_NAME = "whisper-key"
APP_VERSION = "0.1.0"
ENTRY_POINT = "whisper-key.py"
ROOT_DIR = pathlib.Path(__file__).parent.parent

# Build Output
DIST_DIR = ROOT_DIR / f"dist/{APP_NAME}-v{APP_VERSION}"
VENV_PATH = ROOT_DIR / f"venv-{APP_NAME}"

# PyInstaller Configuration
SPEC_FILE = pathlib.Path(__file__).parent / f"{APP_NAME}.spec"
BUILD_ARGS = [
    "--clean",                    # Clean build cache
    "--noconfirm",               # Overwrite output without confirmation
    "--onedir",                  # Create one-folder bundle
    f"--distpath={DIST_DIR.parent}",  # Output directory
    f"--specpath={ROOT_DIR}",    # Spec file location
]