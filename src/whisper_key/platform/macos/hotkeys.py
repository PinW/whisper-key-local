import logging
from dataclasses import dataclass, field
from typing import Callable

from AppKit import NSEvent

from .keycodes import KEY_CODES

logger = logging.getLogger(__name__)

NSKeyDownMask = 1 << 10
NSFlagsChangedMask = 1 << 12

MODIFIER_FLAGS = {
    'ctrl': 1 << 18,
    'control': 1 << 18,
    'cmd': 1 << 20,
    'command': 1 << 20,
    'option': 1 << 19,
    'alt': 1 << 19,
    'shift': 1 << 17,
    'fn': 1 << 23,
    'function': 1 << 23,
}

MODIFIER_MASK = (1 << 18) | (1 << 20) | (1 << 19) | (1 << 17) | (1 << 23)


@dataclass
class ParsedBinding:
    original: str
    modifiers: int
    keycode: int | None
    press_callback: Callable
    release_callback: Callable | None
    is_active: bool = field(default=False)


class ModifierStateTracker:
    def __init__(self):
        self.previous_flags = 0

    def update(self, new_flags: int) -> tuple[int, int, int, int]:
        new_flags = new_flags & MODIFIER_MASK
        old_flags = self.previous_flags
        pressed = new_flags & ~old_flags
        released = old_flags & ~new_flags
        self.previous_flags = new_flags
        return old_flags, new_flags, pressed, released

    def reset(self):
        self.previous_flags = 0


_monitor = None
_bindings: list[ParsedBinding] = []
_state = ModifierStateTracker()


def _parse_hotkey_string(hotkey_str: str) -> tuple[int, int | None]:
    parts = [p.strip().lower() for p in hotkey_str.split('+')]

    modifiers = 0
    keycode = None

    for part in parts:
        if part in ('win', 'window', 'windows', 'super'):
            continue

        if part in MODIFIER_FLAGS:
            modifiers |= MODIFIER_FLAGS[part]
        elif part in KEY_CODES:
            keycode = KEY_CODES[part]
        else:
            logger.warning(f"Unknown key in hotkey string: {part}")

    return modifiers, keycode


def _parse_binding(binding: list) -> ParsedBinding:
    hotkey_str = binding[0]
    press_cb = binding[1]
    release_cb = binding[2] if len(binding) > 2 else None

    modifiers, keycode = _parse_hotkey_string(hotkey_str)

    return ParsedBinding(
        original=hotkey_str,
        modifiers=modifiers,
        keycode=keycode,
        press_callback=press_cb,
        release_callback=release_cb,
    )


def _handle_flags_changed(event):
    old_flags, new_flags, pressed, released = _state.update(event.modifierFlags())

    for binding in _bindings:
        if binding.keycode is not None:
            continue

        if new_flags == binding.modifiers and old_flags != binding.modifiers:
            logger.debug(f"Modifier-only hotkey pressed: {binding.original}")
            binding.is_active = True
            try:
                binding.press_callback()
            except Exception as e:
                logger.error(f"Error in press callback for {binding.original}: {e}")

        elif binding.is_active and (released & binding.modifiers):
            logger.debug(f"Modifier-only hotkey released: {binding.original}")
            binding.is_active = False
            if binding.release_callback:
                try:
                    binding.release_callback()
                except Exception as e:
                    logger.error(f"Error in release callback for {binding.original}: {e}")


def _handle_key_down(event):
    current_flags = event.modifierFlags() & MODIFIER_MASK
    key_code = event.keyCode()

    logger.debug(f"KeyDown: keycode={key_code}, flags={current_flags:#x}")

    for binding in _bindings:
        if binding.keycode is None:
            continue

        if key_code == binding.keycode and current_flags == binding.modifiers:
            logger.debug(f"Traditional hotkey pressed: {binding.original}")
            try:
                binding.press_callback()
            except Exception as e:
                logger.error(f"Error in press callback for {binding.original}: {e}")
            return


def _handle_event(event):
    event_type = event.type()

    if event_type == 12:  # NSFlagsChanged
        _handle_flags_changed(event)
    elif event_type == 10:  # NSKeyDown
        _handle_key_down(event)


def register(bindings: list):
    global _bindings
    _bindings = [_parse_binding(b) for b in bindings]
    logger.info(f"Registered {len(_bindings)} hotkey bindings")
    for b in _bindings:
        binding_type = "modifier-only" if b.keycode is None else "traditional"
        logger.debug(f"  {b.original} -> modifiers={b.modifiers:#x}, keycode={b.keycode} ({binding_type})")


def start():
    global _monitor
    _state.reset()

    mask = NSKeyDownMask | NSFlagsChangedMask
    _monitor = NSEvent.addGlobalMonitorForEventsMatchingMask_handler_(mask, _handle_event)

    if _monitor is None:
        logger.error("Failed to create event monitor - check Accessibility permissions in System Settings > Privacy & Security > Accessibility")
    else:
        logger.info("NSEvent hotkey monitor started")


def stop():
    global _monitor
    if _monitor:
        NSEvent.removeMonitor_(_monitor)
        _monitor = None
        logger.info("NSEvent hotkey monitor stopped")

    for binding in _bindings:
        binding.is_active = False
