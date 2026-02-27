# macOS System Tray Refactor: run_detached() Approach

As a *user* I want **the system tray to work on macOS** so I can see the app status and access menus.

## Background

On macOS, pystray requires NSApplication to run on the **main thread**. The current architecture runs `icon.run()` in a daemon thread, which doesn't work on macOS.

The solution is to use `run_detached()` on both platforms, then run the appropriate event loop on the main thread.

## Current Architecture

```
main.py:
  Main thread:     while shutdown_event.wait() → handles signals

system_tray.py:
  Daemon thread:   icon.run() → handles tray events
```

**Problem:** On macOS, `icon.run()` in a daemon thread causes: no tray icon, Dock icon appears, app hangs, Ctrl+C doesn't work.

## Target Architecture

```
main.py:
  Main thread (macOS):   nsapp.run() → processes all Cocoa events
  Main thread (Windows): while shutdown_event.wait() → handles signals

system_tray.py:
  No thread:       icon.run_detached() → sets up tray, returns immediately
```

## Implementation Plan

1. Refactor system_tray.py
- [x] Remove the daemon thread (`self.thread`)
- [x] Change `icon.run()` to `icon.run_detached()`
- [x] Remove `_run_tray()` method (no longer needed)
- [x] Update `stop()` to work with detached mode
- [x] Remove macOS disable check (line 48-49) - enable tray on macOS
- [x] **Test on Windows:** verify tray still works with `run_detached()`

2. Refactor main.py for platform-specific main loop
- [x] Add platform import: `from .platform import IS_MACOS`
- [x] Replace the `while shutdown_event.wait()` loop with platform-specific code:
  - macOS: `nsapp.run()`
  - Windows: keep existing wait loop
- [x] Import AppKit only on macOS (conditional import)
- [x] **Test on Windows:** verify app still starts and shuts down correctly

3. macOS shutdown handling
- [x] On macOS, `nsapp.run()` blocks forever - need way to stop it
- [x] Wire up signal handler to call `nsapp.stop()` or `nsapp.terminate_(None)`
- [x] Ensure Ctrl+C still triggers graceful shutdown
- [x] **Manual test on macOS:** verify Ctrl+C stops the app

4. macOS system tray verification
- [x] **Manual test on macOS:** tray icon appears in menu bar
- [x] **Manual test on macOS:** tray menu opens and items work
- [ ] ~~**Manual test on macOS:** tray icon updates state (idle/recording/processing)~~ *(requires hotkeys)*
- [x] Document any issues found (see below)

5. Hide Dock icon
- [x] Research: `app.setActivationPolicy_(NSApplicationActivationPolicyAccessory)`
- [x] Add code to hide Dock icon on macOS (menu bar apps shouldn't show in Dock)
- [x] **Manual test:** no Dock icon, only menu bar icon

6. Fix Ctrl+C shutdown
- [x] Investigate why Ctrl+C shows `^C` but doesn't quit
- [x] Solution: Use event polling loop instead of blocking `nsapp.run()`
- [x] Refactor into `platform/*/app.py` for clean abstraction
- [x] **Manual test:** Ctrl+C immediately shuts down app

7. Suppress secure coding warning
- [x] Research NSApplicationDelegate.applicationSupportsSecureRestorableState
- [x] Implement AppDelegate with `applicationSupportsSecureRestorableState_()` returning True
- [x] **Manual test:** no warning on startup

## Code Changes

### system_tray.py - start() method

**Before:**
```python
def start(self):
    # ... setup code ...
    self.thread = threading.Thread(target=self._run_tray, daemon=True)
    self.thread.start()
    self.is_running = True
    return True

def _run_tray(self):
    self.icon.run()
```

**After:**
```python
def start(self):
    # ... setup code ...
    self.icon.run_detached()
    self.is_running = True
    return True
```

### main.py - main loop (refactored to platform abstraction)

**Before:**
```python
while not shutdown_event.wait(timeout=0.1):
    pass
```

**After:**
```python
from .platform import app

def main():
    app.setup()  # Platform-specific init (e.g., hide Dock on macOS)
    # ... component setup ...
    app.run_event_loop(shutdown_event)  # Platform-specific event loop
```

Platform implementations in `platform/*/app.py`:
- **macOS:** Polls NSApplication events with 0.1s timeout, checks shutdown_event each iteration
- **Windows:** Simple `shutdown_event.wait(timeout=0.1)` loop

## Scope

| File | Changes |
|------|---------|
| `system_tray.py` | Remove thread, use `run_detached()`, enable macOS |
| `main.py` | Platform-specific main loop, macOS signal handling |

## Success Criteria

- [x] Windows: app starts, tray works, Ctrl+C shuts down (no regression)
- [x] macOS: app starts without errors
- [x] macOS: tray icon appears in menu bar (not Dock)
- [x] macOS: tray menu works (View Log, Exit, etc.)
- [x] macOS: Ctrl+C gracefully shuts down app
- [ ] macOS: tray icon reflects state changes *(requires hotkeys)*

## Status

**All phases complete.** System tray fully working on macOS with no warnings.

## macOS Testing Findings (2026-02-03)

### Working
- Tray icon appears in menu bar
- Tray menu opens
- Menu actions work (View Log, Advanced Settings, audio device selection)

### Issues Found

**Issue 1: Ctrl+C doesn't quit immediately** ✅ RESOLVED
- Problem: `nsapp.run()` blocks forever, signal handler can't wake it
- Solution: Use event polling loop with `nextEventMatchingMask_untilDate_inMode_dequeue_()` and 0.1s timeout, checking `shutdown_event` each iteration

**Issue 2: Python rocket icon in Dock** ✅ RESOLVED
- Fixed with `app.setActivationPolicy_(NSApplicationActivationPolicyAccessory)` in `platform/macos/app.py`

**Issue 3: Secure coding warning on startup** ✅ RESOLVED
- Fixed with `AppDelegate.applicationSupportsSecureRestorableState_()` returning True in `platform/macos/app.py`

## Risks

| Risk | Mitigation |
|------|------------|
| `run_detached()` behaves differently on Windows | Test Windows first before macOS changes |
| NSApplication.stop_() doesn't work in signal handler | Try `terminate_()` or post event to queue |
| GIL issues on M1/M2/M3 Macs | Document if seen, may need queue-based approach |

## References

- [pystray FAQ - macOS main thread requirement](https://pystray.readthedocs.io/en/latest/faq.html)
- [pystray Issue #138 - GIL on M2](https://github.com/moses-palmer/pystray/issues/138)
- Design doc: `docs/design/macos-support.md` Phase 5
