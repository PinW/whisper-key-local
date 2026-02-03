# macOS Keyboard Simulation (Phase 3.4)

## Goal

Implement `platform/macos/keyboard.py` using Quartz CGEvent to enable auto-paste on macOS.

## Interface Required

```python
def set_delay(delay: float):
    """Set pause between key events."""

def send_hotkey(*keys: str):
    """Send modifier combo (e.g., 'cmd', 'v' for paste)."""

def send_key(key: str):
    """Send single key (e.g., 'enter')."""
```

## Keys to Support

From `config.defaults.yaml`:
- **Paste**: `cmd+v` → keys: `['cmd', 'v']`
- **Enter**: `enter`

## Implementation

### Key Code Mappings

```python
# Quartz virtual key codes
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

# CGEvent modifier flags
MODIFIER_FLAGS = {
    'cmd': Quartz.kCGEventFlagMaskCommand,
    'command': Quartz.kCGEventFlagMaskCommand,
    'ctrl': Quartz.kCGEventFlagMaskControl,
    'control': Quartz.kCGEventFlagMaskControl,
    'shift': Quartz.kCGEventFlagMaskShift,
    'option': Quartz.kCGEventFlagMaskAlternate,
    'alt': Quartz.kCGEventFlagMaskAlternate,
}
```

### CGEvent Approach

```python
from Quartz import (
    CGEventCreateKeyboardEvent,
    CGEventPost,
    CGEventSetFlags,
    kCGHIDEventTap,
)

def send_key(key: str):
    key_code = KEY_CODES.get(key.lower())
    # Key down
    event = CGEventCreateKeyboardEvent(None, key_code, True)
    CGEventPost(kCGHIDEventTap, event)
    # Key up
    event = CGEventCreateKeyboardEvent(None, key_code, False)
    CGEventPost(kCGHIDEventTap, event)

def send_hotkey(*keys: str):
    # Separate modifiers from regular keys
    modifiers = [k for k in keys if k.lower() in MODIFIER_FLAGS]
    regular_keys = [k for k in keys if k.lower() not in MODIFIER_FLAGS]

    # Combine modifier flags
    flags = 0
    for mod in modifiers:
        flags |= MODIFIER_FLAGS[mod.lower()]

    # Send each regular key with modifiers applied
    for key in regular_keys:
        key_code = KEY_CODES.get(key.lower())
        # Key down with modifiers
        event = CGEventCreateKeyboardEvent(None, key_code, True)
        CGEventSetFlags(event, flags)
        CGEventPost(kCGHIDEventTap, event)
        # Key up
        event = CGEventCreateKeyboardEvent(None, key_code, False)
        CGEventSetFlags(event, flags)
        CGEventPost(kCGHIDEventTap, event)
```

## Permissions

Requires **Accessibility** permission in System Preferences → Privacy & Security → Accessibility.

Without this permission, `CGEventPost` will silently fail (no error, but no key events sent).

## Steps

- [x] Replace stub implementation in `platform/macos/keyboard.py`
  - ✅ Implemented KEY_CODES mapping for all letters and special keys
  - ✅ Implemented MODIFIER_FLAGS for cmd, ctrl, shift, option/alt
  - ✅ Implemented set_delay() with global _delay variable
  - ✅ Implemented send_key() with key-down/key-up events
  - ✅ Implemented send_hotkey() with modifier flag support
  - ✅ Added graceful fallback when Quartz unavailable
- [x] Add logging for debugging
  - ✅ Debug logging for delay changes
  - ✅ Debug logging for key/hotkey sends
  - ✅ Error logging for unknown keys
  - ✅ Warning when Quartz not available
- [ ] Test on macOS with Accessibility permission granted

## Testing

1. Enable auto-paste in config
2. Record speech → should auto-paste to active app
3. Test with auto-enter enabled → should paste + send enter
