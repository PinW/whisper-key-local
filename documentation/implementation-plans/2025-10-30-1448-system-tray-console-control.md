# System Tray Console Control Implementation Plan

As a *user*, I want to **control console visibility through system tray** so I can hide the console when not needed while still having easy access to it.

## Current State Analysis

### System Tray (system_tray.py)
- System tray menu currently
  - Auto-paste/Copy mode toggle
  - Model selection submenu
  - Start/Stop Recording action (line 136, set as default click action)
  - Exit option
- Default click action on tray icon triggers recording toggle
- Menu rebuilds dynamically based on application state
- Already imports threading, logging, and has infrastructure for state updates

### Console Window
- Console is the primary UI showing application status and logs
- `console=True` in whisper-key.spec (line 58) - console window exists
- No current mechanism to hide/show console programmatically
- No console window event handling

### Configuration (config.defaults.yaml)
- System tray section exists (lines 181-188) with `enabled` and `tooltip` settings
- No console-specific configuration section
- No settings for console visibility or minimize behavior

### Dependencies
- pywin32 already in use for clipboard operations (win32gui, win32con, win32clipboard, win32api)
- win32console module available but not currently imported

## Implementation Plan

### Phase 1: Console Visibility Module
- [x] Create `src/whisper_key/console_manager.py` with console control functionality
  - ✅ Imported win32console, win32gui, win32con, win32process
  - ✅ Added `get_console_window()` - safely gets console window handle with error handling
  - ✅ Added `is_console_owned()` - verifies console belongs to this process using PID comparison
  - ✅ Added `show_console()` - shows/restores console in executable mode, focuses terminal in CLI mode with fallback
  - ✅ Added `hide_console()` - hides console (executable mode only, warns in CLI mode)
  - ✅ Added `is_console_visible()` - checks current visibility state using win32gui.IsWindowVisible
  - ✅ Added comprehensive error handling, logging, and thread safety with lock

### Phase 2: Configuration Schema
- [x] Update `config.defaults.yaml` - add new console section
  - ✅ Added `console:` section after system_tray section (lines 190-196)
  - ✅ Added `start_hidden: false` setting with default value
  - ✅ Added documentation comments explaining the setting and CLI mode behavior

### Phase 3: System Tray Menu Updates
- [x] Modify `system_tray.py` menu structure
  - ✅ Added "Show Console" menu item (executable mode) / "Focus Terminal" (CLI mode) with dynamic label
  - ✅ Changed default click action to show console (default=True on menu item)
  - ✅ Added `_show_console()` method that delegates to state_manager.show_console()
  - ✅ Removed Start/Stop Recording menu item and related action_label/action_enabled logic

### Phase 4: State Manager Integration
- [x] Update `state_manager.py` to coordinate console visibility
  - ✅ Added ConsoleManager import (line 12)
  - ✅ Added console_manager as required parameter (line 23) and instance variable (line 30)
  - ✅ Added `show_console()` method at line 242-243 that delegates to console_manager
  - ✅ Console manager is accessible to system_tray via state_manager.console_manager

### Phase 5: Startup Behavior
- [x] Update `main.py` initialization sequence
  - ✅ Added ConsoleManager import (line 18)
  - ✅ Added `is_built_executable()` helper function (lines 22-23) to detect PyInstaller executable
  - ✅ Added `setup_console_manager()` function (lines 106-110)
  - ✅ Added `get_console_config()` method to ConfigManager (config_manager.py:206-207)
  - ✅ Initialize console_manager early with mode detection (lines 173-176)
  - ✅ Pass console_manager to StateManager (line 187)
  - ✅ Check `console.start_hidden` config after startup (lines 205-211)
  - ✅ Hide console after 2-second delay if configured (executable mode only)
  - ✅ Log warning if start_hidden set in CLI mode (line 211)

### Phase 6: Executable vs CLI Detection
- [x] Add runtime detection for built executable vs source/CLI mode
  - ✅ Detect PyInstaller executable using `sys.frozen` and `sys._MEIPASS` (line 22-23)
  - ✅ Console_manager initialized with is_executable_mode parameter (line 176)
  - ✅ Mode logged in console_manager.__init__() (console_manager.py:22)
- [x] Extend console_manager for CLI mode terminal focusing
  - ✅ `win32console.GetConsoleWindow()` works in both modes (console_manager.py:30)
  - ✅ `show_console()` uses SetWindowPos for CLI, ShowWindow/SetForegroundWindow for executable (lines 59-88)
  - ✅ `start_hidden` config ignored in CLI mode with warning (main.py:211)
- [x] Update system_tray.py to handle both modes
  - ✅ Dynamic menu label: "Show Console" (executable) / "Focus Terminal" (CLI) (system_tray.py:102)
  - ✅ Both modes use same _show_console() method with different behavior based on is_executable_mode

## Implementation Details

