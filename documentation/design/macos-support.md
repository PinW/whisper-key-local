# macOS Support Design

## Goal

Add macOS support to whisper-key-local while maintaining Windows functionality.

## Progress

- [x] ~~**Phase 1:** Replace Windows-only libraries with cross-platform alternatives where possible~~
- [x] ~~**Phase 2:** Create platform abstraction layer for components that need different implementations~~
- [ ] **Phase 3:** Implement macOS-specific code behind the abstraction layer
  - [x] ~~**3.1:** Audio feedback (`platform/macos/audio.py` - playsound3)~~ *(already done)*
  - [x] ~~**3.2:** App data path (`utils.py` - use `~/Library/Application Support/`)~~
  - [x] ~~**3.3:** Instance lock (`platform/macos/instance_lock.py` - fcntl)~~
  - [ ] **3.4:** Key simulation (`platform/macos/keyboard.py` - Quartz CGEvent)
  - [x] ~~**3.5:** Hotkey detection (`platform/macos/hotkeys.py` - NSEvent)~~ ⚠️ needs real-device testing
  - [x] ~~**3.6:** Platform-aware config defaults (inline syntax in YAML)~~
  - [ ] **3.7:** Skip console manager on macOS
- [x] ~~**Phase 4:** Update `pyproject.toml` with platform markers for conditional dependencies~~
- [x] ~~**Phase 5:** Resolve macOS main thread / event loop architecture~~
  - [x] ~~**5.1:** Refactor to use `run_detached()` on both platforms~~
  - [x] ~~**5.2:** Add NSApplication event loop on main thread for macOS~~
  - [x] ~~**5.3:** Fix Ctrl+C shutdown (event polling in `platform/macos/app.py`)~~
  - [x] ~~**5.4:** Hide Dock icon (`setActivationPolicy_`)~~
  - [x] ~~**5.5:** Suppress secure coding warning (`AppDelegate`)~~
- [ ] **Phase 6:** macOS menu bar icon polish
  - [ ] **6.1:** Design proper template icons for macOS menu bar (monochrome, @2x variants)
  - [ ] **6.2:** Support dark/light mode (template images auto-adapt)
  - [ ] **6.3:** Correct sizing for Retina displays

---

## Phase 5: macOS Main Thread Architecture ✅ Complete

**Problem:** macOS requires NSApplication event loop on main thread for pystray and NSEvent monitoring.

**Solution:** Use `run_detached()` + event polling loop in `platform/macos/app.py`.

**Implementation:** `documentation/implementation-plans/2026-02-03-macos-run-detached-refactor.md`

---

## Component Analysis

| Component | Current (Windows) | Phase 1 | Phase 2/3 |
|-----------|-------------------|---------|-----------|
| Audio recording | sounddevice | ✅ Already cross-platform | - |
| Whisper engine | faster-whisper | ✅ Already cross-platform | - |
| VAD | ten-vad | ✅ Already cross-platform | - |
| Config | ruamel.yaml | ✅ Already cross-platform | - |
| System tray | pystray | ✅ Already cross-platform | - |
| Clipboard read/write | pyperclip | ✅ Already cross-platform | - |
| Audio feedback | winsound | ✅ playsound3 | - |
| Key simulation | pyautogui | ❌ | Platform abstraction (Quartz CGEvent) |
| Hotkey detection | global-hotkeys | ❌ | Platform abstraction (NSEvent) |
| Instance lock | win32event | ❌ | Platform abstraction (fcntl) |
| Console hide | win32console | ❌ | Skip on macOS (not needed) |
| PortAudio DLL | bundled DLL (for WASAPI) | ❌ | Skip on macOS (no WASAPI, sounddevice wheel suffices) |
| Window detection | win32gui | ❌ | Remove (dead code, not used) |
| App data path | `%APPDATA%` env var | ❌ | `~/Library/Application Support/` on macOS |

---

## Phase 1: Cross-Platform Foundations ✅ Complete

Replaced `winsound` with `playsound3` for audio feedback. Remaining cross-platform components (`sounddevice`, `faster-whisper`, `ten-vad`, `pyperclip`) require hotkeys to fully test.

---

## Phase 2: Platform Abstraction Layer ✅ Complete

### Folder Structure

