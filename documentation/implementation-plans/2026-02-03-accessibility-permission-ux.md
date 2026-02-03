# Accessibility Permission UX (macOS)

## Goal

Provide clear UX when macOS Accessibility permission is missing for auto-paste.

## Trigger Points

1. **Startup**: If auto-paste is enabled in config
2. **Runtime**: When user toggles auto-paste ON via system tray menu

## Flow

```
[Auto-paste enabled] → [Check permission silently] → [Missing?]
                                                         ↓
                              ┌─────────────────────────────────────────┐
                              │ ⚠️  Auto-paste requires Accessibility   │
                              │                                         │
                              │ Your terminal needs permission to       │
                              │ simulate Cmd+V keyboard shortcut.       │
                              │                                         │
                              │ What would you like to do?              │
                              │   [1] Grant permission (opens settings, │
                              │       then app closes - restart after)  │
                              │   [2] Disable auto-paste (clipboard     │
                              │       only, saves to config)            │
                              │                                         │
                              │ Choice [1/2]:                           │
                              └─────────────────────────────────────────┘
                                         ↓                    ↓
                                    Choice 1              Choice 2
                                         ↓                    ↓
                              Show system dialog      Update config file
                              Exit app                Set auto_paste=false
                                                      Continue running
```

## Implementation

### 1. Create `terminal_ui.py` (cross-platform)

Location: `src/whisper_key/terminal_ui.py`

```python
def prompt_choice(message: str, options: list[str]) -> int:
    """
    Display message and options, return 0-based index of choice.
    Returns -1 if interrupted (Ctrl+C).
    """
```

### 2. Create `platform/macos/permissions.py`

```python
def check_accessibility_permission() -> bool:
    """Check if Accessibility permission granted (no prompt)."""

def request_accessibility_permission():
    """Show system dialog offering to open Settings."""

def handle_missing_permission(config_manager) -> bool:
    """
    Show terminal prompt, handle user choice.
    Returns True if app should continue, False if app should exit.
    """
```

### 3. Update `platform/macos/keyboard.py`

- Remove current permission checking logic
- Just do keyboard simulation (assume permission handled elsewhere)

### 4. Add permission check to startup flow

In `main.py` or `state_manager.py`:
- After config loaded, if macOS and auto_paste enabled → check permission
- Call `handle_missing_permission()` if needed

### 5. Add permission check to system tray toggle

When user enables auto-paste via menu:
- Check permission
- Call `handle_missing_permission()` if needed

## Steps

- [ ] Create `terminal_ui.py` with `prompt_choice()` function
- [ ] Create `platform/macos/permissions.py` with permission check functions
- [ ] Update `platform/macos/keyboard.py` to remove permission logic
- [ ] Add startup permission check in main flow
- [ ] Add runtime permission check when toggling auto-paste
- [ ] Test flow on macOS

## Files Changed

- `src/whisper_key/terminal_ui.py` (new)
- `src/whisper_key/platform/macos/permissions.py` (new)
- `src/whisper_key/platform/macos/keyboard.py` (modify)
- `src/whisper_key/platform/macos/__init__.py` (export permissions)
- `src/whisper_key/main.py` or `state_manager.py` (startup check)
- `src/whisper_key/system_tray.py` (toggle check)
