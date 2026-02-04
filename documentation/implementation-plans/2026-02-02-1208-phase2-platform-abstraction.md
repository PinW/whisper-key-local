# Phase 2: Platform Abstraction Layer

As a *developer* I want **a platform abstraction layer** so Windows-specific code is isolated and macOS implementations can be added alongside it.

## Current State

Four components use Windows-only libraries:

| Component | Windows Library | macOS Alternative |
|-----------|-----------------|-------------------|
| `instance_manager.py` | win32event, win32api | fcntl |
| `console_manager.py` | win32console, win32gui | Skip on macOS |
| `hotkey_listener.py` | global-hotkeys | QuickMacHotKey |
| `clipboard_manager.py` | pyautogui | Quartz CGEvent |

**Note:** Audio feedback is handled in Phase 1 with playsound3 (cross-platform, no abstraction needed).

**Phase 2 scope:** Create the abstraction structure and move Windows code. macOS modules are empty placeholders - implementations come in Phase 3.

## Implementation Plan

### Step 1: Create platform folder structure
- [x] Create `src/whisper_key/platform/__init__.py`
- [x] Create `src/whisper_key/platform/windows/__init__.py`
- [x] Create `src/whisper_key/platform/macos/__init__.py`

### Step 2: Create platform router
- [x] Implement platform detection in `platform/__init__.py`
- [x] Export `IS_MACOS`, `IS_WINDOWS` constants

### Step 3: Move instance lock to platform layer
- [x] Create `platform/windows/instance_lock.py` (extract from instance_manager.py)
- [x] Create `platform/macos/instance_lock.py` (empty placeholder)
- [x] Update `instance_manager.py` to import from platform

### Step 4: Move console manager to platform layer
- [x] Create `platform/windows/console.py` (extract from console_manager.py)
- [x] Create `platform/macos/console.py` (empty placeholder)
- [x] Update `console_manager.py` to import from platform

### Step 5: Move keyboard simulation to platform layer
- [x] Create `platform/windows/keyboard.py` (pyautogui wrapper)
- [x] Create `platform/macos/keyboard.py` (empty placeholder)
- [x] Update `clipboard_manager.py` to import from platform

### Step 6: Move hotkey detection to platform layer
- [x] Create `platform/windows/hotkeys.py` (global-hotkeys wrapper)
- [x] Create `platform/macos/hotkeys.py` (empty placeholder)
- [x] Update `hotkey_listener.py` to import from platform

### Step 7: Test Windows still works
- [x] Run `/test-from-wsl`
- [x] Manual test: full recording workflow
- [x] PyInstaller build successful

## Implementation Details

### Import Structure

**Key principle:** Platform detection happens ONCE in `platform/__init__.py`. All other components simply import from `platform` without any platform-checking logic.

```
┌─────────────────────────────────────────────────────────────┐
│  platform/__init__.py (THE ONLY FILE WITH PLATFORM LOGIC)  │
│                                                             │
│  if IS_MACOS:                                               │
│      from .macos import instance_lock, console, ...        │
│  else:                                                      │
│      from .windows import instance_lock, console, ...      │
└─────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────┐
│  Components (NO platform detection, just normal imports)   │
│                                                             │
│  instance_manager.py:   from .platform import instance_lock │
│  console_manager.py:    from .platform import console       │
│  clipboard_manager.py:  from .platform import keyboard      │
│  hotkey_listener.py:    from .platform import hotkeys       │
└─────────────────────────────────────────────────────────────┘
```

### Platform Router

```python
# platform/__init__.py
import platform as _platform

PLATFORM = 'macos' if _platform.system() == 'Darwin' else 'windows'
IS_MACOS = PLATFORM == 'macos'
IS_WINDOWS = PLATFORM == 'windows'

if IS_MACOS:
    from .macos import instance_lock, console, keyboard, hotkeys
else:
    from .windows import instance_lock, console, keyboard, hotkeys
```

### Usage in Components

Components do NOT check platform - they just import and use:

```python
# instance_manager.py
from .platform import instance_lock

class InstanceManager:
    def acquire(self):
        return instance_lock.acquire_lock("whisper-key")
```

```python
# clipboard_manager.py
from .platform import keyboard

class ClipboardManager:
    def auto_paste(self):
        keyboard.send_hotkey('ctrl', 'v')  # Platform module handles correct key
```

### Interface Contracts

**instance_lock.py:**
```python
def acquire_lock(app_name: str) -> object | None:
    """Returns lock handle if acquired, None if another instance exists."""

def release_lock(handle: object) -> None:
    """Release the instance lock."""
```

**console.py:**
```python
class ConsoleManager:
    def __init__(self, config: dict, is_executable_mode: bool): ...
    def show_console(self) -> bool: ...
    def hide_console(self) -> bool: ...
```

**keyboard.py:**
```python
def send_hotkey(*keys: str) -> None:
    """Send key combination. Example: send_hotkey('ctrl', 'v')"""

def send_key(key: str) -> None:
    """Send single key. Example: send_key('enter')"""
```

**hotkeys.py:**
```python
class HotkeyManager:
    def register(self, hotkey: str, callback, release_callback=None) -> None: ...
    def start(self) -> None: ...
    def stop(self) -> None: ...
```

## Files to Create

| File | Purpose |
|------|---------|
| `platform/__init__.py` | Platform detection and routing |
| `platform/windows/__init__.py` | Windows exports |
| `platform/windows/instance_lock.py` | Win32 mutex lock |
| `platform/windows/console.py` | Win32 console management |
| `platform/windows/keyboard.py` | pyautogui wrapper |
| `platform/windows/hotkeys.py` | global-hotkeys wrapper |
| `platform/macos/__init__.py` | macOS exports (empty placeholders) |
| `platform/macos/instance_lock.py` | Empty placeholder (Phase 3) |
| `platform/macos/console.py` | Empty placeholder (Phase 3) |
| `platform/macos/keyboard.py` | Empty placeholder (Phase 3) |
| `platform/macos/hotkeys.py` | Empty placeholder (Phase 3) |

## Files to Modify

| File | Changes |
|------|---------|
| `instance_manager.py` | Import from platform.instance_lock |
| `console_manager.py` | Import from platform.console |
| `clipboard_manager.py` | Import keyboard from platform |
| `hotkey_listener.py` | Import hotkeys from platform |

## Success Criteria

- [x] Windows app starts without import errors
- [x] Recording workflow works end-to-end on Windows
- [x] All Windows-specific imports are in platform/windows/
- [x] Platform detection correctly identifies Windows vs macOS
- [x] Clean separation: main components don't import win32* or pyautogui directly