```
src/whisper_key/platform/
├── __init__.py          # Platform detection (IS_MACOS, IS_WINDOWS), routes imports
├── macos/
│   ├── app.py           # NSApplication setup + event loop
│   ├── audio.py         # playsound3
│   ├── keyboard.py      # Quartz CGEvent (not yet implemented)
│   ├── hotkeys.py       # NSEvent global monitoring
│   └── instance_lock.py # fcntl
└── windows/
    ├── app.py           # Simple shutdown_event.wait() loop
    ├── audio.py         # winsound
    ├── keyboard.py      # pyautogui
    ├── hotkeys.py       # global-hotkeys
    ├── instance_lock.py # win32event
    └── console.py       # win32console
```

### Interface Contracts

| Module | Interface |
|--------|-----------|
| `app.py` | `setup()`, `run_event_loop(shutdown_event)` |
| `audio.py` | `play_sound(path, blocking=False)` |
| `keyboard.py` | `send_hotkey(*keys)`, `send_key(key)` |
| `hotkeys.py` | `HotkeyListener` class with `register()`, `start()`, `stop()` |
| `instance_lock.py` | `InstanceLock` class with `acquire()`, `release()` |

---

## Phase 3: macOS Implementations

| Component | Dependency | Status |
|-----------|------------|--------|
| Key simulation | `pyobjc-framework-Quartz` (CGEvent) | Not started |
| Hotkey detection | `pyobjc-framework-AppKit` (NSEvent) | ✅ Complete (needs real-device testing) |
| Instance lock | `fcntl` | ✅ Complete |

**Note:** Hotkey detection uses NSEvent global monitoring with `NSFlagsChanged` for modifier-only hotkeys and `keyDown` for traditional hotkeys. Requires Accessibility permissions. Fn key support via `NSEventModifierFlagFunction`.

---

## Configuration Changes ✅ Complete

### Inline Platform Syntax

Platform-specific defaults use inline syntax in `config.defaults.yaml`:
```yaml
recording_hotkey: ctrl+win | macos: fn+control
paste_hotkey: ctrl+v | macos: cmd+v
auto_enter_combination: alt | macos: option
```

Resolution happens in `config_manager.py` after config merge, before validation.

### Default Hotkeys

| Setting | Windows | macOS |
|---------|---------|-------|
| `recording_hotkey` | `ctrl+win` | `fn+control` |
| `paste_hotkey` | `ctrl+v` | `cmd+v` |
| `auto_enter_combination` | `alt` | `option` |
| `cancel_combination` | `esc` | `ctrl+.` (ESC and cmd+. are system-reserved) |

**Notes for Phase 3.5 (Hotkey Detection):**
- macOS modifier key names: `control`, `option`, `cmd`, `shift`, `fn`
- Fn key supported via `NSEvent.modifierFlags` with `NSEventModifierFlagFunction` (bit 23)
- Hotkey display formatting needs improvement for macOS - consider using symbols (⌘, ⌃, ⌥, ⇧) or proper names

**Decision: NSEvent with ModifierStateTracker** ✅

Implemented NSEvent-based hotkey detection with `NSFlagsChanged` + state tracking for modifier-only hotkeys. See `implementation-plans/2026-02-03-nsevent-hotkey-implementation.md` for details.

---

## Phase 4: Platform Markers in pyproject.toml ✅ Complete

Platform-conditional dependencies using PEP 508 markers (`sys_platform=='win32'` / `sys_platform=='darwin'`). See `pyproject.toml` for current implementation.

---

## Remaining Work

| Priority | Task | Notes |
|----------|------|-------|
| **Critical** | Real-device hotkey testing | Verify NSEvent implementation on actual macOS hardware |
| High | Key simulation (3.4) | Needed for auto-paste |
| Low | Console manager skip (3.7) | Cosmetic |
| Low | Menu bar icons (Phase 6) | Cosmetic |

---

## Risks & Mitigations

| Risk | Impact | Mitigation |
|------|--------|------------|
| NSEvent monitor returns None if Accessibility denied | High | Log clear error message, prompt user to enable permissions |
| Accessibility permissions on macOS | Medium | Clear user messaging, auto-open System Preferences |
| Different hotkey naming (Cmd vs Ctrl) | Low | Platform-aware defaults, users can override |

---

*Created: 2026-02-02 | Updated: 2026-02-03*
