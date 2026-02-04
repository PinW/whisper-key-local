# NSEvent Hotkey Implementation for macOS

As a *mac user* I want **global hotkeys using NSEvent monitoring** so hotkeys work reliably and can support Fn key.

## Status: Implementation Complete, Testing In Progress

## Real App Hotkey Configuration

| Hotkey | Type | Purpose |
|--------|------|---------|
| `fn+ctrl` (default) | modifier-only | Toggle recording |
| `option` | modifier-only | Auto-enter (stop + enter) |
| `ctrl` | modifier-only | Stop-modifier (stop recording) |
| `esc` | traditional (keycode only) | Cancel recording |

**No conflicts exist** - no traditional hotkey shares modifiers with a modifier-only hotkey.

## Implementation

### Core Design

1. **NSEvent global monitor** - monitors `NSKeyDownMask` and `NSFlagsChangedMask`
2. **ModifierStateTracker** - tracks modifier transitions (press/release)
3. **Two event handlers:**
   - `_handle_flags_changed` → modifier-only hotkeys (ctrl+option, option, ctrl)
   - `_handle_key_down` → traditional hotkeys (esc)

### Modifier-Only Hotkeys

Fire immediately when exact modifiers match. Release callback fires when any required modifier is released.

```
Press ctrl → flags = ctrl (no match for ctrl+option)
Press option → flags = ctrl+option (MATCH! fire press callback, mark active)
Release option → flags = ctrl (required modifier released, fire release callback)
```

### Traditional Hotkeys

Fire when keycode AND modifiers match exactly.

```
Press esc → keycode=53, flags=0 (MATCH if binding has modifiers=0)
```

## Known Issues

### Issue 1: ESC Key Not Detected

**Symptom:** Pressing escape produces no debug output at all - the NSKeyDown event isn't reaching our handler.

**Possible causes:**
1. System captures escape before global monitor sees it
2. Touch Bar escape key behaves differently
3. Some apps/modes intercept escape globally

**Investigation needed:**
- Test with physical escape key vs Touch Bar
- Test with Terminal in foreground vs other apps
- Check if `addLocalMonitorForEventsMatchingMask` receives it (would confirm global vs local issue)

**Workaround:** Use alternative cancel hotkey if needed (e.g., `ctrl+.`)

### Issue 2: Modifier-Only vs Traditional Override

**Symptom:** `ctrl+option` fires before user can press space for `ctrl+option+space`.

**Resolution:** Not a problem in real app - no such conflict exists. The test script tests a scenario not used in production.

If future need arises, implement "pending" mechanism:
1. On modifier match, set pending instead of firing
2. On key down, check traditional bindings first
3. On modifier release or non-matching key, fire pending

## Files

| File | Purpose |
|------|---------|
| `platform/macos/hotkeys.py` | NSEvent-based implementation |
| `tools/test_nsevent_hotkey.py` | Standalone test script |

## Testing Checklist

- [x] Fn+Ctrl detected (modifier-only)
- [x] Ctrl+Option detected (modifier-only)
- [x] Release callback fires when modifier released
- [ ] ESC detected (needs investigation)
- [ ] Full app test on macOS
