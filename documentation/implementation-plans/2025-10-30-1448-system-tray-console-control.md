# System Tray Console Control Implementation Plan

As a *user*, I want to **control console visibility through system tray** so I can hide the console when not needed while still having easy access to it.

## Current State Analysis

### System Tray (system_tray.py)
- System tray menu currently includes:
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
- [ ] Create `src/whisper_key/console_manager.py` with console control functionality
  - [ ] Import win32console, win32gui, win32con
  - [ ] Add `get_console_window()` - safely get console window handle
  - [ ] Add `is_console_owned()` - verify console belongs to this process
  - [ ] Add `show_console()` - make console visible
  - [ ] Add `hide_console()` - hide console to background
  - [ ] Add `is_console_visible()` - check current visibility state
  - [ ] Add error handling and logging for all operations

### Phase 2: Configuration Schema
- [ ] Update `config.defaults.yaml` - add new console section
  - [ ] Add `console:` section after system_tray section
  - [ ] Add `start_hidden: false` - start with console hidden
  - [ ] Add `minimize_to_tray: false` - minimize hides to tray instead of taskbar
  - [ ] Add documentation comments for each setting

### Phase 3: System Tray Menu Updates
- [ ] Modify `system_tray.py` menu structure
  - [ ] Remove Start/Stop Recording menu item (line 136)
  - [ ] Add "Show Console" / "Hide Console" menu item (dynamic text based on state)
  - [ ] Change default click action from recording toggle to console show
  - [ ] Update `_create_menu()` to check console visibility state
  - [ ] Add `_toggle_console()` method to handle menu click

### Phase 4: Console Window Event Monitoring
- [ ] Extend `console_manager.py` with window message monitoring
  - [ ] Add `start_window_monitoring()` - monitor console window events
  - [ ] Add window procedure to intercept WM_SIZE messages (minimize events)
  - [ ] Add callback mechanism for minimize events
  - [ ] Use separate thread for message loop
  - [ ] Add `stop_window_monitoring()` for cleanup

### Phase 5: Minimize to Tray Integration
- [ ] Implement minimize-to-tray behavior in `console_manager.py`
  - [ ] On minimize event, check config `minimize_to_tray` setting
  - [ ] If enabled, hide console instead of minimizing to taskbar
  - [ ] Log minimize-to-tray actions

### Phase 6: State Manager Integration
- [ ] Update `state_manager.py` to coordinate console visibility
  - [ ] Add console_manager instance initialization
  - [ ] Add `toggle_console_visibility()` method
  - [ ] Add `get_console_visibility()` method for menu state
  - [ ] Ensure console_manager available to system_tray

### Phase 7: Startup Behavior
- [ ] Update `main.py` initialization sequence
  - [ ] Initialize console_manager before other components
  - [ ] Check `console.start_hidden` config after startup complete
  - [ ] Hide console if configured after brief delay (allow startup messages to display)
  - [ ] Add logging for console visibility actions

### Phase 8: Testing & Validation
- [ ] Manual testing checklist
  - [ ] Test show/hide from system tray menu
  - [ ] Test default click action shows console
  - [ ] Test minimize to tray when enabled in config
  - [ ] Test minimize to taskbar when disabled in config
  - [ ] Test start_hidden config option
  - [ ] Test console close (X button) exits application
  - [ ] Verify recording still works with console hidden

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
    def __init__(self, config: dict):
        self.logger = logging.getLogger(__name__)
        self.config = config
        self.console_handle = None
        self.monitoring_thread = None
        self.minimize_callback = None

    def get_console_window(self):
        # Returns console window handle or None

    def is_console_owned(self):
        # Check if console belongs to this process
        # Return len(win32console.GetConsoleProcessList()) == 1

    def show_console(self):
        # win32gui.ShowWindow(handle, win32con.SW_SHOW)

    def hide_console(self):
        # win32gui.ShowWindow(handle, win32con.SW_HIDE)

    def is_console_visible(self):
        # win32gui.IsWindowVisible(handle)

    def start_window_monitoring(self, minimize_callback):
        # Start monitoring thread for window events

    def stop_window_monitoring(self):
        # Stop monitoring and cleanup
```

### Configuration Schema
```yaml
# Console visibility and behavior settings
console:
  # Start with console hidden
  # true = app starts with console hidden to system tray
  # false = app starts with console visible (default)
  start_hidden: false

  # Minimize console to system tray instead of taskbar
  # true = clicking minimize hides console to tray
  # false = clicking minimize minimizes to taskbar normally
  minimize_to_tray: false
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
    pystray.MenuItem(console_label, self._toggle_console, default=True),  # New default action
    pystray.Menu.SEPARATOR,
    pystray.MenuItem("Exit", self._quit_application_from_tray)
]
```

### Window Event Detection Approach
- Use `win32gui.SetWindowLong()` to install window procedure
- Monitor `WM_SIZE` message with `SIZE_MINIMIZED` parameter
- Alternative: Poll `win32gui.IsIconic()` in separate thread if SetWindowLong doesn't work
- Call minimize_callback when minimize detected

## Files to Modify

1. **NEW: `src/whisper_key/console_manager.py`**
   - Create new module for console visibility control
   - Window event monitoring for minimize detection

2. **`src/whisper_key/config.defaults.yaml`**
   - Add new `console:` section with `start_hidden` and `minimize_to_tray` settings

3. **`src/whisper_key/system_tray.py`**
   - Remove Start/Stop Recording menu item
   - Add Show/Hide Console menu item
   - Change default click action to toggle console visibility
   - Add method to toggle console via state_manager

4. **`src/whisper_key/state_manager.py`**
   - Initialize console_manager instance
   - Add console visibility toggle and query methods
   - Pass console state to system tray for menu updates

5. **`src/whisper_key/main.py`**
   - Initialize console_manager early in startup
   - Check config and hide console after startup if configured
   - Ensure proper cleanup on shutdown

## Success Criteria

- [ ] Clicking system tray icon shows/brings forward the console window
- [ ] "Show Console" / "Hide Console" menu item works correctly with dynamic label
- [ ] Console can be hidden and shown multiple times without issues
- [ ] When `start_hidden: true`, app starts with console hidden to tray
- [ ] When `minimize_to_tray: true`, minimizing console hides it to tray
- [ ] When `minimize_to_tray: false`, minimizing console works normally (taskbar)
- [ ] Closing console window (X button) exits the application
- [ ] All recording/transcription functionality works with console hidden
- [ ] No Start/Stop Recording menu items in system tray
- [ ] Console visibility persists correctly across show/hide cycles
- [ ] No crashes or errors related to console window manipulation