### Console Manager Module Structure
```python
# console_manager.py
import win32console
import win32gui
import win32con
import logging
import threading

class ConsoleManager:
    def __init__(self, config: dict, is_executable_mode: bool = False):
        self.logger = logging.getLogger(__name__)
        self.config = config
        self.is_executable_mode = is_executable_mode
        self.console_handle = None

    def get_console_window(self):
        # Returns console window handle or None
        # self.console_handle = win32console.GetConsoleWindow()

    def show_console(self):
        # Executable mode: Show/restore and focus console window
        # win32gui.ShowWindow(handle, win32con.SW_RESTORE)
        # win32gui.SetForegroundWindow(handle)

    def hide_console(self):
        # Executable mode only: Hide console to background
        # win32gui.ShowWindow(handle, win32con.SW_HIDE)

    def focus_terminal(self):
        # CLI mode: Bring terminal window to front
        # win32gui.SetWindowPos(handle, win32con.HWND_TOP, 0, 0, 0, 0,
        #                       win32con.SWP_NOSIZE | win32con.SWP_NOMOVE)
```

### Configuration Schema
```yaml
# Console visibility settings
console:
  # Start with console hidden
  # true = app starts with console hidden to system tray
  # false = app starts with console visible (default)
  start_hidden: false
```

### System Tray Menu Updates
```python
# New menu structure in _create_menu()
menu_items = [
    pystray.MenuItem("Auto-paste", ...),
    pystray.MenuItem("Copy to clipboard", ...),
    pystray.Menu.SEPARATOR,
    pystray.MenuItem(f"Model: {current_model.title()}", ...),
    pystray.Menu.SEPARATOR,
    pystray.MenuItem("Show Console", self._show_console, default=True)
    pystray.Menu.SEPARATOR,
    pystray.MenuItem("Exit", self._quit_application_from_tray)
]
```

**Behavior Notes:**
- Tray icon only shows/focuses console (never hides)
- Console can be minimized normally to taskbar

### Executable vs CLI Mode Detection
```python
import sys

def is_built_executable():
    # Check if running as PyInstaller executable
    return getattr(sys, 'frozen', False) and hasattr(sys, '_MEIPASS')

# In main.py or state_manager.py initialization:
is_executable = is_built_executable()
self.console_manager = ConsoleManager(config, is_executable_mode=is_executable)

# In console_manager.py:
class ConsoleManager:
    def __init__(self, config: dict, is_executable_mode: bool = False):
        self.is_executable_mode = is_executable_mode
        # Get console window handle (works in both modes)
        self.console_handle = win32console.GetConsoleWindow()

        if is_executable_mode:
            # Full console control: hide/show
            if config.get('console', {}).get('start_hidden'):
                # Initialize with start_hidden behavior
        else:
            # CLI mode: only terminal focusing, ignore config
            if config.get('console', {}).get('start_hidden'):
                self.logger.warning("Console config ignored in CLI mode")
```

### Terminal Focusing in CLI Mode

**Key Discovery:** `win32console.GetConsoleWindow()` works in both executable and CLI modes:
- **Executable mode**: Returns the console window owned by the .exe process
- **CLI mode**: Returns the terminal window (cmd.exe, PowerShell, Windows Terminal) that launched Python

**Focusing Approach (avoids "Access Denied" errors):**
```python
# SetWindowPos with HWND_TOP
win32gui.SetWindowPos(
    console_handle,
    win32con.HWND_TOP,  # Bring to top of Z-order
    0, 0, 0, 0,  # Position (ignored with flags below)
    win32con.SWP_NOSIZE | win32con.SWP_NOMOVE  # Don't change size/position
)
```

**Notes:**
- If SetWindowPos doesn't work, fallback approach is `win32gui.ShowWindow(handle, win32con.SW_RESTORE)` + `win32gui.SetForegroundWindow(handle)`

**Target Use Cases:**
- **Windows Executable**: Console show/focus control
- **CLI**: Terminal focusing

## Files to Modify

1. **NEW: `src/whisper_key/console_manager.py`**
   - Create new module for console visibility control

2. **`src/whisper_key/config.defaults.yaml`**
   - Add new `console:` section with `start_hidden` setting

3. **`src/whisper_key/system_tray.py`**
   - Remove Start/Stop Recording menu item
   - Add "Show Console" menu item (always shows, never hides)
   - Change default click action to show console
   - Add method to show console via state_manager

4. **`src/whisper_key/state_manager.py`**
   - Initialize console_manager instance
   - Add `show_console()` method to delegate to console_manager

5. **`src/whisper_key/main.py`**
   - Initialize console_manager early in startup
   - Check config and hide console after startup if configured
   - Ensure proper cleanup on shutdown

## Success Criteria

### Built Executable Mode
- [ ] Clicking system tray icon shows the console window
- [ ] Clicking tray icon when console is already visible brings it to foreground and focuses it
- [ ] When `start_hidden: true`, app starts with console hidden to tray
- [ ] Closing console window (X button) exits the application
- [ ] All recording/transcription functionality works with console hidden
- [ ] "Show Console" menu item appears in system tray

### CLI Mode
- [ ] Console manager initialized with terminal focusing capability
- [ ] Tray icon click successfully brings terminal window to front
- [ ] "Focus Terminal" menu item appears in system tray
- [ ] `start_hidden` config ignored with warning in CLI mode