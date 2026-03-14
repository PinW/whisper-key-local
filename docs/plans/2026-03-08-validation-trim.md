# Validation Trim

## Overview

Strip `ConfigValidator` down to only the validations that prevent broken behavior. Mutations that the validator performs (hotkey lowercasing, `audio.host` null-to-WASAPI) create false overrides when diffing config against the defaults baseline. Moving mutations to consumers and removing redundant checks fixes this.

## Problem

The validator does three things that hurt the overlay config model:
1. **Mutates values** (`audio.host: null` -> `"WASAPI"`, hotkey `.lower().strip()`) — creates diff against defaults baseline, producing false user overrides
2. **Validates things YAML already handles** (10 boolean checks) — YAML parses `true`/`false` natively
3. **Validates things consumers already handle** (enum checks, clipboard delays) — bad values fail with clear errors at the component that uses them

## Changes

### 1. `config_manager.py` — replace `ConfigValidator` class with `fix_config()` function

Delete the `ConfigValidator` class (lines 388-529). Replace with a module-level function (~25 lines):

```python
def fix_config(config, default_config, logger):
    # Keep these helpers as nested or module-level functions:
    #   _get_config_value_at_path, _set_config_value_at_path, _set_to_default

    # audio.max_duration
    _validate_numeric_range(config, default_config, 'audio.max_duration', min_val=0)

    # VAD thresholds (bad values here = silent malfunction, no consumer error)
    _validate_numeric_range(config, default_config, 'vad.vad_onset_threshold', min_val=0.0, max_val=1.0)
    _validate_numeric_range(config, default_config, 'vad.vad_offset_threshold', min_val=0.0, max_val=1.0)
    _validate_numeric_range(config, default_config, 'vad.vad_min_speech_duration', min_val=0.001, max_val=5.0)
    _validate_numeric_range(config, default_config, 'vad.vad_silence_timeout_seconds', min_val=1.0, max_val=36000.0)

    # Hotkey conflicts (prevents unusable app)
    stop_key = _get_config_value_at_path(config, 'hotkey.stop_key')
    auto_send_key = _get_config_value_at_path(config, 'hotkey.auto_send_key')
    recording_hotkey = _get_config_value_at_path(config, 'hotkey.recording_hotkey')
    command_hotkey = _get_config_value_at_path(config, 'hotkey.command_hotkey')
    _resolve_hotkey_conflicts(config, default_config, stop_key, auto_send_key, recording_hotkey, command_hotkey, logger)

    return config
```

**Removed** (34 calls total):
- 10x `_validate_boolean` (`auto_paste`, `paste_preserve_clipboard`, `type_also_copy_to_clipboard`, `vad_precheck_enabled`, `vad_realtime_enabled`, `log_transcriptions`, `audio_feedback.enabled`, `transcription_complete_enabled`, `system_tray.enabled`, `voice_commands.enabled`) — YAML parses bools natively
- 5x `_validate_enum` (`whisper.device`, `audio.channels`, 2x logging levels, `clipboard.delivery_method`) — bad values fail clearly at consumer
- 6x `_validate_numeric_range` for clipboard delays — harmless if wrong
- 5x `_validate_hotkey_string` — `hotkey_listener.py` already does `.lower().strip()`
- `_validate_audio_host` / `_get_platform_default_audio_host` — moved to consumer (see below)
- `platform_keyboard.validate_delivery_method()` call — moved to consumer (see below)

**Kept** (6 calls):
- `_validate_numeric_range` for `audio.max_duration` (1 call)
- `_validate_numeric_range` for 4 VAD settings (4 calls)
- `_resolve_hotkey_conflicts` (1 call)

**Kept helpers** (as module-level functions):
- `_get_config_value_at_path` — used by `fix_config` and `_resolve_hotkey_conflicts`
- `_set_config_value_at_path` — used by `_resolve_hotkey_conflicts`
- `_set_to_default` — used by `_resolve_hotkey_conflicts` and `_validate_numeric_range`
- `_validate_numeric_range` — 5 calls remain
- `_resolve_hotkey_conflicts` — kept as-is

**Deleted helpers:**
- `_validate_boolean`
- `_validate_enum`
- `_validate_hotkey_string`
- `_validate_audio_host`
- `_get_platform_default_audio_host`

Update `ConfigManager` references:
- Line 97: delete `self.validator = ConfigValidator(self.logger)`
- Lines 150, 172, 214: change `self.validator.fix_config(...)` to `fix_config(..., self.logger)`
- Simplify import: `from .platform import IS_MACOS, keyboard as platform_keyboard` → `from .platform import IS_MACOS`

### 2. `state_manager.py` — no changes needed for `audio.host`

`_initialize_audio_host()` already resolves `null` to WASAPI via `_resolve_audio_host` → `_preferred_platform_host`. The validator's `_validate_audio_host` was doing the same thing redundantly. Removing the validator's version is sufficient.

The auto-persist of fallback device IDs was already removed in a prior commit on this branch.

### 3. `clipboard_manager.py` — absorb `validate_delivery_method()`

In `ClipboardManager.__init__`, after setting `self.delivery_method`, add the platform validation:

```python
self.delivery_method = keyboard.validate_delivery_method(delivery_method)
```

This replaces the validator's call at config_manager.py line 464. The `from .platform import keyboard` import already exists in clipboard_manager.py.

## Files Changed

| File | Change |
|------|--------|
| `config_manager.py` | Replace `ConfigValidator` class with `fix_config()` function, simplify platform import |
| `clipboard_manager.py` | Add `validate_delivery_method()` call in `__init__` |

2 files. `state_manager.py` and `audio_recorder.py` unchanged.

## Impact on Overlay Config

Before: the defaults baseline runs through `fix_config` which mutates `audio.host: null` → `"WASAPI"` and lowercases hotkeys. These mutations mean the baseline differs from raw defaults, and any user config that matches the mutation also appears as a "no difference" — but if the mutation is removed later, old user files break.

After: `fix_config` only resets bad numeric ranges and resolves hotkey conflicts. No mutations that alter default-matching values. The defaults baseline stays clean, and `_compute_overrides` produces accurate diffs.
