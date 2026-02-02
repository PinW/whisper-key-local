# pystray NSApplication Main Thread Requirement on macOS

## Executive Summary

macOS imposes a fundamental architectural constraint: **NSApplication event loop must run on the main thread**. This is a Cocoa framework requirement, not a pystray limitation. Both pystray (system tray) and QuickMacHotKey (hotkey detection) need this.

**The Problem:** Running `icon.run()` in a daemon thread (as works on Windows) causes:
- Tray icon never appears
- Dock icon appears instead (bouncing Python rocket)
- App becomes unresponsive to Ctrl+C
- GIL and NSMenu assertion failures (especially on Apple Silicon M1/M2/M3)

---

## Part 1: Why macOS Requires NSApplication on Main Thread

### The Cocoa Framework Architecture

**NSApplication** is the central coordinator of macOS GUI apps, managing:
- The application's main event loop
- All resources used by the application's objects
- Event dispatch to windows and views

Per Apple's Thread Safety documentation:
> "The main thread of the application is responsible for handling events. Although the Application Kit continues to work if other threads are involved in the event path, operations can occur out of sequence."

### Why This Constraint Exists

1. **Event Loop Architecture:** `NSApplication.run()` starts an event loop that processes user input, window updates, and system notifications. Must run continuously on one thread.

2. **Thread-Unsafe UI Operations:** NSView, NSWindow, and other AppKit classes are explicitly not thread-safe:
   > "You should create, destroy, resize, move, and perform other operations on NSView objects only from the main thread of an application."

3. **Run Loop Binding:** Each thread has its own NSRunLoop. The event loop is tied to the main thread's run loop.

4. **System Integration:** The window server communicates with the main thread's event queue.

### The Python GIL Complication

Python's Global Interpreter Lock adds complexity:
- Only one Python thread can execute Python bytecode at a time
- When `NSApplication.run()` blocks the main thread, background Python threads remain in the GIL queue
- On Apple Silicon (M1/M2/M3), pystray issue #138 shows "PyEval_RestoreThread: GIL is released" errors

---

## Part 2: How pystray Implements NSApplication

### Darwin Backend

When you create a pystray Icon on macOS, it internally does:

```python
self._app = self._options['nsapplication'] \
    if 'nsapplication' in self._options \
    else AppKit.NSApplication.sharedApplication()
```

Key points:
- Uses the **shared singleton instance** of NSApplication
- Allows passing a custom NSApplication instance via options
- Reusing the shared instance lets multiple components integrate

### The `icon.run()` Method

```python
def _run(self):
    # Signal handling setup
    # Main event loop
    self._app.run()  # Blocks forever until stop() called
```

**Critical behavior:**
- **Blocking:** `NSApplication.run()` blocks the calling thread indefinitely
- **Must be on main thread:** Running in a daemon thread causes the event queue to be ignored

### The `icon.run_detached()` Method

```python
icon.run_detached(darwin_nsapplication=nsapp)
# Returns immediately, doesn't block
```

**Key differences from `run()`:**
- **Non-blocking:** Returns immediately
- **Deferred event loop:** Does NOT call `NSApplication.run()` - you must do that yourself
- **Purpose:** Let another framework own the main thread event loop

---

## Part 3: Why Current Architecture Fails on macOS

### Current Windows Architecture (Works Fine)

```
Main thread:     while shutdown_event.wait(timeout=0.1): pass
Daemon thread:   pystray icon.run()  ← Works on Windows
Other threads:   hotkeys, audio, etc.
```

### Why This Fails on macOS

```
Main thread:     while shutdown_event.wait(timeout=0.1): pass
                 └─ Main thread NOT running NSApplication

Daemon thread:   pystray icon.run()  ← FAILS!
                 └─ NSApplication must be on main thread
                 └─ Results in: no tray icon, Dock icon bounces,
                    app unresponsive, Ctrl+C doesn't work
```

---

## Part 4: Thread-Safe Communication

### The Challenge

When NSApplication runs the main-thread event loop, how do background threads safely update the tray?

### Solution: Queue-Based Communication

```python
import queue

update_queue = queue.Queue()

def process_updates():
    while True:
        try:
            update = update_queue.get(timeout=0.1)
            icon.icon = update['image']
            icon.menu = update['menu']
        except queue.Empty:
            continue

# Background threads put updates on the queue
def update_icon_from_worker():
    update_queue.put({'image': new_image, 'menu': new_menu})
```

---

## Part 5: Proposed Solutions

### Solution A: Platform-Specific Main Loop (Recommended)

```python
from whisper_key.platform import IS_MACOS

if IS_MACOS:
    run_macos_app()
else:
    run_windows_app()

def run_windows_app():
    # Current architecture - works fine
    system_tray.start()  # Daemon thread
    while not shutdown_event.wait(timeout=0.1):
        pass

def run_macos_app():
    from AppKit import NSApplication

    nsapp = NSApplication.sharedApplication()

    def setup_callback(icon):
        icon.visible = True
        start_background_components()

    icon.run_detached(
        setup=setup_callback,
        darwin_nsapplication=nsapp
    )

    nsapp.run()  # Main thread runs event loop
```

**Advantages:**
- Clean separation
- Shared NSApplication for tray and hotkeys
- No GIL contention

### Solution B: Use RUMPS on macOS

RUMPS is macOS-native and handles NSApplication internally:

```python
import rumps

class WhisperKeyApp(rumps.App):
    @rumps.clicked("Exit")
    def exit(self, _):
        rumps.quit_app()

app = WhisperKeyApp("Whisper Key")
app.run()
```

**Advantages:** Purpose-built for macOS, simpler API
**Disadvantages:** Requires separate tray code for platforms

### Solution C: Disable Tray on macOS (Currently Implemented)

Simplest approach - loses tray functionality but unblocks development.

---

## Part 6: Implementation Checklist

- [ ] Detect platform (IS_MACOS flag exists)
- [ ] For macOS: Create NSApplication instance early in main()
- [ ] For macOS: Use icon.run_detached() with shared NSApplication
- [ ] For macOS: Run background components in daemon threads
- [ ] For macOS: Use queue-based communication for tray updates
- [ ] For macOS: Run NSApplication.run() on main thread
- [ ] For Windows: Keep current daemon thread architecture
- [ ] Test on both Intel and Apple Silicon Macs

---

## Part 7: Risk Mitigation

| Risk | Severity | Mitigation |
|------|----------|-----------|
| GIL deadlock on Apple Silicon | High | Queue-based communication, no direct calls from daemon threads |
| Signal handling (Ctrl+C) | Medium | Test thoroughly; NSApplication may conflict |
| Menu updates from background threads | Medium | Use queues; never call icon.update() from non-main threads |
| Integration with QuickMacHotKey | High | Both need NSApplication; shared instance required |

---

## References

### pystray
- [pystray Documentation](https://pystray.readthedocs.io/en/latest/)
- [pystray FAQ - macOS Requirements](https://pystray.readthedocs.io/en/latest/faq.html)
- [Issue #138 - GIL problems on M2](https://github.com/moses-palmer/pystray/issues/138)

### Apple Documentation
- [NSApplication Documentation](https://developer.apple.com/documentation/appkit/nsapplication)
- [Thread Safety Summary](https://developer.apple.com/library/archive/documentation/Cocoa/Conceptual/Multithreading/ThreadSafetySummary/ThreadSafetySummary.html)

### Alternatives
- [RUMPS - macOS Status Bar Apps](https://github.com/jaredks/rumps)

---

*Research compiled: 2026-02-02*
