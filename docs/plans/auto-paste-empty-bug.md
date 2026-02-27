# Bug Investigation: Auto-paste delivers empty text + newline

Related: [#21](https://github.com/PinW/whisper-key-local/issues/21)

## Known Facts

1. **Pin's bug**: Claude Code receives empty paste followed by a newline. Transcription is correct (printed to terminal). Only started after switching to GPU mode (custom CTranslate2 ROCm build). Happened 3 times since 2026-02-07.
2. **One occurrence**: transcription time was 1.3 seconds — not unusually fast.
3. **Issue #21 reporter** (@linnkoln): text doesn't paste at all. Fixed by increasing `key_simulation_delay` from 0.05 to 0.1. Standard build (NVIDIA/CPU). Affects "all apps".
4. **Issue #21 second user** (@N3M1X10): auto-paste "never works" in Warframe, "sometimes" fails elsewhere. Windows 11 24H2.
5. **Neither #21 user mentions auto_enter/newline** — unclear if they use auto_enter or not.
6. **`pyautogui.PAUSE`** (set to `key_simulation_delay`) applies AFTER each pyautogui call, not before.
7. **Entire pipeline is synchronous on the hotkey callback thread**: hotkey fires → `toggle_recording()` → `stop_recording()` → `_transcription_pipeline()` → `whisper_engine.transcribe_audio()` → `clipboard_manager.deliver_transcription()` → `execute_auto_paste()` → `send_enter_key()`. All on one thread.

## The Paste Sequence (clipboard_manager.py:88-109)

```
1. original = pyperclip.paste()         # save clipboard
2. pyperclip.copy(text)                 # write transcription to clipboard
3. pyautogui.hotkey('ctrl', 'v')        # simulate paste  ← PAUSE (50ms) after
4. print("Auto-pasted...")
5. pyperclip.copy(original)             # restore clipboard
6. time.sleep(key_simulation_delay)     # 50ms wait
--- back in deliver_transcription ---
7. pyautogui.press('enter')             # auto_enter      ← PAUSE (50ms) after
```

## What We Don't Know

- **Does Ctrl+V actually fire?** We assume it does because Enter fires (newline appears), but we have no proof. Both use pyautogui on the same thread, so if one works the other should too — unless something specific to `hotkey()` vs `press()` differs.
- **Does `pyperclip.copy(text)` succeed?** It returns no confirmation. It could silently fail if another process holds the clipboard lock (`OpenClipboard` fails).
- **Is the clipboard content correct at the moment Ctrl+V is processed by the target app?** Even if copy succeeds, the target app reads the clipboard asynchronously — it might read it after step 5 restores the original.
- **What is "empty"?** Is Claude Code receiving literally nothing, or the previous clipboard content?
- **Thread identity**: which thread does the hotkey callback run on? If it's a background thread without a Windows message pump, clipboard and key simulation behavior could differ from the main thread.

## Theories

### Theory A: Clipboard restore races the target app (fits #21 users)
Step 5 restores the clipboard almost immediately after step 3. The target app receives the Ctrl+V event asynchronously and reads the clipboard — if it reads after step 5, it gets the old content. Increasing `key_simulation_delay` helps because the PAUSE after step 3 gives the target app more time to read before the restore.

**Problem with this theory for Pin's bug**: the delay should only matter between steps 3→5. Pin's default delay is 0.05s. That's tight but it's the same as before GPU mode, and the bug only appeared after GPU.

### Theory B: `pyperclip.copy()` silently fails (clipboard lock contention)
Windows clipboard can only be opened by one thread/process at a time. If something (ROCm runtime thread? another process?) has the clipboard open when step 2 runs, `pyperclip.copy()` could silently fail. The old clipboard content stays, Ctrl+V pastes it (empty or previous), Enter fires on top.

**Why GPU-specific**: The custom CTranslate2 ROCm build spawns HIP runtime threads. If any of them interact with Windows clipboard or hold a system resource that blocks `OpenClipboard()`, this would be intermittent and GPU-only.

### Theory C: Thread context issues with pyautogui
The hotkey callback thread may not be ideal for `pyautogui.hotkey()`. On Windows, `SendInput` (used by pyautogui) requires the calling thread to not be blocked and the target window to be in foreground. If the hotkey listener thread has different properties than the main thread, key simulation could be unreliable.

**Why GPU-specific**: unclear. This would affect CPU mode too unless the GPU transcription somehow changes thread timing.

### Theory D: Hotkey release interference
The recording hotkey (e.g. Ctrl+Win) is released by the user around the same time the paste sequence runs. If the user hasn't fully released modifier keys when `pyautogui.hotkey('ctrl', 'v')` fires, the OS might see Ctrl+Win+V instead of Ctrl+V.

**Problem**: transcription takes 1.3s, so the user's fingers should be off the keys by then. Also not GPU-specific.

### Theory E: Two separate bugs
- #21 users: Theory A (clipboard restore race) — fixed by longer delay
- Pin: Theory B (clipboard lock) — different root cause, only appears with ROCm runtime threads

## Testing Plan

### 1. Add diagnostic logging to execute_auto_paste
- After `pyperclip.copy(text)`, read clipboard back with `pyperclip.paste()` and verify it matches
- Log the thread ID (`threading.current_thread()`)
- Log timestamps at each step (copy, paste, restore)
- Log whether `pyperclip.copy()` actually set the clipboard (read-back verification)

### 2. Test clipboard lock contention
- Before `pyperclip.copy(text)`, try `win32clipboard.OpenClipboard()` / `CloseClipboard()` directly to see if it fails (would confirm lock contention)
- Try adding a retry loop: if read-back doesn't match, retry the copy

### 3. Test without clipboard restore
- Set `preserve_clipboard: false` in config
- If the bug disappears, Theory A is confirmed (at least partially)

### 4. Test with increased delay
- Set `key_simulation_delay: 0.15` — does Pin's bug still occur?
- If it disappears, the root cause is timing-related (A), not lock-related (B)

### 5. Test on CPU mode
- Switch back to CPU (`device: cpu`) with same config
- If the bug disappears, it's GPU-specific (supports B or E)

### 6. Check if Enter actually fires vs Ctrl+V
- Temporarily disable auto_enter and test — does the empty paste still happen (just without the newline)?
- Or: add logging before/after each `pyautogui` call to confirm both fire

### 7. Check pyperclip implementation
- What does `pyperclip.copy()` use on this system? (`win32clipboard`? subprocess?)
- Does it raise on failure or silently fail?
