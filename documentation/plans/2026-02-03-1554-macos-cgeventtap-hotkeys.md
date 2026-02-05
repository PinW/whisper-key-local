# macOS CGEventTap Hotkey Implementation

As a *User* I want **modifier-only hotkey detection on macOS** so I can use Fn or Ctrl alone to trigger recording

## Problem

QuickMacHotKey (current dependency) uses Carbon's `RegisterEventHotKey` which cannot detect modifier-only presses. CGEventTap with `kCGEventFlagsChanged` can detect any modifier key.

## Current State

- `platform/macos/hotkeys.py`: Stub that logs warning
- `pyproject.toml`: Has `pyobjc-framework-Quartz` dependency (needed for CGEventTap)
- Interface: `register(bindings)`, `start()`, `stop()`

## Implementation Plan

### Phase 1: Core CGEventTap Setup

- [ ] Create `MacOSHotkeyManager` class in `platform/macos/hotkeys.py`
- [ ] Implement event tap creation with mask for `kCGEventFlagsChanged`, `kCGEventKeyDown`, `kCGEventKeyUp`
- [ ] Add tap to main run loop via `CFRunLoopAddSource(CFRunLoopGetMain(), ...)`
- [ ] Implement cleanup in `stop()` with `CFMachPortInvalidate()` and `CFRelease()`

### Phase 2: Modifier State Tracking

- [ ] Create `ModifierTracker` class to track previous vs current flags
- [ ] Detect transitions: `pressed = changed & new_flags`, `released = changed & ~new_flags`
- [ ] Map flags to modifier names using constants:
  - `fn`: `1 << 23`
  - `control`: `1 << 18`
  - `shift`: `1 << 17`
  - `command`: `1 << 20`
  - `option`: `1 << 19`

### Phase 3: Hotkey String Parsing

- [ ] Create `HotkeyParser` to convert strings like `"ctrl+option"` to `(modifiers, keycode)`
- [ ] Alias mapping: `ctrl→control`, `cmd→command`, `alt→option`, `win→None`
- [ ] Key code mapping for non-modifier keys (space=49, escape=53, etc.)
- [ ] Categorize: modifier-only (`keycode=None`) vs traditional (`keycode=int`)

### Phase 4: Callback Matching

- [ ] Store bindings as `(required_modifiers: frozenset, keycode: int|None, press_cb, release_cb)`
- [ ] For `kCGEventFlagsChanged`: Match modifier-only hotkeys when exact modifiers active
- [ ] For `kCGEventKeyDown`: Match traditional hotkeys when keycode + required modifiers match
- [ ] For modifier release: Fire release callbacks when any required modifier released

### Phase 5: Module Interface

- [ ] Implement `register(bindings)` - parse and store all hotkeys
- [ ] Implement `start()` - create tap, add to run loop, enable
- [ ] Implement `stop()` - disable tap, remove from run loop, cleanup

### Phase 6: Accessibility Permissions

- [ ] Check `AXIsProcessTrusted()` before creating tap
- [ ] If denied: log warning, call `AXIsProcessTrustedWithOptions` with prompt
- [ ] Graceful degradation (app runs without hotkeys)

### Phase 7: Testing

- [ ] Create `tools/test_macos_cgeventtap.py` standalone test
- [ ] Test modifier-only (fn, ctrl, option)
- [ ] Test combos (ctrl+option)
- [ ] Test traditional (ctrl+shift+space)
- [ ] Test release callbacks
- [ ] Full app integration test

## Files to Modify

| File | Changes |
|------|---------|
| `src/whisper_key/platform/macos/hotkeys.py` | Replace stub with full implementation |

## Implementation Details

### Modifier Flag Constants

```python
MODIFIER_FLAGS = {
    'fn': 1 << 23,
    'control': 1 << 18,
    'shift': 1 << 17,
    'command': 1 << 20,
    'option': 1 << 19,
}
```

### Event Tap Creation

```python
mask = (CGEventMaskBit(kCGEventFlagsChanged) |
        CGEventMaskBit(kCGEventKeyDown) |
        CGEventMaskBit(kCGEventKeyUp))

tap = CGEventTapCreate(
    kCGSessionEventTap,
    kCGHeadInsertEventTap,
    kCGEventTapOptionDefault,
    mask,
    callback,
    None
)
```

### Callback Signature

```python
def _event_callback(proxy, event_type, event, refcon):
    # Return event to pass through (don't consume)
    return event
```

### Binding Format (from HotkeyListener)

```python
# Input: [hotkey_string, press_callback, release_callback, flag]
["control + option", on_press, on_release, False]
```

## Success Criteria

1. Modifier-only hotkeys work (fn, ctrl, option, cmd, shift)
2. Modifier combos work (ctrl+option without additional key)
3. Traditional hotkeys work (ctrl+shift+space)
4. Release callbacks work for stop-with-modifier feature
5. Clear permission error when Accessibility disabled
6. Full app recording workflow functional on macOS
