# macOS App Data Path Implementation

As a *user* I want **config and log files stored in the correct location on macOS** so the app follows platform conventions.

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

## Platform Conventions

| Platform | Standard Location | Example |
|----------|------------------|---------|
| Windows | `%APPDATA%\whisperkey` | `C:\Users\X\AppData\Roaming\whisperkey` |
| macOS | `~/Library/Application Support/whisperkey` | `/Users/X/Library/Application Support/whisperkey` |

## Implementation Plan

### Step 1: Update get_user_app_data_path()
- [ ] Import platform detection from `whisper_key.platform`
- [ ] Return `~/Library/Application Support/whisperkey` on macOS
- [ ] Keep `%APPDATA%\whisperkey` on Windows
- [ ] Ensure directory is created if it doesn't exist

### Step 2: Test on macOS
- [ ] **Manual test:** Run app, verify config created in correct location
- [ ] Verify log file created in correct location

## Implementation Details

```python
# utils.py
import os
from pathlib import Path

def get_user_app_data_path():
    import platform

    if platform.system() == 'Darwin':  # macOS
        base = Path.home() / 'Library' / 'Application Support'
    else:  # Windows
        base = Path(os.getenv('APPDATA'))

    whisperkey_dir = base / 'whisperkey'
    whisperkey_dir.mkdir(parents=True, exist_ok=True)
    return str(whisperkey_dir)
```

**Note:** Using `platform.system()` directly here instead of importing from `whisper_key.platform` to avoid circular import issues (utils.py is imported early).

## Files to Modify

| File | Changes |
|------|---------|
| `src/whisper_key/utils.py` | Update `get_user_app_data_path()` for cross-platform |

## Success Criteria

- [ ] App starts on macOS without path-related crash
- [ ] Config file created at `~/Library/Application Support/whisperkey/user_settings.yaml`
- [ ] Log file created at `~/Library/Application Support/whisperkey/whisper-key.log`
- [ ] Windows behavior unchanged
