# Auto-Update on Startup

As a *user* I want **automatic update checks on startup** so I always run the latest version without manual effort.

## Background

The pyapp binary wraps a pip-installed package. Updates require running `whisper-key.exe self update` (pip upgrade) — but users don't know when a new version is available. The app should check PyPI on startup and offer to update before heavy initialization (model loading, audio, tray setup).

Dev versions (`X.Y.Z-dev`) skip the check entirely — developers manage their own installs.

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
- [ ] Call `check_for_updates()` after ConfigManager init, before component setup
- [ ] Skip when version ends in `-dev` (running from source)
- [ ] Skip when editable install detected (dev testing via pyapp)
- [ ] Skip when `--test` flag is set

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
def check_for_updates(config_manager):
    version = get_version()
    latest = fetch_latest_version()  # returns None on failure
    if not latest or not is_newer(latest, version):
        return

    if version.endswith("-dev") or is_editable_install():
        print(f"   ** Update available: {version} → {latest} (git pull to update)")
        return

    update_config = config_manager.get_update_config()
    update_config = config_manager.get_update_config()

    if update_config['mode'] == 'auto':
        run_update()
        restart_app()
        return

    # mode == 'prompt'
    choice = prompt_update(version, latest)
    if choice == UPDATE_NOW:
        run_update()
        restart_app()
    elif choice == ALWAYS_UPDATE:
        config_manager.update_user_setting('update', 'mode', 'auto')
        run_update()
        restart_app()
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
    print("Updating...")
    subprocess.run([sys.executable, "-m", "pip", "install", "--upgrade", "whisper-key-local"])

def restart_app():
    print("Restarting...")
    os.execv(sys.argv[0], sys.argv)
```

`os.execv` replaces the current process with a fresh one — no double-loading.

### Scope

| File | Changes |
|------|---------|
| `config.defaults.yaml` | Add `update` section |
| `config_manager.py` | Add `get_update_config()` |
| `update_checker.py` | New module — version check, prompt, update, restart |
| `main.py` | Call `check_for_updates()` after config, before components |

## Success Criteria

- [ ] Update prompt appears when PyPI has newer version
- [ ] "Update now" downloads update and restarts app with new version
- [ ] "Always keep up-to-date" sets mode to auto, updates, and restarts
- [ ] "Not now" skips and continues startup normally
- [ ] Auto mode updates silently without prompt on subsequent launches
- [ ] Dev versions and editable installs show non-blocking notice instead of prompt
- [ ] Offline / timeout doesn't block or delay startup noticeably (≤3s)
- [ ] `--test` flag skips check
