import logging
import threading
from dataclasses import dataclass, field
from typing import Callable, Optional

from Xlib import X, display
from Xlib.ext import record
from Xlib.protocol import rq

from .keycodes import KEYS, MODIFIERS

logger = logging.getLogger(__name__)


@dataclass
class ParsedBinding:
    original: str
    required_groups: list[set]
    press_callback: Callable
    release_callback: Callable | None
    is_active: bool = field(default=False)


_pressed: set[int] = set()
_bindings: list[ParsedBinding] = []
_display_record: Optional[display.Display] = None
_context = None
_running = False


def _parse_hotkey_string(hotkey_str: str) -> list[set] | None:
    parts = [p.strip().lower() for p in hotkey_str.split('+')]
    if not parts:
        return None

    groups = []
    for part in parts:
        if part in MODIFIERS:
            groups.append(set(MODIFIERS[part]))
        elif part in KEYS:
            groups.append({KEYS[part]})
        else:
            logger.warning(f"Unknown key in hotkey string: {part}")
            return None

    return groups


def _parse_binding(binding: list) -> ParsedBinding:
    hotkey_str = binding[0]
    press_cb = binding[1]
    release_cb = binding[2] if len(binding) > 2 else None

    required_groups = _parse_hotkey_string(hotkey_str)
    if required_groups is None:
        logger.warning(f"Failed to parse hotkey: {hotkey_str}")
        required_groups = []

    return ParsedBinding(
        original=hotkey_str,
        required_groups=required_groups,
        press_callback=press_cb,
        release_callback=release_cb,
    )


def _key_in_pressed(target) -> bool:
    return target in _pressed


def _all_groups_pressed(binding: ParsedBinding) -> bool:
    for group in binding.required_groups:
        if not any(_key_in_pressed(t) for t in group):
            return False
    return True


def _any_group_released(binding: ParsedBinding, released_key) -> bool:
    for group in binding.required_groups:
        if released_key in group:
            return True
    return False


def _callback(reply):
    if reply.category != record.FromServer:
        return
    if reply.client_swapped:
        return
    if not reply.data:
        return

    data = reply.data

    while data:
        event, data = rq.EventField(None).parse_binary_value(
            data,
            _display_record.display,
            None,
            None,
        )

        key = event.detail

        if event.type == X.KeyPress:
            if key in _pressed:
                continue

            _pressed.add(key)

            for binding in _bindings:
                if not binding.required_groups:
                    continue
                if binding.is_active:
                    continue
                if _all_groups_pressed(binding):
                    logger.debug(f"Press: {binding.original}")
                    binding.is_active = True
                    try:
                        threading.Thread(target=binding.press_callback, daemon=True).start()
                    except Exception as e:
                        logger.error(f"Error in press callback for {binding.original}: {e}")

        elif event.type == X.KeyRelease:
            _pressed.discard(key)

            for binding in _bindings:
                if not binding.is_active:
                    continue
                if not binding.required_groups:
                    continue
                if _any_group_released(binding, key):
                    logger.debug(f"Release: {binding.original}")
                    binding.is_active = False
                    if binding.release_callback:
                        try:
                            threading.Thread(target=binding.release_callback, daemon=True).start()
                        except Exception as e:
                            logger.error(f"Error in release callback for {binding.original}: {e}")


def register(bindings: list):
    global _bindings

    _bindings = [_parse_binding(b) for b in bindings]

    logger.info(f"Registered {len(_bindings)} hotkey bindings")
    for b in _bindings:
        logger.debug(f"  {b.original} -> required_groups={b.required_groups}")


def start():
    global _display_record, _context, _running

    if _running:
        return

    _display_record = display.Display()

    if not _display_record.has_extension("RECORD"):
        _display_record.close()
        _display_record = None
        raise RuntimeError("X RECORD extension is unavailable")

    _context = _display_record.record_create_context(
        0,
        [record.AllClients],
        [{
            'core_requests': (0, 0),
            'core_replies': (0, 0),
            'ext_requests': (0, 0, 0, 0),
            'ext_replies': (0, 0, 0, 0),
            'delivered_events': (0, 0),
            'device_events': (X.KeyPress, X.KeyRelease),
            'errors': (0, 0),
            'client_started': False,
            'client_died': False,
        }]
    )

    _running = True
    threading.Thread(target=_run_listener, daemon=True).start()

    logger.info("X RECORD hotkey listener started")


def _run_listener():
    try:
        _display_record.record_enable_context(_context, _callback)
    except Exception:
        pass
    finally:
        _cleanup()


def _cleanup():
    global _display_record, _context, _running

    if _display_record is not None:
        try:
            _display_record.record_disable_context(_context)
        except Exception:
            pass
        try:
            _display_record.record_free_context(_context)
        except Exception:
            pass
        try:
            _display_record.close()
        except Exception:
            pass
        _display_record = None
        _context = None

    _running = False


def stop():
    global _bindings, _pressed, _running

    if not _running:
        return

    _running = False
    _bindings = []
    _pressed.clear()

    if _display_record is not None:
        try:
            _display_record.record_disable_context(_context)
        except Exception:
            pass

    logger.info("X RECORD hotkey listener stopped")
