# macOS Support Design

## Goal

Add macOS support to whisper-key-local while maintaining Windows functionality.

## Strategy

**Phase 1:** Replace Windows-only libraries with cross-platform alternatives where possible
**Phase 2:** Create platform abstraction layer for components that need different implementations
**Phase 3:** Implement macOS-specific code behind the abstraction layer

---

## Component Analysis

| Component | Current (Windows) | Phase 1 | Phase 2/3 |
|-----------|-------------------|---------|-----------|
| Audio recording | sounddevice | ✅ Already cross-platform | - |
| Whisper engine | faster-whisper | ✅ Already cross-platform | - |
| VAD | ten-vad | ✅ Already cross-platform | - |
| Config | ruamel.yaml | ✅ Already cross-platform | - |
| System tray | pystray | ✅ Already cross-platform | - |
| Clipboard read/write | pyperclip | ✅ Already cross-platform | - |
| Audio feedback | winsound | ❌ | playsound3 |
| Key simulation | pyautogui | ❌ | Platform abstraction (Quartz CGEvent) |
| Hotkey detection | global-hotkeys | ❌ | Platform abstraction (QuickMacHotKey) |
| Instance lock | win32event | ❌ | Platform abstraction (fcntl) |
| Console hide | win32console | ❌ | Skip on macOS (not needed) |
| PortAudio DLL | bundled DLL (for WASAPI) | ❌ | Skip on macOS (no WASAPI, sounddevice wheel suffices) |
| Window detection | win32gui | ❌ | Remove (dead code, not used) |

---

## Phase 1: Cross-Platform Foundations

### 1.1 Audio Feedback

**Current:** `winsound.PlaySound()` (Windows-only)

**Recommendation:** Use `playsound3` - actively maintained fork with macOS fixes.

```python
from playsound3 import playsound

def play_sound(path):
    playsound(path, block=False)
```

**Files affected:** `audio_feedback.py`

### 1.2 Verify Cross-Platform Components

Test these components on macOS to confirm they work:
- [ ] `sounddevice` audio recording
- [ ] `faster-whisper` transcription
- [ ] `ten-vad` voice activity detection
- [ ] `pystray` system tray
- [ ] `pyperclip` clipboard

---

## Phase 2: Platform Abstraction Layer

### 2.1 Folder Structure

```
src/whisper_key/
├── platform/
│   ├── __init__.py          # Platform detection, routes to correct folder
│   ├── macos/
│   │   ├── __init__.py
│   │   ├── audio.py         # playsound3
│   │   ├── keyboard.py      # Quartz CGEvent
│   │   ├── hotkeys.py       # QuickMacHotKey
│   │   └── instance_lock.py # fcntl
│   └── windows/
│       ├── __init__.py
│       ├── audio.py         # winsound
│       ├── keyboard.py      # pyautogui
│       ├── hotkeys.py       # global-hotkeys
│       ├── instance_lock.py # win32event
│       └── console.py       # win32console (Windows-only)
├── audio_feedback.py        # Uses platform.audio
├── clipboard_manager.py     # Uses platform.keyboard
├── hotkey_listener.py       # Uses platform.hotkeys
└── instance_manager.py      # Uses platform.instance_lock
```

### 2.2 Platform Router

```python
# platform/__init__.py
import platform as _platform

PLATFORM = 'macos' if _platform.system() == 'Darwin' else 'windows'
IS_MACOS = PLATFORM == 'macos'
IS_WINDOWS = PLATFORM == 'windows'

# Explicit imports from correct platform subfolder
if IS_MACOS:
    from .macos import audio, keyboard, hotkeys, instance_lock
else:
    from .windows import audio, keyboard, hotkeys, instance_lock
```

### 2.3 Usage in Components

```python
# audio_feedback.py
from .platform import audio

class AudioFeedback:
    def play_start_sound(self):
        audio.play_sound(self.start_sound_path)
```

```python
# clipboard_manager.py
from .platform import keyboard

class ClipboardManager:
    def auto_paste(self):
        keyboard.send_hotkey('cmd', 'v')  # or 'ctrl', 'v' on Windows
```

### 2.4 Interface Contracts

Each platform folder must have modules with matching interfaces:

**audio.py:**
```python
def play_sound(path: str, blocking: bool = False) -> None: ...
```

