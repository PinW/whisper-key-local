# macOS Global Hotkey Libraries for Python

## Executive Summary

**Recommendation: Platform-native libraries** - Use `global-hotkeys` on Windows and `QuickMacHotKey` on macOS. This gives reliable modifier support on both platforms without the Ctrl/Alt bugs in pynput. The libraries are small and the implementation overhead is minimal.

---

## Library Comparison

| Library | macOS Support | Maintained | Modifier Support | Permissions |
|---------|--------------|------------|------------------|-------------|
| **QuickMacHotKey** | ✅ Native | ✅ Active | ✅ All modifiers | Accessibility |
| **pynput** | ✅ Full | ✅ Active | ⚠️ Cmd/Shift only | Accessibility |
| **keyboard** | ⚠️ Experimental | ❌ Unmaintained (2020) | Unknown | Accessibility |
| **PyObjC direct** | ✅ Native | ✅ Active | ✅ All modifiers | Accessibility |

---

## QuickMacHotKey ⭐ Recommended for macOS

**Install:** `pip install quickmachotkey`

Native macOS hotkey binding using the same undocumented Carbon APIs that apps like Alfred and Raycast use.

### Usage
```python
from quickmachotkey import quickHotKey, mask
from quickmachotkey.constants import kVK_Space, controlKey, shiftKey

@quickHotKey(virtualKey=kVK_Space, modifierMask=mask(controlKey, shiftKey))
def on_record_hotkey() -> None:
    print("Ctrl+Shift+Space pressed")

# Requires NSApplication event loop
from AppKit import NSApplication
NSApplication.sharedApplication().run()
```

### Pros
- All modifier keys work (Ctrl, Alt/Option, Cmd, Shift)
- Native macOS API - stable and reliable
- Lightweight (~34 stars, actively maintained)
- Same hotkey syntax as Windows (Ctrl+Shift+Space works!)

### Cons
- macOS only
- Requires PyObjC
- Must run NSApplication event loop
- Uses virtual key codes (need lookup table)

### Virtual Key Code Reference
```python
from quickmachotkey.constants import (
    kVK_Space,      # Space
    kVK_Return,     # Enter
    kVK_ANSI_R,     # R key
    cmdKey,         # Cmd modifier
    controlKey,     # Ctrl modifier
    optionKey,      # Alt/Option modifier
    shiftKey,       # Shift modifier
)
```

---

## pynput (Cross-platform, but macOS limitations)

**Install:** `pip install pynput`

### macOS Limitations

**Critical Issue:** Ctrl and Alt modifiers don't work on macOS.

