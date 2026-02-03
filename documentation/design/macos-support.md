# macOS Support Design

## Goal

Add macOS support to whisper-key-local while maintaining Windows functionality.

## Progress

- [x] ~~**Phase 1:** Replace Windows-only libraries with cross-platform alternatives where possible~~
- [x] ~~**Phase 2:** Create platform abstraction layer for components that need different implementations~~
- [ ] **Phase 3:** Implement macOS-specific code behind the abstraction layer
  - [x] ~~**3.1:** Audio feedback (`platform/macos/audio.py` - playsound3)~~ *(already done)*
  - [x] ~~**3.2:** App data path (`utils.py` - use `~/Library/Application Support/`)~~
  - [x] ~~**3.3:** Instance lock (`platform/macos/instance_lock.py` - fcntl)~~
  - [ ] **3.4:** Key simulation (`platform/macos/keyboard.py` - Quartz CGEvent)
  - [ ] **3.5:** Hotkey detection (`platform/macos/hotkeys.py` - QuickMacHotKey) ⚠️ highest risk
  - [ ] **3.6:** Platform-aware config defaults (cmd vs ctrl)
  - [ ] **3.7:** Skip console manager on macOS
- [x] ~~**Phase 4:** Update `pyproject.toml` with platform markers for conditional dependencies~~
- [ ] **Phase 5:** Resolve macOS main thread / event loop architecture
  - [x] ~~**5.1:** Refactor to use `run_detached()` on both platforms~~
  - [x] ~~**5.2:** Add NSApplication event loop on main thread for macOS~~
  - [ ] **5.3:** Fix Ctrl+C shutdown (signal not waking NSApplication)
  - [ ] **5.4:** Hide Dock icon (setActivationPolicy)
  - [ ] **5.5:** Suppress secure coding warning (optional)

---

## Phase 5: macOS Main Thread Architecture

### The Problem

On macOS, both pystray (system tray) and QuickMacHotKey require the **NSApplication event loop running on the main thread**. This is a hard constraint of Apple's Cocoa framework.

Current Windows architecture:
```
Main thread:     while shutdown_event.wait() → handles signals
Daemon thread:   pystray icon.run() → handles tray
Other threads:   hotkeys, audio, etc.
```

This doesn't work on macOS because:
1. `icon.run()` uses NSApplication internally
2. NSApplication **must** run on main thread
3. Running it in a daemon thread causes: no tray icon, Dock icon appears, app hangs, Ctrl+C doesn't work

### Research Findings

**pystray documentation states:**
> "The system tray icon implementation for OSX will fail unless called from the main thread, and it also requires the application runloop to be running."

**Key constraints:**
- pystray needs NSApplication on main thread
- QuickMacHotKey needs NSApplication on main thread
- Both can share the same NSApplication instance
- `nsapp.run()` blocks forever (it's an event loop)

**Known issues:**
- GIL problems reported on M1/M2/M3 Macs (pystray issue #138)
- May need queue-based communication between components

### Preferred Solution: Use `run_detached()` on Both Platforms

The cleanest approach is to use `icon.run_detached()` on both platforms, eliminating the daemon thread:

```python
# system_tray.py - start() method
icon.run_detached()  # Non-blocking on both platforms

# main.py - after all setup
if IS_MACOS:
    from AppKit import NSApplication
    nsapp = NSApplication.sharedApplication()
    nsapp.run()  # macOS: main thread runs event loop
else:
    while not shutdown_event.wait(timeout=0.1):
        pass  # Windows: main thread waits for shutdown
```

**Why this works:**
- `run_detached()` on Windows: Internally spawns a thread to handle win32 message pump
- `run_detached()` on macOS: Sets up tray, but needs `nsapp.run()` to process events
- No manual daemon thread needed on either platform
- Cleaner than current approach

**Implementation steps:**
1. Remove daemon thread from `system_tray.py`
2. Use `icon.run_detached()` instead of `icon.run()`
3. Add platform-specific main loop in `main.py`
4. On macOS, run `nsapp.run()` after all setup complete

### Additional macOS Considerations

**Dock icon:** By default, any NSApplication shows in Dock. To hide:
- Set `LSUIElement=True` in Info.plist (for bundled apps)
- Or programmatically: `app.setActivationPolicy_(NSApplicationActivationPolicyAccessory)`

**Signal handling:** With NSApplication owning main thread, need to ensure Ctrl+C still works for graceful shutdown.

### Implementation Status (2026-02-03)

**Implemented:**
- `run_detached()` approach working on both Windows and macOS
- System tray appears in menu bar
- Tray menu works (View Log, Advanced Settings, audio device selection)

**Issues Found:**
1. **Ctrl+C doesn't quit immediately** - Signal received (`^C` appears) but NSApplication doesn't wake until a tray action occurs. Need to post a dummy event to wake the run loop.
2. **Python rocket icon in Dock** - Need `setActivationPolicy_(NSApplicationActivationPolicyAccessory)`
3. **Secure coding warning** - Cosmetic warning on startup about `NSApplicationDelegate.applicationSupportsSecureRestorableState`

### Remaining Questions

1. ~~How do hotkey callbacks interact with the NSApplication event loop?~~ *(To be tested with QuickMacHotKey)*
2. ~~Queue-based communication for tray updates from background threads?~~ *(Working - tray updates from callbacks work)*

### References

- [pystray FAQ](https://pystray.readthedocs.io/en/latest/faq.html)
- [pystray Issue #138 - GIL on M2](https://github.com/moses-palmer/pystray/issues/138)
- [QuickMacHotKey](https://github.com/glyph/QuickMacHotKey)
- [RUMPS](https://github.com/jaredks/rumps)

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

- [ ] `sounddevice` audio recording *(requires hotkeys to test)*
- [ ] `faster-whisper` transcription *(requires hotkeys to test)*
- [ ] `ten-vad` voice activity detection *(requires hotkeys to test)*
- [x] `pystray` system tray *(working with run_detached + NSApplication)*
- [ ] `pyperclip` clipboard *(requires hotkeys to test)*

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
