# Voice Commands

Voice command mode lets you run shell commands by speaking trigger phrases. Press **Alt+Win** (default) to record, speak a trigger phrase, then press the stop key to stop. If the transcription matches a trigger, the associated command runs.

## Configuration

Voice commands are configured in `commands.yaml`, located in your config folder:
- **Windows:** `%APPDATA%\whisperkey\commands.yaml`
- **macOS:** `~/Library/Application Support/whisperkey/commands.yaml`

You can open this folder from the system tray menu: **Open Config Folder**.

## Format

```yaml
commands:
  - trigger: "open notepad"
    run: 'notepad.exe'
  - trigger: "search google"
    run: 'start https://www.google.com'
```

Each command has:
- **trigger** — the phrase to match (case-insensitive, punctuation ignored)
- **run** — any shell command (`cmd.exe` on Windows, `/bin/sh` on macOS)

## Matching

- Triggers are matched as substrings — saying "please open notepad" matches `"open notepad"`
- Longer triggers are checked first, so `"open notepad plus plus"` won't accidentally match `"open notepad"`
- First match wins

## Examples

### Open applications
```yaml
  - trigger: "open notepad"
    run: 'notepad.exe'
  - trigger: "open calculator"
    run: 'calc.exe'
```

### Open websites
```yaml
  - trigger: "open browser"
    run: 'start https://www.google.com'
  - trigger: "open youtube"
    run: 'start https://www.youtube.com'
```

### Run desktop shortcuts
```yaml
  - trigger: "open spotify"
    run: 'start "" "%USERPROFILE%\Desktop\Spotify.lnk"'
```

### Run scripts
```yaml
  - trigger: "run backup"
    run: 'python C:\scripts\backup.py'
  - trigger: "deploy"
    run: 'powershell.exe -Command "& C:\scripts\deploy.ps1"'
```

### System commands
```yaml
  - trigger: "lock screen"
    run: 'rundll32.exe user32.dll,LockWorkStation'
  - trigger: "empty recycle bin"
    run: 'powershell.exe -Command "Clear-RecycleBin -Force"'
```

## Hotkey

The command hotkey and stop key are configured in your user settings (`user_settings.yaml`):
```yaml
hotkey:
  command_hotkey: "alt+win | macos: fn+command"
  stop_key: "ctrl | macos: fn"
```

The `stop_key` is shared between transcription and command modes.
