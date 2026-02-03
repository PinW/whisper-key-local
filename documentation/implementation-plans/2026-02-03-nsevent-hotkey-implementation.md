# NSEvent Hotkey Implementation for macOS

As a *mac user* I want **global hotkeys using NSEvent monitoring** so hotkeys work reliably and can support Fn key in the future.

## Why NSEvent Instead of QuickMacHotKey

- **Simpler integration** - Pure Python/PyObjC, no decorator magic, no C callbacks
- **Fn key ready** - Can detect Fn modifier when we add support later
- **Same API surface** - Can implement same `register()`, `start()`, `stop()` interface
- **No external dependency** - Uses PyObjC we already have
- **Modifier-only support** - Can detect `ctrl+cmd` without a regular key via `NSFlagsChanged`

## Current State

- `platform/macos/hotkeys.py` is a stub (logs warning, does nothing)
- `hotkey_listener.py` expects `register(bindings)`, `start()`, `stop()`
- NSApplication event loop already running in `platform/macos/app.py`
- Binding format from `hotkey_listener.py` is list of tuples: `[hotkey_string, press_cb, release_cb, flag]`

## Implementation Plan

### Phase 1: Core Event Monitoring

- [ ] Monitor BOTH `NSKeyDownMask` AND `NSFlagsChangedMask` events
- [ ] Implement `ModifierStateTracker` class to track previous vs current modifier flags
- [ ] Detect modifier transitions: `pressed = (new_flags & ~old_flags)`, `released = (old_flags & ~new_flags)`
- [ ] Implement `register(bindings)` that parses and stores hotkey configs
- [ ] Implement `start()` that creates the monitor
- [ ] Implement `stop()` that removes the monitor
- [ ] Test with hardcoded modifier-only hotkey (ctrl+cmd)

### Phase 2: Hotkey Matching

- [ ] Categorize bindings: modifier-only (`keycode=None`) vs traditional (`keycode=int`)
- [ ] For `NSFlagsChanged` events: match modifier-only hotkeys when exact modifiers become active
- [ ] For `NSKeyDown` events: match traditional hotkeys when keycode + modifiers match
- [ ] Fire press callback on match
- [ ] Fire release callback when any required modifier is released

### Phase 3: Key String Parsing

- [ ] Parse hotkey strings like "ctrl+option" into `(modifier_mask, keycode)`
- [ ] Map modifier names to flag constants (use modern names):
  - `ctrl`/`control` → `NSEventModifierFlagControl`
  - `cmd`/`command` → `NSEventModifierFlagCommand`
  - `option`/`alt` → `NSEventModifierFlagOption`
  - `shift` → `NSEventModifierFlagShift`
- [ ] Map key names to virtual key codes (space=49, escape=53, etc.)
- [ ] Handle alias: `win` → ignore on macOS (Windows-only)
- [ ] Test with config-based hotkey strings

### Phase 4: Integration with HotkeyListener

- [ ] Match binding format: `[hotkey_string, press_cb, release_cb, flag]` (list, not dict!)
- [ ] Verify `hotkey_listener.py` works with new macOS backend
- [ ] Test press callback fires correctly
- [ ] Test release callback fires for stop-with-modifier feature
- [ ] Full app test on macOS

### Phase 5: Fn Key Support (Future)

- [ ] Add `fn` to modifier parsing
- [ ] Map to `NSEventModifierFlagFunction`
- [ ] Update config defaults to use `fn+control`
- [ ] Test Fn key detection

## Implementation Details

### Modifier Flag Constants (Modern Names)

```python
from AppKit import NSEvent

MODIFIER_FLAGS = {
    'ctrl': NSEvent.NSEventModifierFlagControl,
    'control': NSEvent.NSEventModifierFlagControl,
    'cmd': NSEvent.NSEventModifierFlagCommand,
    'command': NSEvent.NSEventModifierFlagCommand,
    'option': NSEvent.NSEventModifierFlagOption,
    'alt': NSEvent.NSEventModifierFlagOption,
    'shift': NSEvent.NSEventModifierFlagShift,
    # Future: 'fn': NSEvent.NSEventModifierFlagFunction,
}

# Mask to isolate modifier flags from other event flags
MODIFIER_MASK = (
    NSEvent.NSEventModifierFlagControl |
    NSEvent.NSEventModifierFlagCommand |
    NSEvent.NSEventModifierFlagOption |
    NSEvent.NSEventModifierFlagShift
)
```

