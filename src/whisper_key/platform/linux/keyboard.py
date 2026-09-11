import logging
import time
from typing import Optional

from Xlib import X, XK, display
from Xlib.ext import xtest

logger = logging.getLogger(__name__)

KEYSYMS = {
    'a': XK.XK_a, 'b': XK.XK_b, 'c': XK.XK_c, 'd': XK.XK_d, 'e': XK.XK_e, 'f': XK.XK_f, 'g': XK.XK_g, 'h': XK.XK_h,
    'i': XK.XK_i, 'j': XK.XK_j, 'k': XK.XK_k, 'l': XK.XK_l, 'm': XK.XK_m, 'n': XK.XK_n, 'o': XK.XK_o, 'p': XK.XK_p,
    'q': XK.XK_q, 'r': XK.XK_r, 's': XK.XK_s, 't': XK.XK_t, 'u': XK.XK_u, 'v': XK.XK_v, 'w': XK.XK_w, 'x': XK.XK_x,
    'y': XK.XK_y, 'z': XK.XK_z,
    '0': XK.XK_0, '1': XK.XK_1, '2': XK.XK_2, '3': XK.XK_3, '4': XK.XK_4,
    '5': XK.XK_5, '6': XK.XK_6, '7': XK.XK_7, '8': XK.XK_8, '9': XK.XK_9,
    'space': XK.XK_space,
    'enter': XK.XK_Return, 'return': XK.XK_Return,
    'tab': XK.XK_Tab,
    'delete': XK.XK_Delete, 'backspace': XK.XK_BackSpace,
    'escape': XK.XK_Escape, 'esc': XK.XK_Escape,
    'f1': XK.XK_F1, 'f2': XK.XK_F2, 'f3': XK.XK_F3, 'f4': XK.XK_F4, 'f5': XK.XK_F5, 'f6': XK.XK_F6,
    'f7': XK.XK_F7, 'f8': XK.XK_F8, 'f9': XK.XK_F9, 'f10': XK.XK_F10, 'f11': XK.XK_F11, 'f12': XK.XK_F12,
    '.': XK.XK_period, ',': XK.XK_comma, '/': XK.XK_slash, ';': XK.XK_semicolon, "'": XK.XK_apostrophe,
    '[': XK.XK_bracketleft, ']': XK.XK_bracketright, '-': XK.XK_minus, '=': XK.XK_equal, '`': XK.XK_grave,
    '\\': XK.XK_backslash,
    'up': XK.XK_Up, 'down': XK.XK_Down, 'left': XK.XK_Left, 'right': XK.XK_Right,
    'home': XK.XK_Home, 'end': XK.XK_End, 'pageup': XK.XK_Page_Up, 'pagedown': XK.XK_Page_Down,
    'insert': XK.XK_Insert,
    'ctrl': XK.XK_Control_L, 'control': XK.XK_Control_L, 'lctrl': XK.XK_Control_L, 'rctrl': XK.XK_Control_R,
    'shift': XK.XK_Shift_L, 'lshift': XK.XK_Shift_L, 'rshift': XK.XK_Shift_R,
    'alt': XK.XK_Alt_L, 'lalt': XK.XK_Alt_L, 'ralt': XK.XK_Alt_R,
    'super': XK.XK_Super_L, 'win': XK.XK_Super_L, 'lwin': XK.XK_Super_L, 'rwin': XK.XK_Super_R,
    'cmd': XK.XK_Super_L, 'command': XK.XK_Super_L,
}

MODIFIER_MASKS = {
    'ctrl': 1 << 2, 'control': 1 << 2, 'lctrl': 1 << 2, 'rctrl': 1 << 3,
    'shift': 1 << 0, 'lshift': 1 << 0, 'rshift': 1 << 1,
    'alt': 1 << 3, 'lalt': 1 << 3, 'ralt': 1 << 5,
    'super': 1 << 4, 'win': 1 << 4, 'lwin': 1 << 4, 'rwin': 1 << 13,
    'cmd': 1 << 4, 'command': 1 << 4,
}

_display: Optional[display.Display] = None
_delay = 0.0


def _get_display():
    global _display
    if _display is None:
        _display = display.Display()
    return _display


def validate_delivery_method(method: str) -> str:
    if method == "type":
        logger.warning("delivery_method 'type' not supported on Linux X11, using 'paste'")
        return "paste"
    return method


def set_delay(delay: float):
    global _delay
    _delay = delay
    logger.debug(f"Keyboard delay set to {delay}s")


def _keysym_to_keycode(keysym_name: str) -> int:
    d = _get_display()
    keysym = KEYSYMS.get(keysym_name.lower())
    if keysym is None:
        raise ValueError(f"Unknown key: {keysym_name}")
    return d.keysym_to_keycode(keysym)


def send_key(key: str):
    d = _get_display()
    key_lower = key.lower()

    try:
        keycode = _keysym_to_keycode(key_lower)
    except ValueError as e:
        logger.error(str(e))
        return

    logger.debug(f"Sending key: {key} (keycode: {keycode})")

    xtest.fake_input(d, X.KeyPress, keycode)

    if _delay > 0:
        time.sleep(_delay)

    xtest.fake_input(d, X.KeyRelease, keycode)
    d.sync()


def send_hotkey(*keys: str):
    d = _get_display()

    modifiers = [k for k in keys if k.lower() in MODIFIER_MASKS]
    regular_keys = [k for k in keys if k.lower() not in MODIFIER_MASKS]

    modifier_keycodes = []
    for mod in modifiers:
        try:
            keycode = _keysym_to_keycode(mod.lower())
            modifier_keycodes.append(keycode)
        except ValueError as e:
            logger.error(str(e))

    logger.debug(f"Sending hotkey: {'+'.join(keys)} (modifiers: {modifiers}, keys: {regular_keys})")

    for keycode in modifier_keycodes:
        xtest.fake_input(d, X.KeyPress, keycode)

    if _delay > 0:
        time.sleep(_delay)

    for key in regular_keys:
        try:
            keycode = _keysym_to_keycode(key.lower())
            xtest.fake_input(d, X.KeyPress, keycode)

            if _delay > 0:
                time.sleep(_delay)

            xtest.fake_input(d, X.KeyRelease, keycode)
        except ValueError as e:
            logger.error(str(e))

    for keycode in reversed(modifier_keycodes):
        xtest.fake_input(d, X.KeyRelease, keycode)

    d.sync()


def type_text(text: str):
    d = _get_display()

    for char in text:
        if char == "\n":
            keycode = d.keysym_to_keycode(XK.XK_Return)
            xtest.fake_input(d, X.KeyPress, keycode)
            if _delay > 0:
                time.sleep(_delay)
            xtest.fake_input(d, X.KeyRelease, keycode)
        elif char == "\t":
            keycode = d.keysym_to_keycode(XK.XK_Tab)
            xtest.fake_input(d, X.KeyPress, keycode)
            if _delay > 0:
                time.sleep(_delay)
            xtest.fake_input(d, X.KeyRelease, keycode)
        else:
            try:
                keysym = XK.string_to_keysym(char)
                if keysym != XK.NoSymbol:
                    keycode = d.keysym_to_keycode(keysym)
                    xtest.fake_input(d, X.KeyPress, keycode)
                    if _delay > 0:
                        time.sleep(_delay)
                    xtest.fake_input(d, X.KeyRelease, keycode)
            except Exception as e:
                logger.warning(f"Could not type character '{char}': {e}")

    d.sync()