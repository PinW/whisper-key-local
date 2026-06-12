# Terminal Tab Title with Animated Status

As a *user running `wk` in a terminal* I want **the tab title to show whisper-key's recording/processing status with an animated icon** so I can see what the app is doing at a glance, the same way Claude Code uses `✻` animation in its tab.

## Background

WezTerm, Windows Terminal, iTerm2, etc. let a foreground process claim its tab title via the OSC 0 escape sequence (`ESC ] 0 ; <title> BEL`). `main.py:206` already emits a static `Whisper Key` title at startup, so the mechanism works — this plan extends it to mirror the application's three runtime states with animation.

The system tray already has the same three-state model (`idle` / `recording` / `processing`) and is updated from 7 sites in `state_manager.py`. The terminal title needs to ride alongside those existing state transitions, not invent its own.

### Source proposal
`~/wezterm/WHISPER_KEY_OSC.md` — describes the OSC 0 mechanism and notes that any terminal-side wrapper hack (e.g. shell binding that pre-sets title) should be removed once the app sets its own title.

## States and animation design

| State | Frames | Frame interval | Notes |
|-------|--------|---------------|-------|
| `idle` | `🎤 whisper key` | static (no ticking) | one-shot emit, animation thread sleeps long |
| `recording` | `🔴 whisper key`, `   whisper key` | 500 ms | flashing red dot — slow pulse like a hardware REC LED |
| `processing` | `●∙∙ whisper key`, `∙●∙ whisper key`, `∙∙● whisper key`, `∙●∙ whisper key` | 200 ms | one dot bouncing across 3 positions; two-dot variant left as a tunable alternative below |

Frame sequences are defined as plain lists in the module so they're trivial to tweak. Two-dot ping-pong alternative for `processing` (user can swap in if preferred):

```
●∙∙∙   whisper key
∙●∙∙   whisper key
∙∙●∙   whisper key
∙∙∙●   whisper key
∙∙●∙   whisper key
∙●∙∙   whisper key
```

Constraint: keep title length stable across frames (pad with spaces) so the tab width doesn't flicker on terminals that auto-size tabs.

## Architecture

### New module: `src/whisper_key/terminal_title.py`

Single `TerminalTitle` class. Cross-platform — OSC 0 works the same on macOS/Linux/Windows (Windows 10+ console with VT mode enabled, which `console.setup()` already handles). No platform abstraction needed.

```
TerminalTitle
├── __init__()         → checks sys.stdout.isatty(); if False, becomes a no-op
├── start()            → emits idle frame, spawns daemon thread
├── update_state(s)    → swaps state under lock, kicks tick event to wake thread
├── stop()             → signals stop, joins thread, optional title-clear emit
└── _animation_loop()  → wait(interval) → emit_frame → tick++; wakes on state change
```

Threading model:
- One daemon thread (`_animation_thread`).
- `_tick_event = threading.Event()` lets `update_state()` interrupt the sleep so a state change reflects immediately rather than after the current frame's interval.
- `_state_lock` protects `_state` and `_frame_index`.
- Per-state interval comes from a dict; `idle` uses a long interval (e.g. 60s) so the thread effectively sleeps until the next state change.

TTY check: `sys.stdout.isatty()` once at construction. If False, every public method is a no-op. This covers pyapp/exe builds launched without a console, redirected stdout, and CI.

### Integration points

`main.py`:
- Remove the inline `sys.stdout.write("\033]0;Whisper Key\007")` at line 206.
- Construct `TerminalTitle()` after `console.setup()`.
- Pass it to `StateManager` (new constructor arg).
- Call `terminal_title.start()` once components are ready (alongside `system_tray.start()`).
- Call `terminal_title.stop()` in `shutdown_app()`.

`state_manager.py`:
- Add `terminal_title` parameter, wrap with `OptionalComponent` (mirrors `system_tray` / `audio_feedback`).
- Add `self.terminal_title.update_state(...)` next to each of the 7 existing `self.system_tray.update_state(...)` calls. Same state strings — no translation.

The `OptionalComponent` wrapper means if `TerminalTitle` is disabled (non-TTY), every call is a silent no-op without conditionals at each call site.

## Implementation Plan

