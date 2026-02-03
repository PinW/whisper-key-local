# NSEvent Hotkey Implementation for macOS

As a *mac user* I want **global hotkeys using NSEvent monitoring** so hotkeys work reliably and can support Fn key in the future.

## Why NSEvent Instead of QuickMacHotKey

- **Simpler integration** - Pure Python/PyObjC, no decorator magic
- **Fn key ready** - Can detect Fn modifier when we add support later
- **Same API surface** - Can implement same `register()`, `start()`, `stop()` interface
- **No external dependency** - Uses PyObjC we already have

## Current State

- `platform/macos/hotkeys.py` is a stub (logs warning, does nothing)
- `hotkey_listener.py` expects `register(bindings)`, `start()`, `stop()`
- NSApplication event loop already running in `platform/macos/app.py`

## Implementation Plan

### Phase 1: Minimal Working Implementation

- [ ] Implement `_global_handler()` that receives all key events
- [ ] Implement `register(bindings)` that stores hotkey configs
- [ ] Implement `start()` that calls `NSEvent.addGlobalMonitorForEventsMatchingMask_handler_()`
- [ ] Implement `stop()` that calls `NSEvent.removeMonitor_()`
- [ ] Test with hardcoded hotkey (ctrl+cmd)

### Phase 2: Key String Parsing

- [ ] Parse hotkey strings like "ctrl+option" into modifier flags
- [ ] Map modifier names to `NSEventModifierFlag` constants:
  - `ctrl`/`control` → `NSControlKeyMask`
  - `cmd`/`command` → `NSCommandKeyMask`
  - `option`/`alt` → `NSAlternateKeyMask`
  - `shift` → `NSShiftKeyMask`
- [ ] Handle virtual key codes for non-modifier keys (space, letters, etc.)
- [ ] Test with config-based hotkey strings

### Phase 3: Integration with HotkeyListener

- [ ] Verify `hotkey_listener.py` works with new macOS backend
- [ ] Test press callback fires correctly
- [ ] Test release callback (if needed for stop-with-modifier feature)
- [ ] Full app test on macOS

### Phase 4: Fn Key Support (Future)

- [ ] Add `fn` to modifier parsing
- [ ] Map to `NSEventModifierFlagFunction`
- [ ] Update config defaults to use `fn+control`
- [ ] Test Fn key detection

## Implementation Details

### Modifier Flag Mapping

```python
from AppKit import NSEvent

MODIFIER_MAP = {
    'ctrl': NSEvent.NSControlKeyMask,
    'control': NSEvent.NSControlKeyMask,
    'cmd': NSEvent.NSCommandKeyMask,
    'command': NSEvent.NSCommandKeyMask,
    'option': NSEvent.NSAlternateKeyMask,
    'alt': NSEvent.NSAlternateKeyMask,
    'shift': NSEvent.NSShiftKeyMask,
    # Future: 'fn': NSEvent.NSFunctionKeyMask,
}
```

### Core Implementation Sketch

```python
from AppKit import NSEvent

_monitor = None
_bindings = []

def register(bindings):
    global _bindings
    _bindings = bindings

def start():
    global _monitor
    _monitor = NSEvent.addGlobalMonitorForEventsMatchingMask_handler_(
        NSEvent.NSKeyDownMask,
        _handle_event
    )

def stop():
    global _monitor
    if _monitor:
        NSEvent.removeMonitor_(_monitor)
        _monitor = None

def _handle_event(event):
    current_flags = event.modifierFlags() & NSEvent.NSDeviceIndependentModifierFlagsMask
    key_code = event.keyCode()

    for binding in _bindings:
        if _matches(binding, current_flags, key_code):
            binding['callback']()
```

### Binding Format (from hotkey_listener.py)

```python
[
    {
        'combination': 'ctrl+cmd',
        'callback': some_function,
        'release_callback': optional_function,  # may be None
        'name': 'standard'
    },
    ...
]
```

## Files to Modify

| File | Changes |
|------|---------|
| `platform/macos/hotkeys.py` | Full implementation |

## Files to Create

| File | Purpose |
|------|---------|
| `tools/test_nsevent_hotkey.py` | Standalone test script |

## Success Criteria

- [ ] Standalone test detects ctrl+cmd press
- [ ] App starts and hotkey triggers recording on macOS
- [ ] Stop-with-modifier works (release detection)
- [ ] Cancel hotkey (esc) works

## Risks

| Risk | Mitigation |
|------|------------|
| Release callback timing | NSKeyUpMask may need separate monitor |
| Modifier-only hotkeys (no regular key) | May need to detect modifier key press directly via keyCode |
| Accessibility permissions | Add clear error message if monitor returns None |

## Notes

- NSEvent monitoring requires Accessibility permissions
- Monitor returns `None` if permissions denied - must handle gracefully
- Main thread not required for `addGlobalMonitorForEventsMatchingMask_handler_`
