# Refactor Stop-With-Modifier to Explicit Stop/Auto-Send Keys

As a *user* I want **simple, explicit stop and auto-send keys** so I don't have to understand the confusing stop-with-modifier system.

## Background

The current `stop_with_modifier_enabled` system derives the stop key from the first modifier of the recording hotkey (e.g., `ctrl+win` → `ctrl` stops). This creates:
- Complex conflict resolution between stop-modifier and auto-enter keys
- Confusing config with `stop_with_modifier_enabled` boolean + implicit key derivation
- Special-case logic for when the stop-modifier overlaps with command hotkey

The fix: replace with two explicit config keys (`stop_key` and `auto_send_key`) that users configure directly. Recording/command hotkeys become start-only (no toggle).

## Current Architecture

```
config.defaults.yaml:
  stop_with_modifier_enabled: true    ← boolean flag
  auto_enter_enabled: true            ← boolean flag
  auto_enter_combination: "alt"       ← key

hotkey_listener.py:
  _extract_first_modifier(recording_hotkey) → derives stop key from hotkey
  toggle_recording() on standard hotkey press (starts AND stops)
  _resolve_hotkey_conflicts() → disables auto-enter if first modifier clashes

state_manager.py:
  toggle_recording() → stops if recording, starts if not
```

## Target Architecture

```
config.defaults.yaml:
  stop_key: "ctrl | macos: fn"        ← explicit key
  auto_send_key: "alt | macos: option" ← explicit key (replaces auto_enter)

hotkey_listener.py:
  stop_key from config directly (no derivation)
  start_recording() on standard hotkey press (start-only)
  simple conflict check: stop_key != auto_send_key

state_manager.py:
  start_recording() → public, start-only (no toggle)
```

## Implementation Plan

1. Config changes
- [x] `config.defaults.yaml`: remove `stop_with_modifier_enabled` and `auto_enter_enabled`
- [x] `config.defaults.yaml`: rename `auto_enter_combination` → `auto_send_key`
- [x] `config.defaults.yaml`: add `stop_key: "ctrl | macos: fn"` with updated comments
- [x] `config.defaults.yaml`: update `recording_hotkey` comment from "start/stop" → "start"

2. ConfigValidator refactor
- [ ] `config_manager.py`: remove `_validate_boolean('hotkey.stop_with_modifier_enabled')`
- [ ] `config_manager.py`: remove `_validate_boolean('hotkey.auto_enter_enabled')`
- [ ] `config_manager.py`: add `_validate_hotkey_string('hotkey.stop_key')`
- [ ] `config_manager.py`: rename `auto_enter_combination` → `auto_send_key` in validation
- [ ] `config_manager.py`: simplify `_resolve_hotkey_conflicts()` — just check stop_key != auto_send_key and neither equals a start hotkey

3. ConfigManager display methods
- [ ] `config_manager.py`: simplify `_get_stop_key()` — read `stop_key` config directly, no modifier extraction
- [ ] `config_manager.py`: update `print_stop_instructions_based_on_config()` — use `stop_key` and `auto_send_key` config names
- [ ] `config_manager.py`: update `print_command_stop_instructions()` — use `stop_key` config

4. StateManager refactor
- [ ] `state_manager.py`: remove `toggle_recording()`
- [ ] `state_manager.py`: make `_start_recording()` public as `start_recording()` with `can_start_recording()` guard and busy-state messages
- [ ] `system_tray.py`: remove dead `_tray_toggle_recording()` method (calls removed `toggle_recording`)

5. HotkeyListener refactor
- [ ] `hotkey_listener.py`: replace `stop_with_modifier_enabled` + `auto_enter_enabled` params with `stop_key` param
- [ ] `hotkey_listener.py`: rename `auto_enter_hotkey` → `auto_send_key`
- [ ] `hotkey_listener.py`: `_standard_hotkey_pressed()` calls `start_recording()` (not toggle)
- [ ] `hotkey_listener.py`: register `stop_key` directly (no `_extract_first_modifier` derivation)
- [ ] `hotkey_listener.py`: register `auto_send_key` with release callback (arming protection for `alt` in `alt+win`)
- [ ] `hotkey_listener.py`: remove `_extract_first_modifier()` method
- [ ] `hotkey_listener.py`: update `change_hotkey_config()` valid settings list

6. main.py wiring
- [ ] `main.py`: update `setup_hotkey_listener()` — pass `stop_key` and `auto_send_key` instead of old params

7. Documentation
- [ ] `documentation/voice-commands.md`: update stop-modifier reference (line 81) to describe `stop_key`

## Implementation Details

### Arming mechanism (preserved, simplified)

Single `keys_armed` flag (renamed from `modifier_key_released`):
- **Disarmed** when any start hotkey fires (recording_hotkey or command_hotkey)
- **Re-armed** when stop_key released OR auto_send_key released
- Both stop_key and auto_send_key check `keys_armed` before firing

