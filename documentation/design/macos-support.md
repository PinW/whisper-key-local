# macOS Support Design

## Goal

Add macOS support to whisper-key-local while maintaining Windows functionality.

## Progress

- [x] ~~**Phase 1:** Replace Windows-only libraries with cross-platform alternatives where possible~~
- [x] ~~**Phase 2:** Create platform abstraction layer for components that need different implementations~~
- [ ] **Phase 3:** Implement macOS-specific code behind the abstraction layer
  - [x] ~~**3.1:** Audio feedback (`platform/macos/audio.py` - playsound3)~~ *(already done)*
  - [x] ~~**3.2:** App data path (`utils.py` - use `~/Library/Application Support/`)~~
  - [ ] **3.3:** Instance lock (`platform/macos/instance_lock.py` - fcntl)
  - [ ] **3.4:** Key simulation (`platform/macos/keyboard.py` - Quartz CGEvent)
  - [ ] **3.5:** Hotkey detection (`platform/macos/hotkeys.py` - QuickMacHotKey) ⚠️ highest risk
  - [ ] **3.6:** Platform-aware config defaults (cmd vs ctrl)
  - [ ] **3.7:** Skip console manager on macOS
- [ ] **Phase 4:** Update `pyproject.toml` with platform markers for conditional dependencies

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
| Audio feedback | winsound | ✅ playsound3 | - |
| Key simulation | pyautogui | ❌ | Platform abstraction (Quartz CGEvent) |
| Hotkey detection | global-hotkeys | ❌ | Platform abstraction (QuickMacHotKey) |
| Instance lock | win32event | ❌ | Platform abstraction (fcntl) |
| Console hide | win32console | ❌ | Skip on macOS (not needed) |
| PortAudio DLL | bundled DLL (for WASAPI) | ❌ | Skip on macOS (no WASAPI, sounddevice wheel suffices) |
| Window detection | win32gui | ❌ | Remove (dead code, not used) |
| App data path | `%APPDATA%` env var | ❌ | `~/Library/Application Support/` on macOS |

---

## Phase 1: Cross-Platform Foundations *(Complete)*

Replaced `winsound` with `playsound3` for audio feedback.

### Verify Cross-Platform Components (on macOS)

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

---

## Configuration Changes

### Default Hotkeys

| Setting | Windows | macOS |
|---------|---------|-------|
| `paste_hotkey` | `ctrl+v` | `cmd+v` |
| `record_hotkey` | `ctrl+shift+space` | `cmd+shift+space` |
| `cancel_hotkey` | `escape` | `escape` |

### Implementation Requirements

**1. Platform detection global** - Use existing `IS_MACOS` from `platform/__init__.py`:
```python
from whisper_key.platform import IS_MACOS
```

**2. Update `config.defaults.yaml`** - Current defaults file only has Windows values. Options:
- **Option A:** Keep single defaults file, override in code (simpler)
- **Option B:** Have `config.defaults.yaml` + `config.defaults.macos.yaml` (more explicit)

**3. Modify `config_manager.py`** - Apply platform-specific defaults:
```python
from .platform import IS_MACOS

def _get_default_value(self, key):
    # Platform-specific overrides
    if IS_MACOS:
        macos_defaults = {
            'paste_hotkey': 'cmd+v',
            'record_hotkey': 'cmd+shift+space',
        }
        if key in macos_defaults:
            return macos_defaults[key]
    # Fall back to config.defaults.yaml
    return self._defaults.get(key)
```

**4. Config file format stays the same** - Users can still override with `ctrl` or `cmd` as they prefer. The platform detection only affects what happens when no config file exists yet.

---

## Phase 4: Platform Markers in pyproject.toml

### How Platform Markers Work

Python's PEP 508 allows conditional dependencies using **environment markers**. The syntax uses a semicolon followed by a condition:

```toml
"pywin32>=306; sys_platform=='win32'"    # Only on Windows
"pyobjc>=10.0; sys_platform=='darwin'"   # Only on macOS
```

When a user runs `pip install whisper-key` or `pipx install whisper-key`:
- Windows users get `pywin32`, `global-hotkeys`, `pyautogui`
- macOS users get `pyobjc-framework-Quartz`, `quickmachotkey`
- Neither platform downloads the other's dependencies

