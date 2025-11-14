# Audio Host Selection Plan

## Goals

1. Allow users to choose the PortAudio host API (e.g., WASAPI, MME).
2. Persist the chosen host so Whisper Key loads it on startup.
3. Filter the audio-source submenu to the currently selected host to keep the list focused.

## Proposed Changes

### Configuration

- Extend `config.defaults.yaml` with `audio.host` (default `WASAPI` on Windows, `None` elsewhere).
- Update `ConfigManager` to expose `get_audio_host()` / `update_audio_host(host_name)` helpers.
- Ensure migrations: if `audio.host` missing from user config, default applied automatically through existing merge logic.

### State Management

- `StateManager` should expose:
  - `get_available_audio_hosts()` → introspect `sd.query_hostapis()` and collect names.
  - `get_current_audio_host()` / `set_audio_host(host_name)` to track selection, update config, and trigger UI refresh.
- When host changes:
  - Persist to config via `ConfigManager.update_user_setting`.
  - Notify `SystemTray` so menus rebuild (similar to model/device changes).
  - Possibly refresh cached device list in `AudioRecorder` if needed.

### AudioRecorder

- Modify `get_available_audio_devices(host_filter: str | None = None)` to accept a host filter.
- If `host_filter` is provided, include only devices whose host API name matches (case-insensitive).
- Leave default behavior unchanged when filter is `None` so other callers (tests, CLI) still see all devices.

### System Tray UI

- Insert a top-level “Audio Host” menu before “Audio Source”.
- Populate it with radio items for each host returned by `StateManager.get_available_audio_hosts()`.
- Selecting a host updates the config/state and rebuilds the menu.
- The “Audio Source” submenu should call `state_manager.get_available_audio_devices(host_filter=current_host)` to show only relevant devices.
- Ensure current selections are indicated (checked radio items).

### Persistence & Startup

- During initialization, load `audio.host` from config and inform `AudioRecorder` / `StateManager`.
- If stored host isn’t available on the system (e.g., ASIO missing), gracefully fall back to default host (WASAPI or first available) and update config.

## Validation

- Manual test plan:
  1. Launch app, confirm “Audio Host” menu appears with available host APIs.
  2. Switch host, ensure menu refreshes and audio sources change.
  3. Restart app; previously selected host should be pre-selected.
  4. Verify loopback devices only appear when host supports them (e.g., WASAPI).
- Optional: add logging when host changes to aid troubleshooting.