This prevents false triggers when `ctrl` fires as part of `ctrl+win` or `alt` fires as part of `alt+win`.

### config.defaults.yaml — hotkey section

**Before:**
```yaml
  recording_hotkey: "ctrl+win | macos: fn+ctrl"
  stop_with_modifier_enabled: true
  auto_enter_enabled: true
  auto_enter_combination: "alt | macos: option"
  cancel_combination: "esc | macos: shift"
  command_hotkey: "alt+win | macos: fn+command"
```

**After:**
```yaml
  recording_hotkey: "ctrl+win | macos: fn+ctrl"
  stop_key: "ctrl | macos: fn"
  auto_send_key: "alt | macos: option"
  cancel_combination: "esc | macos: shift"
  command_hotkey: "alt+win | macos: fn+command"
```

### HotkeyListener.__init__ signature

**Before:**
```python
def __init__(self, state_manager, recording_hotkey, auto_enter_hotkey=None,
             auto_enter_enabled=True, stop_with_modifier_enabled=False,
             cancel_combination=None, command_hotkey=None):
```

**After:**
```python
def __init__(self, state_manager, recording_hotkey, stop_key,
             auto_send_key=None, cancel_combination=None, command_hotkey=None):
```

### HotkeyListener._setup_hotkeys — stop_key registration

**Before:**
```python
if self.stop_with_modifier_enabled:
    self.stop_modifier_hotkey = self._extract_first_modifier(self.recording_hotkey)
    if self.stop_modifier_hotkey:
        hotkey_configs.append({
            'combination': self.stop_modifier_hotkey,
            'callback': self._stop_modifier_hotkey_pressed,
            'release_callback': self._arm_stop_modifier_hotkey_on_release,
            'name': 'stop-modifier'
        })
```

**After:**
```python
hotkey_configs.append({
    'combination': self.stop_key,
    'callback': self._stop_key_pressed,
    'release_callback': self._arm_keys_on_release,
    'name': 'stop'
})

if self.auto_send_key:
    hotkey_configs.append({
        'combination': self.auto_send_key,
        'callback': self._auto_send_key_pressed,
        'release_callback': self._arm_keys_on_release,
        'name': 'auto-send'
    })
```

### StateManager — toggle_recording → start_recording

**Before:**
```python
def toggle_recording(self):
    was_recording = self.stop_recording(use_auto_enter=False)
    if not was_recording:
        if self.can_start_recording():
            self._start_recording()
        else:
            ...busy messages...
```

**After:**
```python
def start_recording(self):
    if self.can_start_recording():
        self._begin_recording()
    else:
        current_state = self.get_current_state()
        if self.is_processing:
            print("⏳ Still processing previous recording...")
        elif self.is_model_loading:
            print("⏳ Still loading model...")
        else:
            print(f"⏳ Cannot record while {current_state}...")
```

(`_start_recording` renamed to `_begin_recording` to avoid confusion with public `start_recording`)

### Conflict resolution simplification

**Before:** Extract first modifier, compare, conditionally disable auto-enter.

**After:**
```python
def _resolve_hotkey_conflicts(self, stop_key, auto_send_key, recording_hotkey, command_hotkey):
    if stop_key == auto_send_key:
        warn + clear auto_send_key
    if stop_key == recording_hotkey:
        warn + reset stop_key to default
    if command_hotkey == recording_hotkey:
        warn + clear command_hotkey  # (existing check, keep)
```

## Scope

| File | Changes |
|------|---------|
| `config.defaults.yaml` | Replace 3 fields with 2, update comments |
| `config_manager.py` | Simplify `_get_stop_key`, update print methods, simplify validator |
| `hotkey_listener.py` | New params, start-only hotkey, explicit stop/auto-send registration, remove extraction |
| `state_manager.py` | Remove `toggle_recording`, public `start_recording` |
| `system_tray.py` | Remove dead `_tray_toggle_recording()` method |
| `main.py` | Update `setup_hotkey_listener` wiring |
| `documentation/voice-commands.md` | Update stop-modifier reference to `stop_key` |

## Success Criteria

- [ ] `ctrl+win` starts recording (does NOT toggle/stop)
- [ ] `ctrl` stops recording and auto-pastes
- [ ] `alt` stops recording and auto-pastes with ENTER
- [ ] `alt+win` starts command mode
- [ ] `ctrl` stops command mode and executes command
- [ ] Pressing `ctrl+win` doesn't falsely trigger `ctrl` stop (arming works)
- [ ] Pressing `alt+win` doesn't falsely trigger `alt` auto-send (arming works)
- [ ] Console instructions show correct keys
- [ ] Config validation catches stop_key == auto_send_key conflict
