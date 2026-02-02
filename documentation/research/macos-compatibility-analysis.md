# macOS Compatibility Analysis

## Windows-Only Components

| File | Windows APIs | macOS Alternative |
|------|--------------|-------------------|
| `audio_feedback.py` | `winsound` | `playsound3` |
| `clipboard_manager.py` | `win32gui`, `pyautogui` | `pynput`, `AppKit` |
| `hotkey_listener.py` | `global-hotkeys` | `pynput.keyboard.GlobalHotKeys` |
| `instance_manager.py` | `win32event`, `win32api` | `fcntl` file locking |
| `console_manager.py` | `win32console`, `win32gui`, `win32con` | Not needed (macOS has no console hide) |
| `utils.py` | Bundled `portaudio.dll` path | Not needed (macOS uses system PortAudio) |

## Cross-Platform Components (No Changes Needed)

- `state_manager.py` - Pure Python orchestration
- `audio_recorder.py` - Uses `sounddevice` (cross-platform)
- `whisper_engine.py` - Uses `faster-whisper` (cross-platform)
- `model_registry.py` - Pure Python
- `voice_activity_detection.py` - Uses `ten-vad` + numpy (cross-platform)
- `config_manager.py` - Uses `ruamel.yaml` (cross-platform)
- `system_tray.py` - Uses `pystray` (already cross-platform)

**Note:** `state_manager.py` and `config_manager.py` have WASAPI audio host defaults but already guard with platform checks (return `None` on non-Windows).

## Difficulty Rating

| Component | Effort | Risk |
|-----------|--------|------|
| Audio feedback | Low | None |
| Instance manager | Low | Minor (cleanup on crash) |
| Console manager | None | Skip entirely on macOS |
| Clipboard/paste | Medium | macOS accessibility permissions |
| **Hotkey listener** | **High** | **Primary blocker** |

## Hotkey Challenge

The `global-hotkeys` library is Windows-only. See `macos-hotkey-research.md` for detailed analysis.

**Recommendation:** Use `QuickMacHotKey` on macOS (native Carbon API)
- All modifier keys work (Ctrl, Alt/Option, Cmd, Shift)
- `pynput` has broken Ctrl/Alt modifiers on macOS - not viable
- Requires macOS accessibility permissions

## pyproject.toml Already Has Platform Conditions

```toml
"global-hotkeys>=0.1.7; platform_system=='Windows'",
"pywin32>=306; platform_system=='Windows'",
"pyautogui>=0.9.54; platform_system=='Windows'",
```

Add for macOS:
```toml
"quickmachotkey>=0.1.0; platform_system=='Darwin'",
"pyobjc-framework-ApplicationServices>=10.0; platform_system=='Darwin'",
"playsound3>=2.0; platform_system=='Darwin'",
```

## Implementation Approach

Platform-specific code in `platform/` folder, with `__init__.py` routing to the correct subfolder:

```
src/whisper_key/
└── platform/
    ├── __init__.py          # Detects OS, imports from correct subfolder
    ├── macos/
    │   ├── audio.py         # playsound3
    │   ├── keyboard.py      # Quartz CGEvent
    │   ├── hotkeys.py       # QuickMacHotKey
    │   └── instance_lock.py # fcntl
    └── windows/
        ├── audio.py         # winsound
        ├── keyboard.py      # pyautogui
        ├── hotkeys.py       # global-hotkeys
        └── instance_lock.py # win32event
```

## Recommended Order

1. **Audio feedback** - Easiest, validates abstraction pattern
2. **Instance manager** - Simple, low risk
3. **Clipboard operations** - Medium complexity
4. **Hotkey listener** - Most complex, save for last

---
*Updated: 2026-02-02*
