from pathlib import Path
from PIL import Image

ASSETS_DIR = Path(__file__).parent / "assets"

def get_tray_icons() -> dict:
    return {
        "idle": Image.open(ASSETS_DIR / "tray_idle.png"),
        "recording": Image.open(ASSETS_DIR / "tray_recording.png"),
        "processing": Image.open(ASSETS_DIR / "tray_processing.png"),
    }