**keyboard.py:**
```python
def send_hotkey(*keys: str) -> None:
    """Example: send_hotkey('cmd', 'v')"""

def send_key(key: str) -> None:
    """Example: send_key('enter')"""
```

**hotkeys.py:**
```python
class HotkeyListener:
    def register(self, hotkey: str, callback: Callable) -> None: ...
    def start(self) -> None: ...
    def stop(self) -> None: ...
```

**instance_lock.py:**
```python
class InstanceLock:
    def acquire(self) -> bool: ...
    def release(self) -> None: ...
```

---

## Phase 3: macOS Implementations

### 3.1 Key Simulation (Quartz CGEvent)

**Dependency:** `pyobjc-framework-Quartz`

```python
# platform/macos/keyboard.py
from Quartz import CGEventCreateKeyboardEvent, CGEventPost, kCGSessionEventTap
import time

KEY_CODES = {
    'a': 0, 'b': 11, 'c': 8, 'd': 2, 'e': 14, 'f': 3, 'g': 5, 'h': 4,
    'i': 34, 'j': 38, 'k': 40, 'l': 37, 'm': 46, 'n': 45, 'o': 31,
    'p': 35, 'q': 12, 'r': 15, 's': 1, 't': 17, 'u': 32, 'v': 9,
    'w': 13, 'x': 7, 'y': 16, 'z': 6,
    'return': 36, 'enter': 36, 'space': 49, 'tab': 48, 'escape': 53,
}

MODIFIERS = {
    'cmd': (1 << 20),
    'command': (1 << 20),
    'ctrl': (1 << 18),
    'control': (1 << 18),
    'shift': (1 << 17),
    'alt': (1 << 19),
    'option': (1 << 19),
}

def send_hotkey(*keys):
    if not keys:
        return
    actual_key = keys[-1].lower()
    modifiers = [k.lower() for k in keys[:-1]]

    key_code = KEY_CODES.get(actual_key)
    if key_code is None:
        raise ValueError(f"Unknown key: {actual_key}")

    modifier_flags = 0
    for mod in modifiers:
        if mod in MODIFIERS:
            modifier_flags |= MODIFIERS[mod]

    # Key down
    event = CGEventCreateKeyboardEvent(None, key_code, True)
    event.flags = modifier_flags
    CGEventPost(kCGSessionEventTap, event)

    time.sleep(0.01)

    # Key up
    event = CGEventCreateKeyboardEvent(None, key_code, False)
    event.flags = modifier_flags
    CGEventPost(kCGSessionEventTap, event)

def send_key(key):
    send_hotkey(key)
```

### 3.2 Hotkey Detection (QuickMacHotKey)

**Dependency:** `quickmachotkey`

```python
# platform/macos/hotkeys.py
from quickmachotkey import quickHotKey, mask
from quickmachotkey.constants import kVK_Space, controlKey, shiftKey
from AppKit import NSApplication
import threading

class HotkeyListener:
    def __init__(self):
        self._hotkeys = {}
        self._thread = None

    def register(self, hotkey: str, callback):
        # Parse hotkey string like "ctrl+shift+space"
        # Map to QuickMacHotKey format
        self._hotkeys[hotkey] = callback

    def start(self):
        # Run NSApplication event loop in background thread
        self._thread = threading.Thread(target=self._run_loop, daemon=True)
        self._thread.start()

    def _run_loop(self):
        # Register hotkeys and start event loop
        app = NSApplication.sharedApplication()
        app.run()

    def stop(self):
        # Stop the event loop
        NSApplication.sharedApplication().terminate_(None)
```

**Note:** QuickMacHotKey requires NSApplication event loop. May need architectural adjustments.

### 3.3 Instance Lock (fcntl)

```python
# platform/macos/instance_lock.py
import fcntl
import os
from pathlib import Path

class InstanceLock:
    def __init__(self, name: str = "whisper-key"):
        self._lock_path = Path.home() / f".{name}.lock"
        self._lock_file = None

    def acquire(self) -> bool:
        try:
            self._lock_file = open(self._lock_path, 'w')
            fcntl.flock(self._lock_file.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
            self._lock_file.write(str(os.getpid()))
            self._lock_file.flush()
            return True
        except (IOError, OSError):
            return False

    def release(self):
        if self._lock_file:
            fcntl.flock(self._lock_file.fileno(), fcntl.LOCK_UN)
            self._lock_file.close()
            self._lock_path.unlink(missing_ok=True)
```

### 3.4 Audio Feedback

