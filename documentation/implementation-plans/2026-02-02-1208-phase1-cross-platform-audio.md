# Phase 1: Cross-Platform Audio Feedback

As a *developer* I want **audio feedback to work on both Windows and macOS** so the app can play sounds on either platform without code changes.

## Current State

- `audio_feedback.py` uses `winsound.PlaySound()` - Windows-only
- Plays start/stop/cancel sounds asynchronously via threading
- Sound files are WAV format in `assets/sounds/`
- `winsound.SND_ASYNC` flag handles non-blocking playback

## Implementation Plan

### Step 1: Add playsound3 dependency
- [x] Add `playsound3>=2.0` to pyproject.toml dependencies (no platform marker - use on both)
  - ✅ Added to dependencies list

### Step 2: Replace winsound with playsound3
- [x] Remove `import winsound`
- [x] Add `from playsound3 import playsound`
- [x] Update `_play_sound_file_async()` to use playsound3
  - ✅ Replaced winsound.PlaySound with playsound(path, block=False)

### Step 3: Test on Windows
- [x] Run `/test-from-wsl` to verify app starts
  - ✅ App starts successfully: "Application ready!"
- [ ] Manual test: verify start/stop/cancel sounds play correctly

## Implementation Details

**Current code:**
```python
import winsound

def _play_sound_file_async(self, file_path: str):
    def play_sound():
        winsound.PlaySound(file_path, winsound.SND_FILENAME | winsound.SND_ASYNC)
    threading.Thread(target=play_sound, daemon=True).start()
```

**New code:**
```python
from playsound3 import playsound

def _play_sound_file_async(self, file_path: str):
    def play_sound():
        playsound(file_path, block=False)
    threading.Thread(target=play_sound, daemon=True).start()
```

**Note:** playsound3's `block=False` handles async internally, but we keep the thread wrapper for consistency and error isolation.

## Files to Modify

| File | Changes |
|------|---------|
| `pyproject.toml` | Add playsound3 dependency |
| `src/whisper_key/audio_feedback.py` | Replace winsound with playsound3 |

## Success Criteria

- [x] App starts without import errors on Windows
- [ ] Start sound plays when recording begins
- [ ] Stop sound plays when recording ends
- [ ] Cancel sound plays when recording is cancelled
- [ ] No blocking or delays in audio playback
