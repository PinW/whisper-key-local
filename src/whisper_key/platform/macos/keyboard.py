import logging
import time

from .keycodes import KEY_CODES

logger = logging.getLogger(__name__)

_delay = 0.0
MODIFIER_FLAGS = {}

try:
    from Quartz import (
        CGEventCreateKeyboardEvent,
        CGEventPost,
        CGEventSetFlags,
        kCGHIDEventTap,
        kCGEventFlagMaskCommand,
        kCGEventFlagMaskControl,
        kCGEventFlagMaskShift,
        kCGEventFlagMaskAlternate,
    )
    _quartz_available = True
    MODIFIER_FLAGS = {
        'cmd': kCGEventFlagMaskCommand,
        'command': kCGEventFlagMaskCommand,
        'ctrl': kCGEventFlagMaskControl,
        'control': kCGEventFlagMaskControl,
        'shift': kCGEventFlagMaskShift,
        'option': kCGEventFlagMaskAlternate,
        'alt': kCGEventFlagMaskAlternate,
    }
except ImportError:
    _quartz_available = False
    logger.warning("Quartz not available - keyboard simulation disabled")


def set_delay(delay: float):
    global _delay
    _delay = delay
    logger.debug(f"Keyboard delay set to {delay}s")


def send_key(key: str):
    if not _quartz_available:
        logger.warning("Cannot send key - Quartz not available")
        return

    key_lower = key.lower()
    key_code = KEY_CODES.get(key_lower)
    if key_code is None:
        logger.error(f"Unknown key: {key}")
        return

    logger.debug(f"Sending key: {key} (code: {hex(key_code)})")

    event = CGEventCreateKeyboardEvent(None, key_code, True)
    CGEventSetFlags(event, 0)
    CGEventPost(kCGHIDEventTap, event)

    if _delay > 0:
        time.sleep(_delay)

    event = CGEventCreateKeyboardEvent(None, key_code, False)
    CGEventSetFlags(event, 0)
    CGEventPost(kCGHIDEventTap, event)


def send_hotkey(*keys: str):
    if not _quartz_available:
        logger.warning("Cannot send hotkey - Quartz not available")
        return

    modifiers = [k for k in keys if k.lower() in MODIFIER_FLAGS]
    regular_keys = [k for k in keys if k.lower() not in MODIFIER_FLAGS]

    flags = 0
    for mod in modifiers:
        flags |= MODIFIER_FLAGS[mod.lower()]

    logger.debug(f"Sending hotkey: {'+'.join(keys)} (modifiers: {modifiers}, keys: {regular_keys})")

    for key in regular_keys:
        key_code = KEY_CODES.get(key.lower())
        if key_code is None:
            logger.error(f"Unknown key in hotkey: {key}")
            continue

        event = CGEventCreateKeyboardEvent(None, key_code, True)
        CGEventSetFlags(event, flags)
        CGEventPost(kCGHIDEventTap, event)

        if _delay > 0:
            time.sleep(_delay)

        event = CGEventCreateKeyboardEvent(None, key_code, False)
        CGEventSetFlags(event, flags)
        CGEventPost(kCGHIDEventTap, event)


def type_text(text: str):
    pass  # SendInput method not used in macOS
