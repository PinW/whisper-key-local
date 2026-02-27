# Voice Commands

Voice command mode lets you trigger actions by speaking. Press **Alt+Win** (default) to start recording, speak a trigger phrase, then press the stop key. If the transcription matches a trigger, the associated action runs.

## Configuration

Voice commands are configured in `commands.yaml`, located in your config folder:
- **Windows:** `%APPDATA%\whisperkey\commands.yaml`
- **macOS:** `~/.whisperkey/commands.yaml`

You can open this folder from the system tray menu: **Open Config Folder**.

## Format

Each command has a **trigger** phrase and exactly one action: `run`, `hotkey`, or `type`.

```yaml
commands:
  # Send a keyboard shortcut
  - trigger: "undo"
    hotkey: "ctrl+z"

  # Deliver pre-written text
  - trigger: "my email"
    type: "user@example.com"

  # Run a shell command
  - trigger: "open notepad"
    run: 'notepad.exe'
```

| Field | Description |
|-------|-------------|
| **trigger** | Phrase to match (case-insensitive, punctuation ignored) |
| **run** | Shell command (`cmd.exe` on Windows, `/bin/sh` on macOS) |
| **hotkey** | Keyboard shortcut to send (e.g. `ctrl+z`, `win+left`) |
| **type** | Pre-written text to deliver to the active window |

## Matching

- Triggers are matched as substrings — saying "please open notepad" matches `"open notepad"`
- Longer triggers are checked first, so `"open notepad plus plus"` won't accidentally match `"open notepad"`
- First match wins

## Command Types

### Hotkey commands

Send keyboard shortcuts to the active window. Use `+` to combine keys.

```yaml
  - trigger: "undo"
    hotkey: "ctrl+z"
  - trigger: "select all"
    hotkey: "ctrl+a"
  - trigger: "snap left"
    hotkey: "win+left"
  - trigger: "show desktop"
    hotkey: "win+d"
```

### Type commands

Deliver pre-written text to the active window using the same method as transcription (clipboard paste or direct typing, depending on your `clipboard.delivery_method` setting).

If you stop recording with the **auto-send key** (Alt by default), Enter is sent after the text — useful for chat apps and terminals.

```yaml
  - trigger: "my email"
    type: "user@example.com"
  - trigger: "my address"
    type: "123 Main Street, City, State 12345"
```

### Shell commands

Run any shell command. The command runs asynchronously — it won't block the app.

```yaml
  - trigger: "open notepad"
    run: 'notepad.exe'
  - trigger: "open browser"
    run: 'start https://www.google.com'
  - trigger: "open downloads"
    run: 'explorer "%USERPROFILE%\Downloads"'
  - trigger: "lock screen"
    run: 'rundll32.exe user32.dll,LockWorkStation'
```

## Hotkey

The command hotkey and stop key are configured in your user settings (`user_settings.yaml`):
```yaml
hotkey:
  command_hotkey: "alt+win | macos: fn+command"
  stop_key: "ctrl | macos: fn"
  auto_send_key: "alt | macos: option"
```

- **stop_key** — stops recording and executes the matched command
- **auto_send_key** — same as stop key, but also sends Enter after `type` commands (ignored for `run` and `hotkey`)

Both keys are shared between transcription and command modes.
