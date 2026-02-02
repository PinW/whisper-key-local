# macOS Hotkey Detection Implementation

As a *user* I want **global hotkeys to work on macOS** so I can use whisper-key on my Mac.

## Current State

- Platform abstraction layer exists (`platform/macos/hotkeys.py` is a placeholder)
- Windows implementation wraps `global-hotkeys` library
- `hotkey_listener.py` uses `platform.hotkeys.register()`, `.start()`, `.stop()`
- Design doc notes NSApplication event loop is required (QuickMacHotKey + pystray may share it)

## Implementation Plan

### Phase 1: Verify QuickMacHotKey Works
- [ ] Create standalone test script `tools/test_macos_hotkey.py`
- [ ] Register one hardcoded hotkey (ctrl+shift+space)
- [ ] Print message when pressed
- [ ] **Manual test:** install `quickmachotkey` on macOS, run script, verify hotkey fires

### Phase 2: NSApplication Event Loop Investigation
- [ ] Create test script `tools/test_macos_tray_hotkey.py` using both pystray AND QuickMacHotKey
- [ ] Determine if they can share NSApplication (design doc suggests yes)
- [ ] Document findings and approach
- [ ] **Manual test:** both tray icon and hotkey work simultaneously

### Phase 3: Implement platform/macos/hotkeys.py
- [ ] Implement `register(bindings)` - accepts same format as Windows
- [ ] Implement `start()` - starts listening (NSApplication coordination)
- [ ] Implement `stop()` - stops listening
- [ ] Use hardcoded key mapping initially (defer string parsing)
- [ ] Test: hotkeys module works in isolation

### Phase 4: Integration Test Script
- [ ] Create `tools/test_macos_integration.py`
- [ ] Use `HotkeyListener` class with `platform.hotkeys`
- [ ] Verify callback fires correctly
- [ ] **Manual test:** hotkey_listener works with new macOS backend

### Phase 5: Accessibility Permissions Handling
- [ ] Research how QuickMacHotKey handles missing permissions
- [ ] Detect when Accessibility/Input Monitoring permission is missing
- [ ] Show clear user message when permission denied (not silent failure)
- [ ] Optionally: prompt user to open System Preferences > Privacy > Accessibility
- [ ] **Manual test:** run without permissions granted, verify clear error message

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

### Phase 8: Update pyproject.toml
- [ ] Add `quickmachotkey` (macOS-only marker)
- [ ] Add `pyobjc-framework-Quartz` (macOS-only marker)
- [ ] Add `pyobjc-framework-ApplicationServices` (macOS-only marker)
- [ ] Verify `pip install` works on both platforms

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

### NSApplication Coordination

pystray on macOS runs `NSApplication.sharedApplication().run()` internally.
QuickMacHotKey also needs NSApplication running.

Design doc approach:
```python
# Both use the same shared NSApplication
nsapp = NSApplication.sharedApplication()
# Register hotkeys before starting pystray
icon.run()  # This runs the event loop
```

Need to verify this works in Phase 3.

## Files to Create

| File | Purpose |
|------|---------|
| `tools/test_macos_hotkey.py` | Standalone hotkey test |
| `tools/test_macos_tray_hotkey.py` | Combined tray + hotkey test |
| `tools/test_macos_integration.py` | HotkeyListener integration test |

## Files to Modify

| File | Changes |
|------|---------|
| `pyproject.toml` | Add macOS-only dependencies |
| `platform/macos/hotkeys.py` | Full implementation |

## Success Criteria

- [ ] `pip install` works on macOS with all dependencies
- [ ] Standalone hotkey test registers and fires callback
- [ ] Tray icon and hotkeys work together
- [ ] HotkeyListener class works with macOS backend
- [ ] Missing Accessibility permission shows clear error (not silent failure)
- [ ] App starts and responds to hotkeys on macOS