### Common Markers

| Marker | Windows | macOS | Linux |
|--------|---------|-------|-------|
| `sys_platform` | `'win32'` | `'darwin'` | `'linux'` |

### Updated pyproject.toml

```toml
dependencies = [
    # Cross-platform
    "faster-whisper>=1.2.1",
    "sounddevice>=0.4.6",
    "pyperclip>=1.8.2",
    "ruamel.yaml>=0.18.14",
    "pystray>=0.19.5",
    "Pillow>=10.0.0",
    "playsound3>=2.3.0",

    # Windows-only
    "global-hotkeys>=0.1.7; sys_platform=='win32'",
    "pywin32>=306; sys_platform=='win32'",
    "pyautogui>=0.9.54; sys_platform=='win32'",

    # macOS-only
    "quickmachotkey>=0.1.0; sys_platform=='darwin'",
    "pyobjc-framework-Quartz>=10.0; sys_platform=='darwin'",
    "pyobjc-framework-ApplicationServices>=10.0; sys_platform=='darwin'",
]
```

### Implementation Notes

1. **Both pip and pipx support markers** - They evaluate conditions at install time
2. **Use `sys_platform`** - More common than `platform_system` in the wild
3. **Test on both platforms** - CI should verify installation works on Windows and macOS
4. **Real-world examples** - PyInstaller, playsound3, and many others use this pattern

---

## Implementation Order

### Sprint 1: Foundation
1. Create `platform/` folder with `__init__.py`, `macos/`, `windows/` subfolders
2. Move Windows code into `platform/windows/` modules (no behavior change)
3. Update existing components to import from `platform`
4. Test Windows still works

### Sprint 2: Instance Lock
5. ~~Implement `platform/macos/audio.py` (playsound3)~~ *(done)*
6. Implement `platform/macos/instance_lock.py` (fcntl)
7. Update `instance_manager.py` to use platform imports
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
| Different hotkey naming (Cmd vs Ctrl) | Low | Platform-aware defaults, users can override |

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

---

## Implementation Notes

### Hotkey String Parsing

Current code uses string format like `"ctrl+shift+space"` parsed by `utils.parse_hotkey()`.

QuickMacHotKey uses a different format - virtual key codes and modifier masks:
```python
@quickHotKey(virtualKey=kVK_Space, modifierMask=mask(controlKey, shiftKey))
```

**Need to build:** A translation layer that converts config strings → QuickMacHotKey format:
- `"ctrl"` → `controlKey`
- `"shift"` → `shiftKey`
- `"cmd"` → `cmdKey`
- `"space"` → `kVK_Space` (49)
- etc.

Check `quickmachotkey.constants` for available key codes.

### NSApplication Event Loop Challenge

QuickMacHotKey needs an NSApplication event loop to receive hotkey events:
```python
from AppKit import NSApplication
NSApplication.sharedApplication().run()  # Blocks forever, processing events
```

**The problem:** `.run()` blocks the thread. But whisper-key already has its own main loop (pystray system tray, state management, etc.).

**Research findings:**

1. **pystray DOES use NSApplication on macOS** - Good news, they can share!
   > "The system tray icon implementation for OSX will fail unless called from the main thread, and it also requires the application runloop to be running."

2. **Both must run on main thread** - This is a hard constraint on macOS (unlike Linux/Windows where pystray can run detached).

3. **Recommended approach - shared NSApplication:**
   ```python
   from AppKit import NSApplication
   from quickmachotkey import quickHotKey
   import pystray

   # Create shared NSApplication FIRST
   nsapp = NSApplication.sharedApplication()

   # Register hotkeys (decorator runs at definition time)
   @quickHotKey(virtualKey=kVK_Space, modifierMask=mask(controlKey, shiftKey))
   def on_record():
       # handle hotkey
       pass

   # pystray uses the same NSApplication
   icon = pystray.Icon("whisper-key", image, menu=menu)
   icon.run_detached(darwin_nsapplication=nsapp)
   ```

4. **Known issues:**
   - GIL problems reported on M2 Macs (pystray issue #138)
   - May need queue-based communication between components
   - Careful exception handling required

**This is still the highest-risk part** - but now we have a concrete approach to try. Tackle in Sprint 4.

---

*Created: 2026-02-02*
