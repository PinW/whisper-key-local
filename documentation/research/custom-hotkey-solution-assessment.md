# Custom macOS Hotkey Solution Assessment

## Summary

Building a custom macOS global hotkey solution in Python with Fn key support is **possible but constrained**. While PyObjC provides the low-level APIs (CGEventTap, NSEvent monitoring) needed to detect global keyboard events and the Fn modifier, Apple's API restrictions and the Fn key's reserved status create significant limitations. A from-scratch solution is feasible but requires substantial effort.

## Approach Options

### Option 1: CGEventTap (Lowest-level, most control)

**How it works:**
- Create a low-level event tap using `Quartz.CGEventTapCreate()` that intercepts all keyboard events
- Register a callback function that fires for every keyboard event system-wide
- Integrate the tap into the Core Foundation run loop

**Pros:**
- Lowest level - can detect ANY keyboard event including Fn key modifier
- Can intercept and modify/block events
- Works globally across all applications

**Cons:**
- Requires accessibility permissions
- Memory leak issues with CGEventTapCreate (should be called sparingly)
- Complex C-level callback management through PyObjC
- Requires Core Foundation run loop integration
- Performance overhead from monitoring every keyboard event

**Code Complexity:** HIGH

### Option 2: NSEvent Global Monitoring (Medium-level, simpler)

**How it works:**
- Use `NSEvent.addGlobalMonitorForEventsMatchingMask_handler_()` to register a global event monitor
- Handler callback fires only for matching events
- Cannot modify events (read-only monitoring)

**Pros:**
- Much simpler than CGEventTap
- No run loop management needed
- No C callbacks - pure Python/PyObjC
- Fn key state detectable via `event.modifierFlags()` with NSEventModifierFlagFunction

**Cons:**
- Cannot block/intercept events
- Requires accessibility permissions
- Less control than CGEventTap

**Code Complexity:** MEDIUM

### Option 3: Carbon RegisterEventHotKey (Legacy, limited)

**How it works:**
- Use deprecated Carbon API to register event hotkeys
- Specify virtual key code and modifier mask
- System calls handler when that specific combo is pressed

**Pros:**
- Simpler API
- No event loop integration needed

**Cons:**
- **Deprecated since macOS 10.8**
- Cannot detect Fn key as modifier
- May break in future macOS versions

**Code Complexity:** MEDIUM

## Fn Key Detection Method

**Via NSEvent (simpler):**
```python
from AppKit import NSEvent

def handler(event):
    if event.modifierFlags() & NSEvent.NSEventModifierFlagFunction:
        print("Fn key detected!")

    has_control = event.modifierFlags() & NSEvent.NSEventModifierFlagControl
    has_option = event.modifierFlags() & NSEvent.NSEventModifierFlagOption
    has_command = event.modifierFlags() & NSEvent.NSEventModifierFlagCommand
```

**Via CGEventFlags (lower-level):**
```python
from Quartz import CGEventFlags

def tap_callback(proxy, event_type, event, refcon):
    flags = event.flags()
    has_fn = flags & CGEventFlags.maskSecondaryFn
    has_control = flags & CGEventFlags.maskControl
```

**Critical Limitation:** The Fn key is **reserved by Apple** for system functions. While it CAN be detected, Apple's public API explicitly excludes it from RegisterEventHotKey.

## Code Outline

### NSEvent Global Monitoring Implementation

```python
from AppKit import NSEvent, NSApplication

class MacHotkeyListener:
    def __init__(self):
        self.handlers = {}
        self.monitor = None

    def register(self, key_code, modifiers, callback):
        key = (key_code, modifiers)
        self.handlers[key] = callback

    def _global_handler(self, event):
        event_modifiers = event.modifierFlags()
        characters = event.charactersIgnoringModifiers()

        if not characters:
            return

        key_char = ord(characters[0])

        for (registered_key, registered_mods), callback in self.handlers.items():
            if key_char == registered_key:
                current_mods = event_modifiers & NSEvent.NSEventDeviceIndependentModifierFlagsMask
                if current_mods == registered_mods:
                    callback()

    def start(self):
        self.monitor = NSEvent.addGlobalMonitorForEventsMatchingMask_handler_(
            NSEvent.NSKeyDownMask,
            self._global_handler
        )

    def stop(self):
        if self.monitor:
            NSEvent.removeMonitor_(self.monitor)
            self.monitor = None
```

**Effort:** ~150 lines of Python, moderate PyObjC knowledge required

## Effort Assessment

| Aspect | Difficulty | Time Estimate |
|--------|-----------|---------------|
| NSEvent global monitoring | Medium | 2-3 hours |
| CGEventTap approach | Hard | 6-8 hours |
| Testing & debugging | Hard | 4-6 hours |
| Edge cases | Medium | 2-3 hours |
| **Total (NSEvent)** | **Medium** | **8-12 hours** |
| **Total (CGEventTap)** | **Hard** | **14-18 hours** |

**Why it's non-trivial:**
1. PyObjC-to-C boundary complexity
2. Run loop integration (main thread requirements)
3. Accessibility permission handling
4. Memory management (CGEventTap leaks)
5. Testing requires actual macOS hardware

## Recommendation

**Don't build from scratch** - use QuickMacHotKey for standard modifiers, then:

1. **If Fn key is required:** Add NSEvent global monitoring alongside QuickMacHotKey to detect Fn state
2. **Alternative:** Let users configure Fn remapping via Karabiner-Elements at system level

**Implementation Path:**
1. Try QuickMacHotKey first (2-3 hours integration)
2. If Fn needed, add NSEvent observer for Fn detection (medium effort)
3. Combine both: QuickMacHotKey for registration, NSEvent for Fn state checking

---
*Generated: 2026-02-03*