From [GitHub Issue #297](https://github.com/moses-palmer/pynput/issues/297):
> "On Mac, hotkeys with the modifiers ctrl or alt simply don't work."

**Root Cause:** `CGEventKeyboardGetUnicodeString` returns modified characters instead of base keys.

**Status:** Open since 2020, no fix.

**Working:** `<cmd>+<key>`, `<shift>+<key>`, single keys
**Broken:** `<ctrl>+<key>`, `<alt>+<key>`

### Function Keys
F1-F12 issues were **fixed** in July 2024.

---

## keyboard Library

**Status: Not Recommended**

- "Experimental OS X support"
- Last release: March 2020, unmaintained
- Key suppression not available on macOS

---

## Accessibility Permissions (macOS)

All hotkey solutions require accessibility permissions. Here's how to handle this gracefully.

### Check Permission Status

```python
from ApplicationServices import AXIsProcessTrusted

def has_accessibility_permission() -> bool:
    return AXIsProcessTrusted()
```

### Trigger System Permission Dialog

Use `AXIsProcessTrustedWithOptions` with `kAXTrustedCheckOptionPrompt` to show the macOS permission dialog:

```python
from ApplicationServices import (
    AXIsProcessTrustedWithOptions,
    kAXTrustedCheckOptionPrompt
)
from Foundation import NSDictionary

def request_accessibility_permission() -> bool:
    options = NSDictionary.dictionaryWithObject_forKey_(
        True,
        kAXTrustedCheckOptionPrompt
    )
    return AXIsProcessTrustedWithOptions(options)
```

This will:
1. Check if permission is granted
2. If not, show the system "app wants to control your computer" dialog
3. Add the app to the Accessibility list automatically
4. Return current permission status

**Note:** The dialog only appears once. After that, user must manually toggle in System Preferences.

### Open System Preferences Directly

```python
import subprocess

def open_accessibility_settings():
    # Works on macOS Monterey and earlier
    url = "x-apple.systempreferences:com.apple.preference.security?Privacy_Accessibility"
    subprocess.run(["open", url])
```

Or with PyObjC:
```python
from AppKit import NSWorkspace
from Foundation import NSURL

def open_accessibility_settings():
    url = NSURL.URLWithString_(
        "x-apple.systempreferences:com.apple.preference.security?Privacy_Accessibility"
    )
    NSWorkspace.sharedWorkspace().openURL_(url)
```

**macOS Sonoma+ URL:**
```python
url = "x-apple.systempreferences:com.apple.settings.PrivacySecurity.extension?Privacy_Accessibility"
```

### Recommended UX Flow

```python
import platform

def ensure_accessibility_permission():
    if platform.system() != "Darwin":
        return True

    from ApplicationServices import (
        AXIsProcessTrusted,
        AXIsProcessTrustedWithOptions,
        kAXTrustedCheckOptionPrompt
    )
    from Foundation import NSDictionary

    # Already granted?
    if AXIsProcessTrusted():
        return True

    # Show system dialog (only works first time)
    options = NSDictionary.dictionaryWithObject_forKey_(
        True, kAXTrustedCheckOptionPrompt
    )
    AXIsProcessTrustedWithOptions(options)

    # Check again - user may have granted immediately
    if AXIsProcessTrusted():
        return True

    # Still no permission - show helpful message
    print("⚠️  Accessibility permission required for global hotkeys")
    print("   Please enable in: System Preferences → Privacy & Security → Accessibility")
    print("   Then restart the app.")

    # Optionally open settings for them
    import subprocess
    subprocess.run(["open", "x-apple.systempreferences:com.apple.preference.security?Privacy_Accessibility"])

    return False
```

### Important Limitations

1. **Sandboxed apps cannot use AXIsProcessTrustedWithOptions** - the dialog won't appear
2. **No programmatic granting** - user must manually toggle the checkbox
3. **App restart usually required** after granting permission
4. **When running from terminal**, Terminal.app itself needs permission, not just the Python script
5. **Bundled .app** gets its own entry in the Accessibility list

### Threading Caveat

Permission dialogs must run on the main thread. If using background threads:
```python
# Error: "NSWindow drag regions should only be invalidated on the Main Thread!"
# Solution: Use multiprocessing or dispatch to main thread
```

---

## Recommendation for whisper-key-local

### ⭐ Recommended: Platform-native implementations

```python
# src/whisper_key/platform/__init__.py
import platform

if platform.system() == "Darwin":
    from .hotkeys_macos import MacHotkeyListener as HotkeyListener
else:
    from .hotkeys_windows import WindowsHotkeyListener as HotkeyListener
```

| Platform | Library | Hotkey Example |
|----------|---------|----------------|
| Windows | `global-hotkeys` | `ctrl + shift + space` |
| macOS | `QuickMacHotKey` | `controlKey + shiftKey + kVK_Space` |

**Pros:**
- All modifiers work on both platforms
- Same user-facing hotkey (Ctrl+Shift+Space) works everywhere
- Native, reliable implementations
- Small dependency footprint

**Cons:**
- Two implementations to maintain
- Different APIs (but can be abstracted)

### pyproject.toml Changes

```toml
dependencies = [
    # ... existing ...
    "global-hotkeys>=0.1.7; platform_system=='Windows'",
    "quickmachotkey>=0.1.0; platform_system=='Darwin'",
    "pyobjc-framework-ApplicationServices>=10.0; platform_system=='Darwin'",
]
```

---

## Sources

- [QuickMacHotKey](https://github.com/glyph/QuickMacHotKey)
- [pynput PyPI](https://pypi.org/project/pynput/)
- [pynput Platform Limitations](https://pynput.readthedocs.io/en/latest/limitations.html)
- [pynput Issue #297 - Ctrl/Alt on macOS](https://github.com/moses-palmer/pynput/issues/297)
- [AXIsProcessTrustedWithOptions Apple Docs](https://developer.apple.com/documentation/applicationservices/1459186-axisprocesstrustedwithoptions)
- [macOS System Preferences URL Schemes](https://gist.github.com/rmcdongit/f66ff91e0dad78d4d6346a75ded4b751)
- [ActivityWatch Accessibility PR](https://github.com/ActivityWatch/aw-watcher-window/pull/41)
- [Requesting macOS Permissions Guide](https://gannonlawlor.com/posts/macos_privacy_permissions/)

---
*Generated: 2026-01-16*
