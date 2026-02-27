# Voice Commands Phase 1: Shell Command Execution

As a *user* I want **voice-triggered shell commands** so I can run PowerShell commands hands-free by speaking a trigger phrase

## Background

Whisper Key currently transcribes speech to text and pastes it. This adds a second mode — "command mode" — where a different hotkey triggers recording, and the transcribed text is matched against user-defined trigger phrases that execute shell commands instead of pasting.

The flow mirrors the existing recording flow (hotkey → record → transcribe) but branches after transcription: instead of clipboard delivery, it matches the text against commands and runs the associated shell command.

### Current flow
```
Ctrl+Win → record → transcribe → paste text
```

### Target flow
```
Ctrl+G → record → transcribe → match trigger phrase → run shell command
```

## Implementation Plan

### 1. Commands config file and loader
- [ ] Create `src/whisper_key/commands.defaults.yaml` with example commands
- [ ] Add `VoiceCommandManager` class in new `src/whisper_key/voice_commands.py`
- [ ] On startup, check for `commands.yaml` in user app data dir (`%APPDATA%\whisperkey\`)
- [ ] If missing, copy `commands.defaults.yaml` as `commands.yaml`
- [ ] Load and parse commands into a lookup structure

### 2. Trigger phrase matching
- [ ] Implement `match_command(text)` — the public interface for all command matching (this method evolves over time; Phase 1 uses simple string containment, future phases swap in fuzzy/embedding/LLM matching)
- [ ] Inside `match_command`: normalize text (lowercase, strip punctuation), then check if any trigger phrase is contained within the transcription
- [ ] If multiple triggers match, pick the longest (most specific) one
- [ ] Return the best match (or None if nothing matches)

### 3. Shell command execution
- [ ] Add `execute_command(shell_command)` method to `VoiceCommandManager`
- [ ] Run via `subprocess.Popen(command, shell=True)` — user writes whatever shell syntax they want in their config
- [ ] Fire-and-forget (don't block the main thread, don't capture output)
- [ ] Log command execution, log errors if the process fails to launch

### 4. Command mode hotkey and state flow
- [ ] Add `command_hotkey: "ctrl+g"` to `hotkey` section in `config.defaults.yaml`
- [ ] Add command hotkey registration in `HotkeyListener` (same pattern as recording hotkey)
- [ ] Add `_command_hotkey_pressed()` callback that sets a "command mode" flag **and starts recording** (flag must be set at recording start, not stop — VAD timeout, max duration, and stop modifier all enter `_transcription_pipeline` independently)
- [ ] If already recording (normal or command mode), ignore the second hotkey (existing `can_start_recording()` check handles this)
- [ ] Add stop modifier support for command hotkey (same as recording)
- [ ] In `StateManager._transcription_pipeline()`, branch after transcription: if command mode → clear flag, match + execute; else → paste
- [ ] `_command_mode` flag is cleared when consumed (regardless of match result), so alternate stop paths (VAD, max duration) work correctly

### 5. Config validation
- [ ] Add `command_hotkey` validation in `ConfigValidator` (same hotkey string validation as `recording_hotkey`)
- [ ] Extend hotkey conflict detection to check `command_hotkey` against `recording_hotkey` and `auto_enter_combination`

### 6. Wire up in main.py
- [ ] Create `VoiceCommandManager` instance in `main()`
- [ ] Pass to `StateManager`
- [ ] Pass command hotkey config to `HotkeyListener`

## Implementation Details

### Commands config format (`commands.defaults.yaml`)

```yaml
# Voice Commands Configuration
# Each command maps a trigger phrase to a shell command
# Trigger phrases are matched against your speech (case-insensitive, fuzzy)

commands:
  - trigger: "open browser"
    run: 'start chrome'

  - trigger: "open notepad"
    run: 'start notepad'

  - trigger: "lock screen"
    run: 'rundll32.exe user32.dll,LockWorkStation'

  - trigger: "screenshot"
    run: 'snippingtool'
```

### State flow branching

The key change is in `StateManager._transcription_pipeline()`. Currently it always calls `clipboard_manager.deliver_transcription()`. With command mode, it checks a flag:

```python
# In _transcription_pipeline:
text = self.whisper_engine.transcribe_audio(audio_data)
if text:
    if self._command_mode:
        self._command_mode = False
        self.voice_commands.handle_transcription(text)
    else:
        self.clipboard_manager.deliver_transcription(text, use_auto_enter)
```

### Trigger matching approach

`match_command(text)` is the single entry point for all command matching. The internals evolve over time — Phase 1 starts simple, future phases swap in smarter matching without changing the interface.

```python
def match_command(self, text):
    normalized = self._normalize(text)  # lowercase, strip punctuation
    best_match = None
    for command in self.commands:
        trigger = self._normalize(command['trigger'])
        if trigger in normalized:
            if best_match is None or len(trigger) > len(self._normalize(best_match['trigger'])):
                best_match = command
    return best_match
```

Only checks if the trigger phrase appears within the spoken text (not the reverse — saying just "open" should not match "open browser"). Longest match wins when multiple triggers hit.

Future phases replace the matching internals with embedding similarity, fuzzy matching, or LLM-based intent extraction.

### Files modified
- `src/whisper_key/config.defaults.yaml` — add `command_hotkey` to hotkey section
- `src/whisper_key/hotkey_listener.py` — register command hotkey
- `src/whisper_key/state_manager.py` — command mode flag and branching
- `src/whisper_key/main.py` — instantiate and wire VoiceCommandManager

### Files created
- `src/whisper_key/voice_commands.py` — VoiceCommandManager class
- `src/whisper_key/commands.defaults.yaml` — default commands config

## Success Criteria

- [ ] Pressing Ctrl+G starts recording, releasing Ctrl stops recording (same as main hotkey)
- [ ] Saying a trigger phrase runs the associated shell command
- [ ] Saying something that doesn't match any trigger does nothing (logged to console)
- [ ] User feedback mirrors normal recording (same start/stop sounds), with different log messages (e.g., "Command matched: open browser" or "No command matched for: open browzer")
- [ ] `commands.yaml` is auto-created in user app data dir on first run
- [ ] Editing `commands.yaml` and restarting picks up changes
- [ ] Shell commands execute without blocking the UI
