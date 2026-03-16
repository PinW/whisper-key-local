# Auto-Update on Startup

As a *user* I want **automatic update checks on startup** so I always run the latest version without manual effort.

## Background

Users don't know when a new version is available. The app should check PyPI on startup and offer to update before heavy initialization (model loading, audio, tray setup). Works for both pyapp binary and regular pip installs.

| Install method | Update mechanism | Restart |
|---|---|---|
| pyapp binary | pip upgrade (same as `self update`) | exit, user relaunches |
| `pip install` | pip upgrade | exit, user relaunches |
| source (`whisper-key.py`) | notice only ("git pull") | no action |

Dev versions (`X.Y.Z-dev`) and `--test` mode show a notice only — no prompt, no blocking.

## Current Startup Flow

```
main() →
  app.setup()
  argparse
  guard_against_multiple_instances()
  print("Starting Whisper Key...")
  ConfigManager()           ← config + logging
  setup all components      ← heavy init (whisper model, audio, tray)
  print("Whisper Key ready!")
  app.run_event_loop()
```

## Target Startup Flow

```
main() →
  app.setup()
  argparse
  guard_against_multiple_instances()
  print("Starting Whisper Key...")
  ConfigManager()           ← config + logging (needed for update settings)
  check_for_updates()       ← NEW: before heavy init
  setup all components
  print("Whisper Key ready!")
  app.run_event_loop()
```

## Implementation Plan

1. Add update config to defaults
- [ ] Add `update` section to `config.defaults.yaml`
- [ ] Add `get_update_config()` to `ConfigManager`

2. Create update checker module
- [ ] Create `src/whisper_key/update_checker.py`
- [ ] Implement PyPI version check via JSON API
- [ ] Implement update prompt using `terminal_ui.prompt_choice`
- [ ] Implement `self update` execution and app restart

3. Wire into main.py
- [ ] Call `check_for_updates(config_manager, test_mode=args.test)` after ConfigManager init, before component setup

4. Test
- [ ] Build pyapp exe and test update prompt flow
- [ ] Test auto mode (silent update)
- [ ] Test offline / timeout behavior
- [ ] Test dev version skips check

## Implementation Details

### Config defaults

```yaml
update:
  mode: prompt    # "prompt" = ask user, "auto" = update silently
```

### PyPI version check

Query `https://pypi.org/pypi/whisper-key-local/json` — returns JSON with `info.version` as the latest release. Use `urllib.request` (stdlib, no extra dependency). Timeout of 3 seconds.

### update_checker.py

```python
# Core function called from main.py
def check_for_updates(config_manager, test_mode=False):
    version = get_version()
    is_dev = version.endswith("-dev") or test_mode

    latest = fetch_latest_version()  # returns None on failure
    if not latest or not is_newer(latest, version):
        return

    if is_dev:
        print(f"   ** Update available: {version} → {latest} (git pull to update)")
        return

    update_config = config_manager.get_update_config()

    if update_config['mode'] == 'auto':
        run_update()
        return

    # mode == 'prompt'
    choice = prompt_update(version, latest)
    if choice == UPDATE_NOW:
        run_update()
    elif choice == ALWAYS_UPDATE:
        config_manager.update_user_setting('update', 'mode', 'auto')
        run_update()
```

### Version comparison

Use `packaging.version.Version` (already a transitive dependency via pip/setuptools) for proper semver comparison. Handles pre-release, post-release, etc.

### Update prompt (terminal_ui)

```
  ┌──────────────────────────────────────────┐
  │ Update available: 0.7.1 → 0.8.0         │
  │                                          │
  │ [1] Update now                           │
  │     Downloads and installs the update    │
  │                                          │
  │ [2] Always keep up-to-date               │
  │     Update now and auto-install future   │
  │     updates                              │
  │                                          │
  │ [3] Not now                              │
  │     Skip for this session                │
  └──────────────────────────────────────────┘

  Press a number to choose:
```

### Running the update

```python
def run_update():
    print("   Updating...")
    subprocess.run([sys.executable, "-m", "pip", "install", "--upgrade", "whisper-key-local"])
    # NOTE: GPU onboarding will add a post-update hook here to restore
    # AMD CT2 ROCm wheels (which get overwritten by the standard PyPI wheel)
    print("   Update installed. Please restart Whisper Key.")
    sys.exit(0)
```

Exits after update — avoids `os.execv` console flicker on Windows. User relaunches.

### Scope

| File | Changes |
|------|---------|
| `config.defaults.yaml` | Add `update` section |
| `config_manager.py` | Add `get_update_config()` |
| `update_checker.py` | New module — version check, prompt, update, restart |
| `main.py` | Call `check_for_updates()` after config, before components |

## Success Criteria

- [ ] Update prompt appears when PyPI has newer version
- [ ] "Update now" downloads update and exits for user to relaunch
- [ ] "Always keep up-to-date" sets mode to auto, updates, and exits
- [ ] "Not now" skips and continues startup normally
- [ ] Auto mode updates silently without prompt on subsequent launches
- [ ] Dev versions and `--test` mode show non-blocking notice instead of prompt
- [ ] Offline / timeout doesn't block or delay startup noticeably (≤3s)