1. Create `terminal_title.py`
- [x] `TerminalTitle` class with `start`, `update_state`, `stop` methods
  - ✅ Implemented per sketch; dropped dead `model_loading` frame entries (state strings mirror tray's 3 states)
- [x] TTY detection via `sys.stdout.isatty()` — disabled-mode is full no-op
  - ✅ Also guards `sys.stdout is None` (noconsole builds) and closed-stdout `ValueError`/`OSError` in constructor
- [x] Frame tables: `_FRAMES = {"idle": [...], "recording": [...], "processing": [...]}`
- [x] Per-state intervals: `_INTERVALS = {"idle": 60.0, "recording": 0.5, "processing": 0.2}`
- [x] `_emit(title)` helper: writes `\033]0;<title>\007` and flushes stdout
  - ✅ Self-stops the animation loop if stdout dies mid-run (verified by test)
- [x] Animation thread loop: read state under lock, emit frame, advance index, wait on `_tick_event` with per-state timeout, clear event
  - ✅ Frame selection under lock, I/O outside lock
- [x] `update_state()` swaps state, resets frame index to 0, sets `_tick_event` to wake the loop
- [x] `stop()` sets stop+tick events, joins with short timeout (≤1s), optionally emits a final blank `\033]0;\007` to let the shell reclaim the title
  - ✅ Tested with fake TTY: frame sequences, state transitions, blank-title emit, non-TTY no-op all verified

2. Wire into main.py
- [x] Delete the inline OSC write at `main.py:206`
  - ✅ Replaced by one-shot idle emit in `TerminalTitle.__init__` so the title still appears instantly at launch (before model load)
- [x] Import and instantiate `TerminalTitle` after `console.setup()` / `app.setup()`
- [x] Pass to `StateManager` constructor (new kwarg)
- [x] Call `terminal_title.start()` after `system_tray.start()`
- [x] Call `terminal_title.stop()` from `shutdown_app()`
  - ✅ Moved to `StateManager.shutdown()` next to `system_tray.stop()` — symmetric component ownership, no `shutdown_app` signature change

3. Wire into state_manager.py
- [x] Add `terminal_title` constructor parameter, wrap with `OptionalComponent`
- [x] Add `self.terminal_title.update_state(...)` next to each of the 7 existing tray `update_state` call sites:
  - ✅ Implemented as `_update_ui_state()` helper fanning out to tray + title; all 7 sites converted to call it
  - `cancel_active_recording` → `idle`
  - `start_command_recording` → `recording`
  - `_begin_recording` → `recording`
  - `_transcription_pipeline` start → `processing`
  - `_transcription_pipeline` finally (no pending) → `idle`
  - `set_model_loading(True)` → `processing`
  - `set_model_loading(False)` → `idle`

4. Cross-platform sanity
- [x] Verify Windows Terminal renders the OSC sequence (existing `console.setup()` already enables VT — no extra work expected)
  - ✅ App startup from Windows verified clean; interactive rendering check pending user test
- [ ] Verify legacy `cmd.exe` / conhost gracefully ignores it (no stray bytes shown). If garbage appears, gate emission behind `console.supports_vt()` or similar
- [x] No platform-specific code expected; single module covers all OSes

5. Manual testing
- [x] WezTerm (WSL): launch `wk`, observe idle title
  - ✅ Iterated extensively with user; final design: bare `Whisper Key` idle, 🔴 blink 1.5s/1.0s, animations user-configurable (default static)
- [x] Hold/press hotkey: title flashes red dot
  - ✅ Verified; braille-blank padding fixes leading-whitespace trim shifting text on blink-out
- [x] Release hotkey: title animates during transcription, returns to idle when done
- [ ] Switch model from tray → title shows processing animation during model load
- [ ] Cancel mid-recording → title returns to idle without a frame stuck on red
- [ ] Ctrl+C exit → title clears (or shell reclaims it on next prompt)
- [ ] Windows Terminal: same checks as above
- [x] Pipe stdout to file (`wk > out.log`): no escape sequences appear in the log (TTY check works)
  - ✅ Verified: captured startup output contains zero OSC bytes (master leaked `]0;Whisper Key` here)

6. Cleanup
- [x] If a wezterm.lua binding exists that pre-sets the title via `printf "\033]0;..."`, remove it (none found in current `~/.config/wezterm/wezterm.lua` — skip if absent)
- [x] Remove the now-superseded static `sys.stdout.write("\033]0;Whisper Key\007")` line in `main.py` (covered in phase 2)

## Code sketches

### terminal_title.py (skeleton)

```python
import sys
import threading

_FRAMES = {
    "idle":       ["🎤 whisper key"],
    "recording":  ["🔴 whisper key", "   whisper key"],
    "processing": ["●∙∙ whisper key", "∙●∙ whisper key", "∙∙● whisper key", "∙●∙ whisper key"],
    "model_loading": ["●∙∙ whisper key", "∙●∙ whisper key", "∙∙● whisper key", "∙●∙ whisper key"],
}
_INTERVALS = {"idle": 60.0, "recording": 0.5, "processing": 0.2, "model_loading": 0.2}

class TerminalTitle:
    def __init__(self):
        self._enabled = sys.stdout.isatty()
        self._state = "idle"
        self._frame_index = 0
        self._lock = threading.Lock()
        self._tick = threading.Event()
        self._stop = threading.Event()
        self._thread = None

    def start(self):
        if not self._enabled:
            return
        self._emit_current()
        self._thread = threading.Thread(target=self._loop, daemon=True)
        self._thread.start()

    def update_state(self, new_state: str):
        if not self._enabled:
            return
        with self._lock:
            if new_state == self._state:
                return
            self._state = new_state
            self._frame_index = 0
        self._tick.set()

    def stop(self):
        if not self._enabled:
            return
        self._stop.set()
        self._tick.set()
        if self._thread:
            self._thread.join(timeout=1.0)
        sys.stdout.write("\033]0;\007")
        sys.stdout.flush()

    def _loop(self):
        while not self._stop.is_set():
            self._emit_current()
            with self._lock:
                interval = _INTERVALS.get(self._state, 1.0)
                self._frame_index += 1
            self._tick.wait(timeout=interval)
            self._tick.clear()

    def _emit_current(self):
        with self._lock:
            frames = _FRAMES.get(self._state, _FRAMES["idle"])
            title = frames[self._frame_index % len(frames)]
        sys.stdout.write(f"\033]0;{title}\007")
        sys.stdout.flush()
```

### state_manager.py (delta)

**Before:**
```python
def __init__(self, ..., system_tray=None, audio_feedback=None, voice_command_manager=None):
    ...
    self.system_tray = OptionalComponent(system_tray)
```

**After:**
```python
def __init__(self, ..., system_tray=None, audio_feedback=None, voice_command_manager=None, terminal_title=None):
    ...
    self.system_tray = OptionalComponent(system_tray)
    self.terminal_title = OptionalComponent(terminal_title)
```

Each existing line:
```python
self.system_tray.update_state("recording")
```
gets a sibling:
```python
self.terminal_title.update_state("recording")
```

### main.py (delta)

**Before** (lines 204–208):
```python
console.setup()
sys.stdout.reconfigure(encoding='utf-8', errors='replace')
sys.stdout.write("\033]0;Whisper Key\007")
sys.stdout.flush()
app.setup()
```

**After:**
```python
console.setup()
sys.stdout.reconfigure(encoding='utf-8', errors='replace')
app.setup()
terminal_title = TerminalTitle()
```

…then `terminal_title` is passed into `StateManager(...)` and started right before `app.run_event_loop(...)`, alongside `system_tray.start()`.

## Scope

| File | Change |
|------|--------|
| `src/whisper_key/terminal_title.py` | **New** — `TerminalTitle` class, frame tables, animation thread |
| `src/whisper_key/main.py` | Drop static OSC write, build/start/stop `TerminalTitle`, pass to `StateManager` |
| `src/whisper_key/state_manager.py` | New `terminal_title` constructor arg, 7 mirrored `update_state` calls |
| `~/.config/wezterm/wezterm.lua` | (No-op — no current binding emits OSC for `wk`) |

## Success Criteria

- [ ] Idle: tab shows `🎤 whisper key`
- [ ] Recording: tab pulses red dot at ~500 ms
- [ ] Processing (transcription or model load): tab shows bouncing-dot animation at ~200 ms
- [ ] State transitions are visible within ≤200 ms (no waiting on the previous frame's interval)
- [ ] Returns to idle after every flow: cancel, normal stop, max-duration auto-stop, VAD silence timeout, model-load complete
- [ ] No OSC bytes leak when stdout is redirected (`wk > out.log`)
- [ ] No regression on Windows Terminal or WezTerm
- [ ] No spurious garbage chars in legacy cmd.exe (or, if any, gated behind a VT-capability check)
- [ ] On exit: title clears or is overwritten by the shell's prompt redraw

## Risks

| Risk | Mitigation |
|------|------------|
| Tab width flickers between frames of differing visual width | Pad all frames in a state to identical character count; use width-stable glyphs |
| Emoji width inconsistency (🔴 = 1 cell vs 2 cell across terminals) | Acceptable cosmetic variance; document if it bothers users |
| Animation thread keeps running during shutdown and writes after stdout closes | `stop()` joins with 1s timeout; daemon thread is killed at process exit anyway |
| State change races (e.g. `update_state("idle")` called during a frame emit) | Frame index reset + `_tick_event.set()` on update; lock guards state read inside `_emit_current` |
| `cmd.exe` (legacy conhost) renders escape bytes literally | If reported, add a VT-capability gate using existing `console` platform module |
| `OptionalComponent` semantics differ from expected | Already used for `system_tray`/`audio_feedback`; pattern is established |

## Open questions

- **Configurable on/off?** Add a `console.tab_title_animation: true/false` config key, or keep it always-on when TTY-attached? Default-on with a single config flag is cheap and matches the existing `audio_feedback.enabled` pattern.
- **Different icon for `model_loading` vs `processing`?** Currently both use the same animation. If we want a distinct visual, model-load could use e.g. `⏳` static. Skipped for v1 — tray already conflates them.
- **Two-dot vs one-dot processing?** Plan defaults to single-dot bounce (cleaner, fewer frames). Two-dot ping-pong is documented as a drop-in alternative.
