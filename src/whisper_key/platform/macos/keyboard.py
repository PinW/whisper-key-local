import logging

logger = logging.getLogger(__name__)

_warned = False

def set_delay(delay: float):
    pass

def send_hotkey(*keys: str):
    global _warned
    if not _warned:
        logger.warning("Keyboard simulation not yet implemented on macOS - paste will not work")
        _warned = True

def send_key(key: str):
    global _warned
    if not _warned:
        logger.warning("Keyboard simulation not yet implemented on macOS - paste will not work")
        _warned = True