### Modifier State Tracker

```python
class ModifierStateTracker:
    def __init__(self):
        self.previous_flags = 0

    def update(self, new_flags):
        new_flags = new_flags & MODIFIER_MASK
        old_flags = self.previous_flags

        pressed = new_flags & ~old_flags    # Bits that turned ON
        released = old_flags & ~new_flags   # Bits that turned OFF

        self.previous_flags = new_flags
        return old_flags, new_flags, pressed, released
```

### Core Implementation Sketch

```python
from AppKit import NSEvent

_monitor = None
_bindings = []  # List of ParsedBinding objects
_state = ModifierStateTracker()

def register(bindings):
    global _bindings
    _bindings = [_parse_binding(b) for b in bindings]

def start():
    global _monitor
    mask = NSEvent.NSKeyDownMask | NSEvent.NSFlagsChangedMask
    _monitor = NSEvent.addGlobalMonitorForEventsMatchingMask_handler_(
        mask,
        _handle_event
    )
    if _monitor is None:
        logger.error("Failed to create event monitor - check Accessibility permissions")

def stop():
    global _monitor
    if _monitor:
        NSEvent.removeMonitor_(_monitor)
        _monitor = None

def _handle_event(event):
    event_type = event.type()

    if event_type == NSEvent.NSFlagsChanged:
        _handle_flags_changed(event)
    elif event_type == NSEvent.NSKeyDown:
        _handle_key_down(event)

def _handle_flags_changed(event):
    old_flags, new_flags, pressed, released = _state.update(event.modifierFlags())

    # Check modifier-only bindings
    for binding in _bindings:
        if binding.keycode is not None:
            continue  # Not a modifier-only binding

        # Press: exact modifiers just became active
        if new_flags == binding.modifiers and old_flags != binding.modifiers:
            binding.press_callback()
            binding.is_active = True

        # Release: was active, now a required modifier was released
        elif binding.is_active and (released & binding.modifiers):
            if binding.release_callback:
                binding.release_callback()
            binding.is_active = False

def _handle_key_down(event):
    current_flags = event.modifierFlags() & MODIFIER_MASK
    key_code = event.keyCode()

    for binding in _bindings:
        if binding.keycode is None:
            continue  # Modifier-only, handled by flags_changed

        if key_code == binding.keycode and current_flags == binding.modifiers:
            binding.press_callback()
```

### Binding Format (from hotkey_listener.py)

**Actual format is a list of lists (not dicts!):**
```python
[
    ["control + command", on_press, on_release, False],
    ["escape", on_cancel, None, False],
    ...
]
```

### Parsed Binding Structure

```python
@dataclass
class ParsedBinding:
    original: str
    modifiers: int        # Combined modifier flags
    keycode: int | None   # None for modifier-only hotkeys
    press_callback: Callable
    release_callback: Callable | None
    is_active: bool = False
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

- [ ] Standalone test detects ctrl+cmd press (modifier-only)
- [ ] Standalone test detects ctrl+option+space (traditional)
- [ ] Release callback fires when modifier released
- [ ] App starts and hotkey triggers recording on macOS
- [ ] Stop-with-modifier works (release detection)
- [ ] Cancel hotkey (esc) works

## Risks

| Risk | Mitigation |
|------|------------|
| Accessibility permissions denied | Check if monitor is None, log clear error message |
| Binding format mismatch | Use list format, not dict (verified from hotkey_listener.py:64-68) |
| Outdated constant names | Use modern `NSEventModifierFlag*` names, not deprecated `NS*KeyMask` |
| Modifier event timing | State tracker ensures we detect exact transition moments |

## Notes

- NSEvent monitoring requires Accessibility permissions
- Monitor returns `None` if permissions denied - must handle gracefully
- Main thread not required for `addGlobalMonitorForEventsMatchingMask_handler_`
- CGEventTap is fallback if NSEvent proves unreliable in testing
