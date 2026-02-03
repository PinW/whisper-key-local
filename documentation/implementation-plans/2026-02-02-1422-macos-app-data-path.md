# macOS Paths and File Operations

As a *user* I want **config and log files stored in the correct location on macOS** and **tray menu file operations to work** so the app follows platform conventions.

## Current State

`utils.py:get_user_app_data_path()` uses Windows-only `%APPDATA%` environment variable:

```python
def get_user_app_data_path():
    appdata = os.getenv('APPDATA')  # None on macOS!
    whisperkey_dir = os.path.join(appdata, 'whisperkey')
    os.makedirs(whisperkey_dir, exist_ok=True)
    return whisperkey_dir
```

On macOS, `APPDATA` is undefined → crash on startup before anything else runs.

`system_tray.py` uses `os.startfile()` which is Windows-only:

```python
os.startfile(log_path)    # Windows-only!
os.startfile(config_path) # Windows-only!
```

On macOS this raises `AttributeError: module 'os' has no attribute 'startfile'`.

## Platform Conventions

| Platform | Standard Location | Example |
|----------|------------------|---------|
| Windows | `%APPDATA%\whisperkey` | `C:\Users\X\AppData\Roaming\whisperkey` |
| macOS | `~/Library/Application Support/whisperkey` | `/Users/X/Library/Application Support/whisperkey` |

## Implementation Plan

### Step 1: Create platform/windows/paths.py
- [x] Create `platform/windows/paths.py`
- [x] Implement `get_app_data_path()` using `%APPDATA%`
- [x] Implement `open_file()` using `os.startfile()`

### Step 2: Create platform/macos/paths.py
- [x] Create `platform/macos/paths.py`
- [x] Implement `get_app_data_path()` using `~/Library/Application Support/`
- [x] Implement `open_file()` using `subprocess.run(['open', path])`

### Step 3: Update platform routers
- [x] Add `paths` import to `platform/windows/__init__.py`
- [x] Add `paths` import to `platform/macos/__init__.py`
- [x] Add `paths` import to `platform/__init__.py`

### Step 4: Update utils.py
- [x] Import `paths` from `.platform`
- [x] Simplify `get_user_app_data_path()` to use `paths.get_app_data_path()`
- [x] Add `open_file()` wrapper that calls `paths.open_file()`

### Step 5: Update system_tray.py
- [x] Replace `os.startfile()` with `utils.open_file()`

### Step 6: Test on macOS
- [x] **Manual test:** Run app, verify config created in correct location
- [x] Verify log file created in correct location
- [x] Verify "View Log" and "Advanced Settings" menu items work

## Implementation Details

### platform/windows/paths.py

```python
import os
from pathlib import Path

def get_app_data_path():
    return Path(os.getenv('APPDATA')) / 'whisperkey'

def open_file(path):
    os.startfile(path)
```

### platform/macos/paths.py

```python
import subprocess
from pathlib import Path

def get_app_data_path():
    return Path.home() / 'Library' / 'Application Support' / 'whisperkey'

def open_file(path):
    subprocess.run(['open', str(path)])
```

### platform/__init__.py (updated)

```python
if IS_MACOS:
    from .macos import instance_lock, console, keyboard, hotkeys, paths
else:
    from .windows import instance_lock, console, keyboard, hotkeys, paths
```

### utils.py (updated)

```python
from .platform import paths

def get_user_app_data_path():
    whisperkey_dir = paths.get_app_data_path()
    whisperkey_dir.mkdir(parents=True, exist_ok=True)
    return str(whisperkey_dir)

def open_file(path):
    paths.open_file(path)
```

### system_tray.py (updated)

```python
from .utils import open_file

def _view_log_file(self, icon=None, item=None):
    log_path = self.config_manager.get_log_file_path()
    open_file(log_path)

def _open_config_file(self, icon=None, item=None):
    config_path = self.config_manager.user_settings_path
    open_file(config_path)
```

## Files to Create

| File | Purpose |
|------|---------|
| `platform/windows/paths.py` | Windows app data path |
| `platform/macos/paths.py` | macOS app data path |

## Files to Modify

| File | Changes |
|------|---------|
| `platform/windows/__init__.py` | Add `paths` import |
| `platform/macos/__init__.py` | Add `paths` import |
| `platform/__init__.py` | Add `paths` to imports |
| `utils.py` | Add `get_user_app_data_path()` and `open_file()` using platform.paths |
| `system_tray.py` | Replace `os.startfile()` with `utils.open_file()` |

## Success Criteria

- [x] App starts on macOS without path-related crash
- [x] Config file created at `~/Library/Application Support/whisperkey/user_settings.yaml`
- [x] Log file created at `~/Library/Application Support/whisperkey/whisper-key.log`
- [x] Tray menu "View Log" opens log file on macOS
- [x] Tray menu "Advanced Settings" opens config file on macOS
- [x] Windows behavior unchanged

## Status

**COMPLETE** - All criteria verified on macOS (2026-02-03).
