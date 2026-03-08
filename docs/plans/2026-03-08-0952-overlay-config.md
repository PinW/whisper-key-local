# Overlay Config Implementation Plan

## Overview

Switch from "full-copy" config to an "overlay" pattern where the user settings file only contains values the user explicitly changed. Defaults live solely in `config.defaults.yaml` and evolve freely with app updates.

## Problem

Today, `user_settings.yaml` is a full clone of `config.defaults.yaml`. This causes:
- Users can't tell what they customized vs what's a default
- Updated defaults don't reach existing users (their file has the old value baked in)
- Auto-updates can't safely evolve defaults without overwriting user choices

## Design

### Core Principle
`user_settings.yaml` = **only overrides**. Everything else comes from defaults at load time.

### First Run
Instead of `shutil.copy2(defaults, user_settings)`, generate a commented starter file:

```yaml
# Whisper Key - User Settings
# Only uncommented values override defaults.
# See config.defaults.yaml for all available options.
#
# whisper:
#   model: tiny
#   device: cpu
```

### Load Flow (unchanged conceptually)
```
config.defaults.yaml  →  deep_merge(defaults, user_overrides)  →  validate  →  self.config
```

The merge already works correctly for sparse user files — this is just removing the full-copy step.

### Save Flow (changed)
Only write user-changed values to `user_settings.yaml`, not the full merged config.

Track which values differ from defaults and persist only those.

### Config Versioning
Add `_config_version: 1` to `config.defaults.yaml`. This enables future migrations.

- Not a user-facing setting — prefixed with `_` and excluded from validation
- On load, compare user file version to defaults version
- If user version < defaults version, run sequential migrations
- Store migrations as functions: `_migrate_v1_to_v2(user_config)`

## Changes

### 1. `config.defaults.yaml` — add version key

Add at the top of the file, before all sections:

```yaml
_config_version: 1
```

### 2. `config_manager.py` — overlay load/save

#### `_ensure_user_settings_exist()`
Replace `shutil.copy2` with generating a minimal starter file containing only `_config_version: 1` and commented examples.

#### `_load_config()`
- Load defaults and user file as today
- Run migrations if `user._config_version < defaults._config_version`
- Deep merge (already works with sparse user config)
- Validate merged config (unchanged)
- **Remove**: the `save_config_to_user_settings_file()` call after merge

#### `save_config_to_user_settings_file()` → `_save_user_overrides()`
Rename and change to diff-based save:
- Compare `self.config` against `self.default_config` (store defaults as instance var)
- Build a dict of only the values that differ
- Always include `_config_version`
- Write only the diff to `user_settings.yaml`

#### `update_user_setting()`
- Update `self.config` as today
- Call `_save_user_overrides()` instead of `save_config_to_user_settings_file()`

### 3. `config_manager.py` — migration framework

Add a migrations list:

```python
MIGRATIONS = [
    # (from_version, to_version, migration_function)
    # (1, 2, _migrate_v1_to_v2),
]
```

`_run_migrations(user_config, user_version, target_version)`:
- Run each applicable migration in order
- Update `_config_version` in user config
- Save after migrations complete

Migrations are added as needed in future PRs — this PR just sets up the framework with an empty list.

### 4. `config_manager.py` — diff helper

```python
def _compute_overrides(config, defaults):
    overrides = {}
    for key, value in config.items():
        if key not in defaults:
            continue
        if isinstance(value, dict) and isinstance(defaults[key], dict):
            nested = _compute_overrides(value, defaults[key])
            if nested:
                overrides[key] = nested
        elif value != defaults[key]:
            overrides[key] = value
    return overrides
```

### 5. Existing user migration (one-time)

On first load after this change, existing users will have a full-copy `user_settings.yaml` without `_config_version`. Handle this:

- If `_config_version` is missing, treat as version 0
- Migration v0→v1: load the full file, diff against defaults, keep only overrides, write back
- This automatically slims existing user files down to just their customizations

## Data Flow

```
BEFORE (full copy):
  defaults ──copy──→ user_settings.yaml (500 lines, all values)
  load: defaults + user_settings → merge (user wins on everything) → validate → save all back

AFTER (overlay):
  defaults ──starter──→ user_settings.yaml (5 lines, commented examples)
  load: defaults + user_overrides → merge (defaults fill gaps) → validate
  save: diff(config, defaults) → user_settings.yaml (only changed values)
```

## Files Changed

| File | Change |
|------|--------|
| `config.defaults.yaml` | Add `_config_version: 1` |
| `config_manager.py` | Overlay load/save, migration framework, diff helper, v0→v1 migration |

2 files. The merge and validation logic is mostly unchanged — this is primarily about what gets written to the user file.

## Edge Cases

- **User manually adds a value equal to default**: gets stripped on next save (harmless, value doesn't change)
- **Platform values** (`"x | macos: y"`): diff runs against pre-resolved defaults, so platform resolution still works correctly
- **Empty user file**: deep merge returns pure defaults (already works)
- **Corrupt user file**: existing error handling falls back to defaults (unchanged)
