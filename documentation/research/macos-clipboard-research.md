# macOS Clipboard and Paste Simulation Research

## Executive Summary

**Current Windows implementation uses:**
- `pyperclip` for clipboard operations (already cross-platform)
- `pyautogui` for key simulation (Ctrl+V)
- `win32gui` for foreground window detection

**macOS recommendation:**
- **Clipboard:** pyperclip works unchanged
- **Key simulation:** Quartz CGEvent (pyautogui/pynput don't work reliably)
- **Foreground window:** NSWorkspace from PyObjC
- **Permissions:** None needed for key simulation (unlike hotkey detection)

---

## 1. Current Windows Implementation

From `clipboard_manager.py`:

```python
# Typical auto-paste workflow
original_content = pyperclip.paste()          # Backup clipboard
pyperclip.copy(transcribed_text)              # Put text on clipboard
pyautogui.hotkey(*self.paste_keys)            # Simulate Ctrl+V
pyperclip.copy(original_content)              # Restore clipboard
```

**Windows-specific APIs:**
- `pyautogui.hotkey()` - Key simulation
- `win32gui.GetForegroundWindow()` - Get active window handle

---

## 2. macOS Key Simulation Options

### pyautogui on macOS - NOT RECOMMENDED

- Designed primarily for Windows
- No native macOS key simulation support
- Missing support for Cmd modifier

### pynput on macOS - PARTIALLY BROKEN

| Keys | Status |
|------|--------|
| Cmd+V | ✅ Works |
| Ctrl+V | ❌ Broken |
| Alt+V | ❌ Broken |

Same underlying issue as hotkey detection - `CGEventKeyboardGetUnicodeString` returns modified characters.

### Quartz CGEvent (PyObjC) - RECOMMENDED

Native macOS API, works with all modifiers, no permissions needed.

```python
from Quartz import CGEventCreateKeyboardEvent, CGEventPost, kCGSessionEventTap

KEY_CODES = {
    'v': 9,
    'return': 36,
    'enter': 36,
    'space': 49,
}

MODIFIERS = {
    'cmd': (1 << 20),
    'ctrl': (1 << 18),
    'shift': (1 << 17),
    'alt': (1 << 19),
    'option': (1 << 19),
}

def send_hotkey(*keys):
    """Send key combination: send_hotkey('cmd', 'v')"""
    if not keys:
        return

    actual_key = keys[-1].lower()
    modifiers = [k.lower() for k in keys[:-1]]

    key_code = KEY_CODES.get(actual_key)
    if key_code is None:
        raise ValueError(f"Unknown key: {actual_key}")

    modifier_flags = 0
    for mod in modifiers:
        modifier_flags |= MODIFIERS[mod]

    # Press
    event_down = CGEventCreateKeyboardEvent(None, key_code, True)
    event_down.flags = modifier_flags
    CGEventPost(kCGSessionEventTap, event_down)

    # Release
    import time
    time.sleep(0.01)
    event_up = CGEventCreateKeyboardEvent(None, key_code, False)
    event_up.flags = modifier_flags
    CGEventPost(kCGSessionEventTap, event_up)
```

---

## 3. Clipboard APIs

### pyperclip - USE AS-IS

Works on macOS unchanged (uses `pbcopy`/`pbpaste` commands internally).

```python
import pyperclip
pyperclip.copy(text)       # Copy
content = pyperclip.paste() # Read
```

No changes needed. No reliability issues like Windows native APIs.

### NSPasteboard - NOT NEEDED

Native macOS API via PyObjC. Only use if pyperclip has issues (it won't).

---

## 4. Foreground Window Detection

### Windows
```python
hwnd = win32gui.GetForegroundWindow()
title = win32gui.GetWindowText(hwnd)
```

### macOS (NSWorkspace)
```python
from AppKit import NSWorkspace

workspace = NSWorkspace.sharedWorkspace()
active_app = workspace.activeApplication()
# Returns: bundle_id, name, pid (not window handle/title)
```

**Note:** macOS is app-centric, not window-centric. Getting window titles requires Accessibility API (needs permission).

---

## 5. Permissions

| Feature | Permission Required |
|---------|-------------------|
| Key simulation (CGEvent) | ❌ None |
| Clipboard (pyperclip) | ❌ None |
| App detection (NSWorkspace) | ❌ None |
| Window titles | ✅ Accessibility |
| Hotkey detection | ✅ Accessibility |

Key simulation via Quartz CGEvent does NOT require accessibility permission - this is a significant advantage.

---

## 6. Configuration Mapping

| Windows | macOS |
|---------|-------|
| `ctrl+v` | `cmd+v` |
| `ctrl+shift+enter` | `cmd+shift+return` |

Options:
1. Platform-aware defaults in code
2. Separate config values per platform
3. Let users configure (most flexible)

---

## 7. Implementation Plan

### Platform Abstraction Layer

```
src/whisper_key/platform/
├── __init__.py           # Platform detection & imports
├── keyboard_windows.py   # pyautogui wrapper
└── keyboard_macos.py     # Quartz CGEvent
```

### keyboard_windows.py
```python
import pyautogui

def send_hotkey(*keys):
    pyautogui.hotkey(*keys)

def send_key(key):
    pyautogui.press(key)
```

### keyboard_macos.py
```python
# Quartz CGEvent implementation (see section 2)
```

### Update clipboard_manager.py
```python
from .platform import send_hotkey, send_key

# Replace: pyautogui.hotkey(*self.paste_keys)
# With:    send_hotkey(*self.paste_keys)

# Replace: pyautogui.press('enter')
# With:    send_key('enter')
```

---

## 8. Dependencies

Add to `pyproject.toml`:
```toml
"pyobjc-framework-Quartz>=10.0; platform_system=='Darwin'",
"pyobjc-framework-AppKit>=10.0; platform_system=='Darwin'",
```

---

## 9. Windows vs macOS Comparison

| Aspect | Windows | macOS |
|--------|---------|-------|
| Clipboard | pyperclip | pyperclip (unchanged) |
| Key simulation | pyautogui | Quartz CGEvent |
| Foreground app | win32gui | NSWorkspace |
| Permissions | None | None (for paste) |
| Paste hotkey | Ctrl+V | Cmd+V |

---

## 10. macOS Keyboard Simulation Libraries

| Library | Type | macOS Status | Repository |
|---------|------|--------------|------------|
| **PyObjC (Quartz/CGEvent)** | Native framework binding | ✅ Recommended | https://github.com/ronaldoussoren/pyobjc |
| **pyautogui** | Cross-platform | ❌ Unreliable on macOS | https://github.com/asweigart/pyautogui |
| **pynput** | Cross-platform | ⚠️ Ctrl/Alt broken | https://github.com/moses-palmer/pynput |
| **keyboard** | Cross-platform | ❌ Unmaintained (2020) | https://github.com/boppreh/keyboard |
| **QuickMacHotKey** | macOS native (detection only) | ✅ For hotkey listening | https://github.com/glyph/QuickMacHotKey |

**Notes:**
- CGEvent (via PyObjC) is for **simulating** keypresses
- QuickMacHotKey is for **detecting** hotkeys (not simulation)
- pynput issue tracker: https://github.com/moses-palmer/pynput/issues/297

---

*Generated: 2026-02-02*
