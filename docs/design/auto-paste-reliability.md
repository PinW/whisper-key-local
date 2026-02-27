# Auto-Paste Reliability

Prior investigation: @plans/auto-paste-empty-bug.md

## Problem

Auto-paste fails intermittently. The transcription is correct (printed to terminal), but the target app receives empty text followed by a stray Enter. Related: [#21](https://github.com/PinW/whisper-key-local/issues/21)

## Observations

- **Pin's bug**: Only started after switching to GPU mode (ROCm). One occurrence had 1.3s transcription time — not unusually fast. Claude Code receives empty paste + newline.
- **#21 reporter** (@linnkoln): Text doesn't paste at all. Fixed by increasing `key_simulation_delay` from 0.05 to 0.1. Affects "all apps".
- **#21 second user** (@N3M1X10): Auto-paste "never works" in Warframe, "sometimes" fails elsewhere. Windows 11 24H2.

## The Paste Sequence (`clipboard_manager.py:88-109`)

```
1. original = pyperclip.paste()         # save clipboard
2. pyperclip.copy(text)                 # write transcription
3. pyautogui.hotkey('ctrl', 'v')        # simulate paste  ← PAUSE (50ms) after
4. print("Auto-pasted...")
5. pyperclip.copy(original)             # restore clipboard
6. time.sleep(key_simulation_delay)     # 50ms wait
--- back in deliver_transcription ---
7. pyautogui.press('enter')             # auto_enter      ← PAUSE (50ms) after
```

## Root Cause Analysis

There are likely **two separate bugs** producing the same symptom:

### Bug 1: Clipboard Restore Race (affects #21 users)

Step 3 puts keystrokes into the Windows input queue. The target app processes them asynchronously through its message loop, then calls `GetClipboardData()`. If step 5 runs before the target app reads the clipboard, it gets the restored (old/empty) content.

The only delay between steps 3→5 is `pyautogui.PAUSE` (50ms). Increasing `key_simulation_delay` to 0.1 fixes this for #21 users, confirming a timing race.

### Bug 2: Clipboard Lock Contention (affects GPU/ROCm mode)

Pin's bug occurred at 1.3s transcription time — 50ms should be plenty for the race window. This suggests a different cause: `pyperclip.copy(text)` at step 2 may **silently fail** due to clipboard lock contention.

Windows clipboard can only be opened by one process/thread at a time (`OpenClipboard`). The custom CTranslate2 ROCm build spawns HIP runtime threads — if any of them hold system resources that block `OpenClipboard()`, `pyperclip.copy()` could fail silently. The old clipboard content stays, Ctrl+V pastes it (empty or stale), and Enter fires on the empty result.

### Shared Symptom

In both cases, `auto_enter` sends Enter to an empty input field — in Claude Code this inserts a newline rather than submitting.

## Constraint: Clipboard Reads Are Invisible

Windows provides no API to detect when another process *reads* the clipboard. `GetClipboardSequenceNumber` tracks *writes* only. `AddClipboardFormatListener` fires on *changes* only. There is no reliable way to confirm "the target app has consumed our paste" without OS-level hooks.

This means any clipboard-based approach is inherently timing-dependent. The only way to eliminate the race entirely is to not use the clipboard for text delivery.

---

## Options

### Option A: Direct Text Injection

Bypass the clipboard entirely. Use `SendInput` with `KEYEVENTF_UNICODE` to type characters directly into the active window.

**Windows:** `SendInput` with `KEYEVENTF_UNICODE` via ctypes (or pynput's `Controller.type()`). Each character is injected as a synthetic keystroke. The OS translates it to `WM_CHAR` messages.

**macOS:** `CGEventKeyboardSetUnicodeString` — less reliable than Windows, some apps ignore the Unicode payload. Clipboard + Cmd+V remains safest on macOS.

**Flow:**
```
1. keyboard.type_text(text)    # SendInput KEYEVENTF_UNICODE per character
2. (clipboard never touched)
```

| Dimension | Assessment |
|-----------|------------|
| Race condition | **Impossible** — clipboard not involved |
| Clipboard preserved | **Naturally** — never touched |
| Reliability | High on Windows, lower on macOS |
| Speed | Fast for typical transcriptions (<500 chars). ~1ms per char |
| Unicode | Full support, including emoji via UTF-16 surrogate pairs |
| Limitations | Blocked by UIPI (elevated target windows). Newlines and tabs need `VK_RETURN`/`VK_TAB` handling. Some apps handle paste differently from typing (rich text editors may apply different formatting). Anti-cheat may block injected input |

**Platform impact:** New `type_text()` function in `platform/windows/keyboard.py` and `platform/macos/keyboard.py`. macOS implementation would likely fall back to clipboard + Cmd+V for reliability.

### Option B: Deferred Clipboard Restore

Keep clipboard-based paste but move the restore to a background timer with a generous delay.

**Flow:**
```
1. pyperclip.copy(text)
2. keyboard.send_hotkey('ctrl', 'v')
3. return immediately (paste is "done")
4. (background thread) sleep(500ms), then pyperclip.copy(original)
```

| Dimension | Assessment |
|-----------|------------|
| Race condition | **Virtually eliminated** — 500ms is 10x the worst observed failure window |
| Clipboard preserved | Yes, after ~500ms delay |
| Reliability | High — clipboard paste is universal |
| Limitations | Still timing-based (a very slow app could theoretically fail). If user pastes something else within 500ms, their paste gets overwritten by the restore. Two concurrent transcriptions could conflict |

**Variant — Restore on next recording start:** Instead of a timer, restore the original clipboard when the user presses the hotkey to start the next recording. Guarantees the paste completed because the user has moved on. Downside: clipboard holds transcription indefinitely if user doesn't record again.

### Option C: No Clipboard Restore

Remove the restore step entirely. The transcription stays in the clipboard after paste.

**Flow:**
```
1. pyperclip.copy(text)
2. keyboard.send_hotkey('ctrl', 'v')
3. (done — clipboard retains transcription)
```

| Dimension | Assessment |
|-----------|------------|
| Race condition | **Impossible** — no restore to race against |
| Clipboard preserved | **No** — `preserve_clipboard` feature is removed |
| Reliability | Highest — simplest possible flow |
| Limitations | Breaks `preserve_clipboard` for users who rely on it. User's clipboard always contains last transcription |

### Option D: Clipboard Paste with Integrity Check + Adaptive Delay

Paste via clipboard but poll the clipboard in a loop to ensure our content is still there before restoring.

**Flow:**
```
1. pyperclip.copy(text)
2. keyboard.send_hotkey('ctrl', 'v')
3. loop (every 20ms, up to 500ms max):
     - read clipboard
     - if content != our text: something else wrote to clipboard, abort restore
4. pyperclip.copy(original)
```

| Dimension | Assessment |
|-----------|------------|
| Race condition | **Reduced** — generous max wait. Integrity check prevents clobbering if another app writes to clipboard during the wait |
| Clipboard preserved | Yes |
| Reliability | Good, still timing-based but with safety checks |
| Limitations | Polling adds CPU overhead. Still can't confirm target app read the clipboard — we only confirm nothing else *wrote* to it. 500ms max is heuristic |

---

## Recommendation

**Implement Option A (direct text injection) as the primary delivery method, with clipboard paste as the fallback.**

Rationale:
- It's the only option that structurally eliminates **both bugs** — the clipboard restore race (Bug 1) AND clipboard lock contention (Bug 2)
- Clipboard is naturally preserved without any save/restore logic
- The platform abstraction layer already exists — add `type_text()` alongside `send_key()` and `send_hotkey()`
- On macOS where direct injection is less reliable, keep clipboard + Cmd+V (the race is less severe there due to different message dispatch)
- Clipboard paste remains available as a config option for apps that need it (e.g., rich text paste) — pair with Option B (deferred restore) when used

### Suggested Config

```yaml
clipboard:
  # How text is delivered to the active window
  # "type" = direct text injection (no clipboard involvement)
  # "paste" = clipboard + Ctrl+V (traditional, universal compatibility)
  delivery_method: type

  # (only applies when delivery_method is "paste")
  preserve_clipboard: true
  clipboard_restore_delay: 0.5
```

### Implementation Scope

| File | Change |
|------|--------|
| `platform/windows/keyboard.py` | Add `type_text()` using ctypes `SendInput` + `KEYEVENTF_UNICODE` |
| `platform/macos/keyboard.py` | Add `type_text()` — likely clipboard+Cmd+V fallback |
| `clipboard_manager.py` | Route through `keyboard.type_text()` or clipboard-paste based on config |
| `config.defaults.yaml` | Add `delivery_method`, `clipboard_restore_delay` |
| `config_manager.py` | Wire up new settings |
