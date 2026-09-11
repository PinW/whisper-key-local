import logging
from pathlib import Path

logger = logging.getLogger(__name__)

ASSETS_DIR = Path(__file__).parent / "assets"


def get_tray_icons() -> dict:
    icons = {}
    for state in ["idle", "recording", "processing"]:
        icon_path = ASSETS_DIR / f"tray_{state}.png"
        if icon_path.exists():
            try:
                from PIL import Image
                icons[state] = Image.open(icon_path)
            except Exception as e:
                logger.warning(f"Failed to load tray icon {icon_path}: {e}")
                icons[state] = None
        else:
            icons[state] = None
    return icons


class TrayIcon:
    def __init__(self):
        pass

    def set_icon(self, state: str):
        pass

    def stop(self):
        pass