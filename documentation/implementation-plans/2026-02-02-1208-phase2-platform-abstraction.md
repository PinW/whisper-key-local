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

## Implementation Plan

### Step 1: Create platform folder structure
- [ ] Create `src/whisper_key/platform/__init__.py`
- [ ] Create `src/whisper_key/platform/windows/__init__.py`
- [ ] Create `src/whisper_key/platform/macos/__init__.py`

### Step 2: Create platform router
- [ ] Implement platform detection in `platform/__init__.py`
- [ ] Export `IS_MACOS`, `IS_WINDOWS` constants

### Step 3: Move instance lock to platform layer
- [ ] Create `platform/windows/instance_lock.py` (extract from instance_manager.py)
- [ ] Create `platform/macos/instance_lock.py` (fcntl implementation)
- [ ] Update `instance_manager.py` to import from platform

### Step 4: Move console manager to platform layer
- [ ] Create `platform/windows/console.py` (extract from console_manager.py)
- [ ] Create `platform/macos/console.py` (no-op stub)
- [ ] Update `console_manager.py` to import from platform

### Step 5: Move keyboard simulation to platform layer
- [ ] Create `platform/windows/keyboard.py` (pyautogui wrapper)
- [ ] Create `platform/macos/keyboard.py` (Quartz CGEvent - placeholder)
- [ ] Update `clipboard_manager.py` to import from platform

### Step 6: Move hotkey detection to platform layer
- [ ] Create `platform/windows/hotkeys.py` (global-hotkeys wrapper)
- [ ] Create `platform/macos/hotkeys.py` (QuickMacHotKey - placeholder)
- [ ] Update `hotkey_listener.py` to import from platform

### Step 7: Update dependencies
- [ ] Add platform markers to pyproject.toml for Windows-only deps
- [ ] Add macOS dependencies with platform markers

### Step 8: Test Windows still works
- [ ] Run `/test-from-wsl`
- [ ] Manual test: full recording workflow

## Implementation Details

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

### macOS Stubs (Phase 2)

macOS modules will have minimal implementations that raise `NotImplementedError` or log warnings. Full implementations come in Phase 3.

```python
# platform/macos/keyboard.py
def send_hotkey(*keys):
    raise NotImplementedError("macOS keyboard not implemented yet")

def send_key(key):
    raise NotImplementedError("macOS keyboard not implemented yet")
```

### Instance Lock (fcntl) - Full Implementation

```python
# platform/macos/instance_lock.py
import fcntl
import os
from pathlib import Path

_lock_file = None

def acquire_lock(app_name: str):
    global _lock_file
    lock_path = Path.home() / f".{app_name}.lock"
    try:
        _lock_file = open(lock_path, 'w')
        fcntl.flock(_lock_file.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
        _lock_file.write(str(os.getpid()))
        _lock_file.flush()
        return _lock_file
    except (IOError, OSError):
        return None

def release_lock(handle):
    global _lock_file
    if handle:
        fcntl.flock(handle.fileno(), fcntl.LOCK_UN)
        handle.close()
    _lock_file = None
```

### Console (macOS no-op)

```python
# platform/macos/console.py
class ConsoleManager:
    def __init__(self, config, is_executable_mode=False):
        pass  # No console management needed on macOS

    def show_console(self):
        return True

    def hide_console(self):
        return True
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
| `platform/macos/__init__.py` | macOS exports |
| `platform/macos/instance_lock.py` | fcntl file lock |
| `platform/macos/console.py` | No-op stub |
| `platform/macos/keyboard.py` | Placeholder (NotImplementedError) |
| `platform/macos/hotkeys.py` | Placeholder (NotImplementedError) |

## Files to Modify

| File | Changes |
|------|---------|
| `instance_manager.py` | Import from platform.instance_lock |
| `console_manager.py` | Import from platform.console |
| `clipboard_manager.py` | Import keyboard from platform |
| `hotkey_listener.py` | Import hotkeys from platform |
| `pyproject.toml` | Add platform markers to dependencies |

## Success Criteria

- [ ] Windows app starts without import errors
- [ ] Recording workflow works end-to-end on Windows
- [ ] All Windows-specific imports are in platform/windows/
- [ ] Platform detection correctly identifies Windows vs macOS
- [ ] Clean separation: main components don't import win32* or pyautogui directly
