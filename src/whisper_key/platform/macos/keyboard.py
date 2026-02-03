import logging
import time

logger = logging.getLogger(__name__)

_delay = 0.0

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
except ImportError:
    _quartz_available = False
    logger.warning("Quartz not available - keyboard simulation disabled")


KEY_CODES = {
    'a': 0x00, 'b': 0x0B, 'c': 0x08, 'd': 0x02, 'e': 0x0E,
    'f': 0x03, 'g': 0x05, 'h': 0x04, 'i': 0x22, 'j': 0x26,
    'k': 0x28, 'l': 0x25, 'm': 0x2E, 'n': 0x2D, 'o': 0x1F,
    'p': 0x23, 'q': 0x0C, 'r': 0x0F, 's': 0x01, 't': 0x11,
    'u': 0x20, 'v': 0x09, 'w': 0x0D, 'x': 0x07, 'y': 0x10,
    'z': 0x06,
    'enter': 0x24, 'return': 0x24,
    'tab': 0x30, 'space': 0x31, 'delete': 0x33, 'escape': 0x35,
}

MODIFIER_FLAGS = {}
if _quartz_available:
    MODIFIER_FLAGS = {
        'cmd': kCGEventFlagMaskCommand,
        'command': kCGEventFlagMaskCommand,
        'ctrl': kCGEventFlagMaskControl,
        'control': kCGEventFlagMaskControl,
        'shift': kCGEventFlagMaskShift,
        'option': kCGEventFlagMaskAlternate,
        'alt': kCGEventFlagMaskAlternate,
    }


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
    CGEventPost(kCGHIDEventTap, event)

    if _delay > 0:
        time.sleep(_delay)

    event = CGEventCreateKeyboardEvent(None, key_code, False)
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
