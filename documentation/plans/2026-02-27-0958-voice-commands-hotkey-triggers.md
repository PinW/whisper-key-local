# Voice Commands Phase 2: Hotkey Triggers

As a *user* I want **voice-triggered hotkeys** so I can send keyboard shortcuts hands-free by speaking a trigger phrase

## Background

Building on Phase 1 (shell command execution), this adds a second command type: sending global hotkey combinations. The infrastructure for simulating key presses already exists in `clipboard_manager.py` (paste hotkey, enter key) and `platform/windows/keyboard.py` (SendInput). We extend the commands config to support a `hotkey` action alongside the existing `run` action.

### Phase 1 config (shell only)
```yaml
commands:
  - trigger: "open browser"
    run: 'start chrome'
```

### Phase 2 config (shell + hotkeys)
```yaml
commands:
  - trigger: "open browser"
    run: 'start chrome'
  - trigger: "undo"
    hotkey: "ctrl+z"
  - trigger: "copy that"
    hotkey: "ctrl+c"
```

## Implementation Plan

### 1. Extend commands config format
- [ ] Add `hotkey` as an alternative to `run` in command definitions
- [ ] Validate that each command has exactly one of `run` or `hotkey`
- [ ] Add hotkey examples to `commands.defaults.yaml`

### 2. Hotkey sending via existing platform keyboard module
- [ ] Add `send_hotkey(hotkey_string)` method to `VoiceCommandManager`
- [ ] Reuse `platform/windows/keyboard.py` SendInput infrastructure
- [ ] Parse hotkey string (e.g., "ctrl+z") into modifier + key sequence
- [ ] Press modifiers down, press key, release key, release modifiers

### 3. Command dispatch
- [ ] Update `handle_transcription()` to check command type (`run` vs `hotkey`)
- [ ] Route to `execute_command()` or `send_hotkey()` accordingly

## Implementation Details

### Updated commands config format

```yaml
commands:
  # Shell commands
  - trigger: "open browser"
    run: 'start chrome'

  # Hotkey commands
  - trigger: "undo"
    hotkey: "ctrl+z"
  - trigger: "redo"
    hotkey: "ctrl+y"
  - trigger: "select all"
    hotkey: "ctrl+a"
  - trigger: "save"
    hotkey: "ctrl+s"
  - trigger: "copy"
    hotkey: "ctrl+c"
  - trigger: "paste"
    hotkey: "ctrl+v"
  - trigger: "switch window"
    hotkey: "alt+tab"
```

### Hotkey sending

The `platform/windows/keyboard.py` module already has `send_hotkey()` / key simulation via ctypes SendInput. The `VoiceCommandManager` calls into it directly:

```python
def handle_transcription(self, text):
    command = self.match_command(text)
    if not command:
        logger.info(f"No command matched for: {text}")
        return

    if 'run' in command:
        self._execute_shell(command['run'])
    elif 'hotkey' in command:
        self._send_hotkey(command['hotkey'])
```

### Files modified
- `src/whisper_key/voice_commands.py` — add hotkey dispatch and sending
- `src/whisper_key/commands.defaults.yaml` — add hotkey command examples

### Files created
None — builds on Phase 1 files

## Success Criteria

- [ ] Saying "undo" sends Ctrl+Z to the active window
- [ ] Saying "save" sends Ctrl+S to the active window
- [ ] Hotkey commands and shell commands coexist in the same config file
- [ ] Invalid hotkey strings in config are logged and skipped (don't crash)
- [ ] Modifier keys (ctrl, alt, shift, win) are properly pressed and released
