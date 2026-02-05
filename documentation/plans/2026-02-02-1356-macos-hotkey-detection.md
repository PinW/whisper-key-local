# macOS Hotkey Detection Implementation

As a *user* I want **global hotkeys to work on macOS** so I can use whisper-key on my Mac.

## Prerequisites

- [x] ~~`run_detached()` refactor complete~~ - NSApplication runs on main thread via `platform/macos/app.py`. See: `2026-02-03-macos-run-detached-refactor.md`

## Current State

- Platform abstraction layer exists (`platform/macos/hotkeys.py` is a stub)
- Windows implementation wraps `global-hotkeys` library
- `hotkey_listener.py` uses `platform.hotkeys.register()`, `.start()`, `.stop()`
- NSApplication event loop handled by main.py (after refactor)

## Implementation Plan

### Phase 1: Verify QuickMacHotKey Works

- [x] ~~Create standalone test script `tools/test_macos_hotkey.py`~~
- [x] ~~Register one hardcoded hotkey (ctrl+shift+space)~~
- [x] ~~Print message when pressed~~
- [ ] **Manual test:** install `quickmachotkey` on macOS, run script, verify hotkey fires

### Phase 2: Combined Tray + Hotkey Test

- [ ] Create test script `tools/test_macos_tray_hotkey.py`
- [ ] Use `run_detached()` approach with NSApplication on main thread
- [ ] Register a hotkey and show a tray icon
- [ ] **Manual test:** both tray icon and hotkey work simultaneously

### Phase 3: Implement platform/macos/hotkeys.py

- [ ] Implement `register(bindings)` - accepts same format as Windows
- [ ] Implement `start()` - registers hotkeys with QuickMacHotKey
- [ ] Implement `stop()` - unregisters hotkeys
- [ ] Use hardcoded key mapping initially (defer full string parsing)
- [ ] Test: hotkeys module works in isolation

### Phase 4: Integration Test

- [ ] Create `tools/test_macos_integration.py`
- [ ] Use `HotkeyListener` class with `platform.hotkeys`
- [ ] Verify callback fires correctly
- [ ] **Manual test:** hotkey_listener works with new macOS backend

### Phase 5: Accessibility Permissions Handling

- [ ] Research how QuickMacHotKey handles missing permissions
- [ ] Detect when Accessibility permission is missing
- [ ] Show clear user message (not silent failure)
- [ ] Optionally: prompt user to open System Preferences
- [ ] **Manual test:** run without permissions, verify clear error message

### Phase 6: String Parsing (hotkey format conversion)

- [ ] Map config strings ("ctrl+shift+space") to QuickMacHotKey format
- [ ] Handle modifier keys: ctrl, shift, cmd/command, alt/option
- [ ] Handle common keys: space, enter, escape, letters, numbers
- [ ] Test: various hotkey string formats parse correctly

### Phase 7: Full App Test

- [ ] Run whisper-key app on macOS
- [ ] Verify tray icon appears
- [ ] Verify hotkey triggers recording
- [ ] Document any remaining issues

## Implementation Details

### Binding Format (Windows)

Current bindings passed to `hotkeys.register()`:
```python
[
    ["control + shift + space", callback, release_callback, False],
    ["control + shift + enter", callback, None, False],
    ...
]
```

### QuickMacHotKey API

```python
from quickmachotkey import quickHotKey, mask
from quickmachotkey.constants import kVK_Space, controlKey, shiftKey

@quickHotKey(virtualKey=kVK_Space, modifierMask=mask(controlKey, shiftKey))
def my_callback():
    print("Hotkey pressed!")
```

Key constants are in `quickmachotkey.constants` (e.g., `kVK_Space`, `kVK_Return`).
Modifier constants: `controlKey`, `shiftKey`, `cmdKey`, `optionKey`.

### Key Code Mapping

Will need to map string names to virtual key codes:
```python
KEY_CODES = {
    'space': 49,    # kVK_Space
    'enter': 36,    # kVK_Return
    'return': 36,
    'escape': 53,   # kVK_Escape
    'a': 0, 'b': 11, 'c': 8, ...
}

MODIFIERS = {
    'ctrl': controlKey,
    'control': controlKey,
    'shift': shiftKey,
    'cmd': cmdKey,
    'command': cmdKey,
    'alt': optionKey,
    'option': optionKey,
}
```

## Files to Create

| File | Purpose |
|------|---------|
| `tools/test_macos_hotkey.py` | Standalone hotkey test |
| `tools/test_macos_tray_hotkey.py` | Combined tray + hotkey test |
| `tools/test_macos_integration.py` | HotkeyListener integration test |

## Files to Modify

| File | Changes |
|------|---------|
| `platform/macos/hotkeys.py` | Full implementation |

## Dependencies

Already in pyproject.toml with macOS markers:
- [x] `quickmachotkey` (macOS-only)
- [x] `pyobjc-framework-Quartz` (macOS-only)

## Success Criteria

- [ ] Standalone hotkey test registers and fires callback
- [ ] Tray icon and hotkeys work together
- [ ] HotkeyListener class works with macOS backend
- [ ] Missing Accessibility permission shows clear error
- [ ] App starts and responds to hotkeys on macOS
