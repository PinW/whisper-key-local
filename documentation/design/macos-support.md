# macOS Support Design

## Goal

Add macOS support to whisper-key-local while maintaining Windows functionality.

## Progress

- [x] ~~**Phase 1:** Replace Windows-only libraries with cross-platform alternatives where possible~~
- [x] ~~**Phase 2:** Create platform abstraction layer for components that need different implementations~~
- [x] ~~**Phase 3:** Implement macOS-specific code behind the abstraction layer~~
  - [x] ~~**3.1:** Audio feedback (`audio_feedback.py` - playsound3, cross-platform)~~
  - [x] ~~**3.2:** App data path (`platform/macos/paths.py` - `~/Library/Application Support/`)~~
  - [x] ~~**3.3:** Instance lock (`platform/macos/instance_lock.py` - fcntl)~~
  - [x] ~~**3.4:** Key simulation (`platform/macos/keyboard.py` - Quartz CGEvent)~~
  - [x] ~~**3.5:** Hotkey detection (`platform/macos/hotkeys.py` - NSEvent)~~
  - [x] ~~**3.6:** Platform-aware config defaults (inline syntax in YAML)~~
  - [x] ~~**3.7:** Console manager (`platform/macos/console.py` - no-op stub)~~
  - [x] ~~**3.8:** Accessibility permission UX (`platform/macos/permissions.py`)~~
- [x] ~~**Phase 4:** Update `pyproject.toml` with platform markers for conditional dependencies~~
- [x] ~~**Phase 5:** Resolve macOS main thread / event loop architecture~~
  - [x] ~~**5.1:** Refactor to use `run_detached()` on both platforms~~
  - [x] ~~**5.2:** Add NSApplication event loop on main thread for macOS~~
  - [x] ~~**5.3:** Fix Ctrl+C shutdown (event polling in `platform/macos/app.py`)~~
  - [x] ~~**5.4:** Hide Dock icon (`setActivationPolicy_`)~~
  - [x] ~~**5.5:** Suppress secure coding warning (`AppDelegate`)~~
- [ ] **Phase 6:** macOS polish & documentation
  - [x] ~~**6.1:** Design proper template icons for macOS menu bar (monochrome, @2x variants)~~
  - [x] ~~**6.2:** Support dark/light mode (gradient indicator lights for visibility)~~
  - [x] ~~**6.3:** Correct sizing for Retina displays~~
  - [x] ~~**6.4:** Fix tray icon not updating during transcription (threaded callbacks)~~
  - [ ] **6.5:** Update README with macOS support
  - [x] ~~**6.6:** Update project index~~

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

Replaced `winsound` with `playsound3` for audio feedback.

---

## Phase 2: Platform Abstraction Layer ✅ Complete

### Folder Structure

```
src/whisper_key/platform/
├── __init__.py          # Platform detection (IS_MACOS, IS_WINDOWS), routes imports
├── macos/
│   ├── app.py           # NSApplication setup + event loop
│   ├── console.py       # No-op stub
│   ├── hotkeys.py       # NSEvent global monitoring
│   ├── instance_lock.py # fcntl
│   ├── keyboard.py      # Quartz CGEvent
│   ├── keycodes.py      # Mac virtual key codes
│   ├── paths.py         # ~/Library/Application Support/
│   └── permissions.py   # Accessibility permission check/prompt
└── windows/
    ├── app.py           # Simple shutdown_event.wait() loop
    ├── console.py       # win32console
    ├── hotkeys.py       # global-hotkeys
    ├── instance_lock.py # win32event
    ├── keyboard.py      # pyautogui
    ├── paths.py         # %APPDATA%
    └── permissions.py   # No-op (Windows doesn't need accessibility permission)
```

### Interface Contracts

| Module | Interface |
|--------|-----------|
| `app.py` | `setup()`, `run_event_loop(shutdown_event)` |
| `keyboard.py` | `send_hotkey(*keys)`, `send_key(key)` |
| `hotkeys.py` | `HotkeyListener` class with `register()`, `start()`, `stop()` |
| `instance_lock.py` | `InstanceLock` class with `acquire()`, `release()` |
| `console.py` | `ConsoleManager` class with `show_console()`, `hide_console()` |
| `paths.py` | `get_app_data_dir()` |
| `permissions.py` | `check_accessibility_permission()`, `handle_missing_permission()` |

---

## Phase 3: macOS Implementations ✅ Complete

| Component | Dependency | Status |
|-----------|------------|--------|
| Key simulation | `pyobjc-framework-Quartz` (CGEvent) | ✅ Complete |
| Hotkey detection | `pyobjc-framework-AppKit` (NSEvent) | ✅ Complete |
| Instance lock | `fcntl` (stdlib) | ✅ Complete |
| Console manager | N/A (no-op stub) | ✅ Complete |
| Accessibility UX | `pyobjc-framework-ApplicationServices` | ✅ Complete |

---

## Configuration Changes ✅ Complete

Platform-specific defaults use inline syntax in `config.defaults.yaml` (e.g., `ctrl+win | macos: fn+control`). Resolution happens in `config_manager.py`.

| Setting | Windows | macOS |
|---------|---------|-------|
| `recording_hotkey` | `ctrl+win` | `fn+control` |
| `paste_hotkey` | `ctrl+v` | `cmd+v` |
| `auto_enter_combination` | `alt` | `option` |
| `cancel_combination` | `esc` | `shift` |

---

## Phase 4: Platform Markers in pyproject.toml ✅ Complete

Platform-conditional dependencies using PEP 508 markers (`sys_platform=='win32'` / `sys_platform=='darwin'`). See `pyproject.toml` for current implementation.

---

## Remaining Work

| Priority | Task | Notes |
|----------|------|-------|
| Low | Update README (Phase 6.5) | Documentation |

---

## Accessibility Permission UX ✅ Complete

**Problem:** macOS requires Accessibility permission for keyboard simulation. Without it, `CGEventPost` silently fails - no error, no paste.

**Solution:** Platform abstraction in `platform/*/permissions.py` with user-friendly terminal prompt.

**Implementation:**
- `check_accessibility_permission()` - Check if permission granted
- `request_accessibility_permission()` - Show system permission dialog
- `handle_missing_permission()` - Terminal UI with two options:
  1. Grant permission (opens System Settings, prompts restart)
  2. Disable auto-paste (transcribe to clipboard only)

**Trigger:** At app startup when auto-paste is enabled but permission not granted.

---

## Risks & Mitigations

| Risk | Impact | Mitigation |
|------|--------|------------|
| Accessibility permissions on macOS | Medium | ✅ Handled via `platform/macos/permissions.py` |

---

*Created: 2026-02-02 | Updated: 2026-02-04 | Phase 5 complete, Phase 6 icons done*