```python
# platform/macos/audio.py
from playsound3 import playsound as _playsound
import threading

def play_sound(path: str, blocking: bool = False):
    if blocking:
        _playsound(path)
    else:
        threading.Thread(target=_playsound, args=(path,), daemon=True).start()
```

---

## Configuration Changes

### Default Hotkeys

| Setting | Windows | macOS |
|---------|---------|-------|
| `paste_hotkey` | `ctrl+v` | `cmd+v` |
| `record_hotkey` | `ctrl+shift+space` | `cmd+shift+space` |
| `cancel_hotkey` | `escape` | `escape` |

**Approach:** Platform-aware defaults in `config_manager.py`:

```python
def _get_platform_defaults(self):
    if platform.system() == "Darwin":
        return {
            'paste_hotkey': 'cmd+v',
            'record_hotkey': 'cmd+shift+space',
        }
    return {
        'paste_hotkey': 'ctrl+v',
        'record_hotkey': 'ctrl+shift+space',
    }
```

---

## Dependencies

### pyproject.toml Updates

```toml
dependencies = [
    # Existing cross-platform
    "faster-whisper>=1.2.1",
    "sounddevice>=0.4.6",
    "pyperclip>=1.8.2",
    "ruamel.yaml>=0.18.14",
    "pystray>=0.19.5",
    "Pillow>=10.0.0",

    # Windows-only
    "global-hotkeys>=0.1.7; platform_system=='Windows'",
    "pywin32>=306; platform_system=='Windows'",
    "pyautogui>=0.9.54; platform_system=='Windows'",

    # macOS-only
    "quickmachotkey>=0.1.0; platform_system=='Darwin'",
    "pyobjc-framework-Quartz>=10.0; platform_system=='Darwin'",
    "pyobjc-framework-ApplicationServices>=10.0; platform_system=='Darwin'",
    "playsound3>=2.0; platform_system=='Darwin'",
]
```

---

## Implementation Order

### Sprint 1: Foundation
1. Create `platform/` folder with `__init__.py`, `macos/`, `windows/` subfolders
2. Move Windows code into `platform/windows/` modules (no behavior change)
3. Update existing components to import from `platform`
4. Test Windows still works

### Sprint 2: Audio & Instance Lock
5. Implement `platform/macos/audio.py` (playsound3)
6. Implement `platform/macos/instance_lock.py` (fcntl)
7. Update `audio_feedback.py` and `instance_manager.py` to use platform imports
8. Test on macOS

### Sprint 3: Keyboard Simulation
9. Implement `platform/macos/keyboard.py` (Quartz CGEvent)
10. Implement `platform/windows/keyboard.py` (pyautogui wrapper)
11. Update `clipboard_manager.py` to use `platform.keyboard`
12. Test paste workflow on both platforms

### Sprint 4: Hotkey Detection
13. Implement `platform/macos/hotkeys.py` (QuickMacHotKey)
14. Implement `platform/windows/hotkeys.py` (global-hotkeys wrapper)
15. Update `hotkey_listener.py` to use `platform.hotkeys`
16. Handle NSApplication event loop integration
17. Test hotkey detection on both platforms

### Sprint 5: Polish
18. Platform-aware config defaults
19. Skip console manager on macOS
20. Update documentation
21. End-to-end testing on both platforms

---

## Risks & Mitigations

| Risk | Impact | Mitigation |
|------|--------|------------|
| QuickMacHotKey requires NSApplication event loop | High | May need to restructure main loop, or run in separate process |
| Accessibility permissions on macOS | Medium | Clear user messaging, auto-open System Preferences |
| playsound3 reliability | Low | Fall back to PyObjC NSSound if issues |
| Different hotkey naming (Cmd vs Ctrl) | Low | Config migration, clear documentation |

---

## Testing Strategy

### Unit Tests
- Each platform module tested in isolation
- Mock platform detection for cross-platform test runs

### Integration Tests
- Full workflow on Windows VM
- Full workflow on macOS VM
- Hotkey detection + transcription + paste cycle

### Manual Testing
- Various macOS apps (Notes, Terminal, VS Code, browser)
- Accessibility permission flow
- System tray behavior

---

## Open Questions

1. **NSApplication event loop:** Does pystray already run one? Can we share it with QuickMacHotKey?
2. **Audio host defaults:** Should macOS default to CoreAudio explicitly?

---

*Created: 2026-02-02*
