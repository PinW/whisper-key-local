# Linux Desktop Support Research

**Date:** 2026-02-16
**Status:** Research Complete
**Scope:** Adding Linux as a third supported platform alongside Windows and macOS

---

## 1. Executive Summary

Linux support for Whisper Key is **feasible but non-trivial**, primarily because of the X11 vs Wayland fragmentation. The project's existing platform abstraction layer (`platform/{windows,macos}/`) is well-designed for adding a third `platform/linux/` directory with mirrored APIs.

**What works already (cross-platform):**
- Audio capture via `sounddevice` (PortAudio) -- works on Linux with minor caveats
- Clipboard via `pyperclip` -- works on Linux with `xclip`/`xsel` or `wl-clipboard`
- System tray via `pystray` -- works on Linux with AppIndicator backend
- Audio feedback via `playsound3` -- works on Linux with GStreamer/ALSA backends
- faster-whisper / CTranslate2 -- works on Linux, and GPU support via ROCm is **better** on Linux than Windows
- YAML config, logging, threading -- all pure Python, fully cross-platform

**What needs Linux-specific implementation:**
- Global hotkeys (the hardest problem -- X11 vs Wayland split)
- Key simulation for auto-paste
- Instance locking (can reuse macOS `fcntl` approach directly)
- Paths (`~/.config/whisperkey` via XDG)
- File opening (`xdg-open`)
- Console management (no-op, like macOS)
- Permissions (input group membership check)
- Platform detection in `__init__.py`

**The X11 vs Wayland problem** is the single biggest risk. Global hotkeys and key simulation have fundamentally different solutions depending on the display server, and Wayland's security model intentionally blocks the exact patterns this app relies on.

---

## 2. Component-by-Component Analysis

### 2.1 Platform Detection (`platform/__init__.py`)

**Current code:**
```python
PLATFORM = 'macos' if _platform.system() == 'Darwin' else 'windows'
```

**Change needed:** Add Linux detection. Simple.

```python
_system = _platform.system()
if _system == 'Darwin':
    PLATFORM = 'macos'
elif _system == 'Linux':
    PLATFORM = 'linux'
else:
    PLATFORM = 'windows'

IS_MACOS = PLATFORM == 'macos'
IS_WINDOWS = PLATFORM == 'windows'
IS_LINUX = PLATFORM == 'linux'
```

**Effort:** Trivial
**Risk:** None

Also need to detect display server type within Linux:
```python
import os
SESSION_TYPE = os.environ.get('XDG_SESSION_TYPE', 'x11')  # 'x11', 'wayland', or 'tty'
IS_WAYLAND = SESSION_TYPE == 'wayland'
```

### 2.2 Config Platform Values (`config_manager.py`)

**Current format:** `"ctrl+win | macos: fn+ctrl"`
**Change needed:** Add Linux variant syntax, e.g. `"ctrl+win | macos: fn+ctrl | linux: ctrl+super"`

The `_parse_platform_value()` function currently only handles `| macos:`. Need to extend to support `| linux:` with fallback to the default (Windows) value when no Linux-specific value is given.

**Effort:** Small
**Risk:** Low -- but this is a config format change

### 2.3 Global Hotkeys (`hotkeys.py`) -- HARDEST COMPONENT

**Windows:** Uses `global-hotkeys` library (Windows-only, uses Win32 RegisterHotKey)
**macOS:** Uses `NSEvent.addGlobalMonitorForEventsMatchingMask_handler_` (Cocoa)
**Current API:** `register(bindings)`, `start()`, `stop()`

**Linux solutions differ by display server:**

#### X11 Approach
- **pynput** -- Works well on X11. Provides `keyboard.Listener` for global key monitoring and `keyboard.GlobalHotKeys` for hotkey matching. Battle-tested, widely used. Does NOT work on native Wayland.
- Pure Xlib bindings via `python-xlib` -- Lower level, more control, but more code.

#### Wayland Approach
- **evdev** (kernel-level) -- Reads raw `/dev/input/event*` devices. Works on both X11 and Wayland because it operates below the display server layer. Requires user to be in the `input` group or run as root. This is the most reliable Wayland solution.
- **XDG GlobalShortcuts portal** -- The "proper" Wayland way. Uses D-Bus to register shortcuts with the compositor. Support varies wildly by desktop environment (KDE supports it, GNOME does not yet fully support it, Hyprland supports it). Python implementation is immature and buggy.

#### Recommended Strategy
Use **evdev** as the primary backend. It works on both X11 and Wayland, operates at the kernel level, and gives full control over key events including press/release detection (needed for the stop-with-modifier feature).

**Key features needed:**
- Modifier-only hotkeys (e.g., just pressing `ctrl` to stop) -- evdev supports this natively
- Modifier+key combos (e.g., `ctrl+super`) -- evdev supports this
- Press AND release callbacks -- evdev provides both key-down and key-up events
- Non-blocking background listener -- run in a daemon thread with `asyncio` or polling

**Dependencies:** `evdev` (Python package, Linux-only)
**System requirement:** User must be in the `input` group (`sudo usermod -aG input $USER`)

**Effort:** Large (most complex component)
**Risk:** High -- `input` group permission is a friction point for users

### 2.4 Key Simulation (`keyboard.py`)

**Windows:** Uses `pyautogui.hotkey()` and `pyautogui.press()`
**macOS:** Uses Quartz `CGEventCreateKeyboardEvent` / `CGEventPost`
**Current API:** `set_delay(delay)`, `send_hotkey(*keys)`, `send_key(key)`

#### X11 Approach
- **xdotool** -- CLI tool, call via `subprocess.run(['xdotool', 'key', 'ctrl+v'])`. Widely available, simple. Does NOT work on Wayland.
- **pynput** `keyboard.Controller` -- Works on X11. Clean Python API.
- **python-xlib** -- Direct X11 protocol, more control.

#### Wayland Approach
- **ydotool** -- CLI tool using kernel uinput. Works on both X11 and Wayland. Requires the `ydotoold` daemon running. Limitation: ASCII only (fine for Ctrl+V key simulation).
- **evdev UInput** -- Create a virtual keyboard device via `evdev.UInput` and inject key events. Works on both X11 and Wayland. Same permission requirements as reading events (needs `input` group or `uinput` group).
- **wtype** -- Wayland-only, for wlroots compositors. Too compositor-specific.

#### Recommended Strategy
Use **evdev UInput** for key simulation. Since we already need evdev for hotkey detection, this avoids adding another dependency. The `UInput` class can create a virtual keyboard and send synthetic key events.

Fallback: `xdotool` on X11 systems where evdev permissions aren't configured.

**Effort:** Medium
**Risk:** Medium -- same permission requirements as hotkeys

### 2.5 Clipboard (`clipboard_manager.py`)

**Current:** Uses `pyperclip` (cross-platform). Clipboard ops are already platform-agnostic.

**Linux support in pyperclip:**
- **X11:** Requires `xclip` or `xsel` installed (`sudo apt install xclip`)
- **Wayland:** Requires `wl-clipboard` installed (`sudo apt install wl-clipboard`). Recent versions of pyperclip detect Wayland and use `wl-copy`/`wl-paste`.

**Alternative:** `pyperclipfix` fork has more robust Wayland detection.

**What works already:** `pyperclip.copy()`, `pyperclip.paste()` -- the entire `ClipboardManager` class should work on Linux without code changes, only system package dependencies.

**Effort:** Minimal (documentation / dependency checking only)
**Risk:** Low -- but need to detect missing clipboard tools and give helpful error messages

### 2.6 Audio Capture (`audio_recorder.py`)

**Current:** Uses `sounddevice` (PortAudio bindings) with `numpy`. Cross-platform.

**Linux status:**
- sounddevice works on Linux via PortAudio
- PortAudio supports ALSA, PulseAudio, and (in 19.7.0+) PipeWire
- **Caveat:** Some distros ship outdated `libportaudio2` (19.6.0) that lacks PulseAudio/PipeWire host API support
- Modern distros (Ubuntu 24.04+, Fedora 39+) ship PortAudio 19.7.0+

**WASAPI-specific code:** The `_needs_resampling()` method checks for WASAPI (Windows Audio Session API). On Linux, the equivalent host APIs are ALSA/PulseAudio/PipeWire. The WASAPI resampling workaround is Windows-only and will correctly be skipped on Linux since no host API name will contain "wasapi".

**Host API names on Linux:** "ALSA", "PulseAudio", "JACK" (and eventually "PipeWire" via native PortAudio support)

**What works already:** Core recording loop, device enumeration, VAD integration -- all work on Linux.

**Effort:** Minimal
**Risk:** Low -- PortAudio version on older distros could be a problem

### 2.7 Audio Feedback (`audio_feedback.py`)

**Current:** Uses `playsound3` with `backend="winmm"` on Windows, `None` (auto) elsewhere.

**Linux status:**
- playsound3 supports Linux via GStreamer, ALSA (aplay), or FFmpeg backends
- Auto-detection picks the best available backend
- GStreamer is the preferred backend and is installed on most desktop Linux distros

**Current code already handles this:**
```python
SOUND_BACKEND = "winmm" if platform.system() == "Windows" else None
```
The `None` value triggers auto-detection, which works on Linux.

**System requirement:** GStreamer (`sudo apt install gstreamer1.0-tools`) or aplay (part of ALSA utils, usually pre-installed).

**Effort:** None (already works)
**Risk:** None

### 2.8 Instance Locking (`instance_lock.py`)

**Windows:** Uses Win32 named mutex (`win32event.CreateMutex`)
**macOS:** Uses `fcntl.flock()` on a lock file at `~/.{app_name}.lock`

**Linux:** `fcntl.flock()` is a POSIX API available on Linux. The macOS implementation can be **reused identically** for Linux.

**Effort:** Trivial (copy macOS implementation or share code)
**Risk:** None

### 2.9 Paths (`paths.py`)

**Windows:** `%APPDATA%\whisperkey`
**macOS:** `~/Library/Application Support/whisperkey`

**Linux (XDG standard):**
- Config/data: `$XDG_CONFIG_HOME/whisperkey` (defaults to `~/.config/whisperkey`)
- Or `$XDG_DATA_HOME/whisperkey` (defaults to `~/.local/share/whisperkey`)
- File opening: `subprocess.run(['xdg-open', str(path)])`

```python
import os, subprocess
from pathlib import Path

def get_app_data_path():
    xdg_config = os.environ.get('XDG_CONFIG_HOME', '')
    if xdg_config:
        return Path(xdg_config) / 'whisperkey'
    return Path.home() / '.config' / 'whisperkey'

def open_file(path):
    subprocess.run(['xdg-open', str(path)])
```

**Effort:** Trivial
**Risk:** None

### 2.10 Console Management (`console.py`)

**Windows:** Full console show/hide using `win32console`, `win32gui`
**macOS:** No-op stub (returns True)

**Linux:** No-op stub, same as macOS. Linux terminal management isn't relevant for a tray application.

**Effort:** Trivial (copy macOS no-op)
**Risk:** None

### 2.11 System Tray (`system_tray.py`)

**Current:** Uses `pystray` (cross-platform). Already in dependencies.

**Linux backend options in pystray:**
1. **AppIndicator** (preferred) -- Works on GNOME (with `gnome-shell-extension-appindicator`), KDE, XFCE, Cinnamon. Requires `gir1.2-ayatanaappindicator3-0.1` system package.
2. **GTK** -- Fallback. Uses GTK StatusIcon (deprecated in GTK3, removed in GTK4).
3. **Xlib** -- X11 only, won't work on Wayland.

**Wayland compatibility:** AppIndicator backend works on Wayland because it communicates over D-Bus (StatusNotifierItem protocol), not via X11. This is the recommended backend.

**Desktop environment coverage:**
| DE | AppIndicator | Notes |
|-----|-------------|-------|
| GNOME | Requires extension | `gnome-shell-extension-appindicator` |
| KDE Plasma | Native | Built-in StatusNotifierItem support |
| XFCE | Native | Built-in |
| Cinnamon | Native | Built-in |
| Sway/Hyprland | Varies | Need `waybar` or similar with tray support |

**What works already:** The entire `SystemTray` class uses pystray's API, which is backend-agnostic. No code changes needed.

**Effort:** Minimal (system package documentation only)
**Risk:** Low -- GNOME requires a shell extension, tiling WMs may lack tray support

### 2.12 Icons (`icons.py`)

**Windows/macOS:** Loads PNG icons from platform-specific assets directories.

**Linux:** Same approach works. Need to create `platform/linux/assets/` with tray icons. Can likely reuse the Windows or macOS icon set since pystray handles the rendering.

**Effort:** Trivial (copy icon assets, create module)
**Risk:** None

### 2.13 Permissions (`permissions.py`)

**Windows:** No-op (returns True)
**macOS:** Checks Accessibility permission via `AXIsProcessTrusted()`

**Linux:** No system-level accessibility permission like macOS. However, need to check:
- `input` group membership (for evdev hotkey/keyboard access)
- Clipboard tool availability (xclip/wl-clipboard)

```python
import os, grp

def check_accessibility_permission() -> bool:
    try:
        user_groups = [g.gr_name for g in grp.getgrall() if os.getlogin() in g.gr_mem]
        return 'input' in user_groups
    except:
        return True  # Assume OK if we can't check

def handle_missing_permission(config_manager) -> bool:
    # Guide user to add themselves to input group
    return True
```

**Effort:** Small
**Risk:** Low

### 2.14 App Event Loop (`app.py`)

**Windows:** Simple polling loop (`shutdown_event.wait(timeout=0.1)`)
**macOS:** NSApplication event loop pumping

**Linux:** Simple polling loop like Windows. No special event loop needed unless using GTK/Qt for something.

**Effort:** Trivial
**Risk:** None

### 2.15 Whisper Engine / GPU Support

**Current:** faster-whisper + CTranslate2, supports `cpu` and `cuda` devices.

**Linux GPU status:**
- **NVIDIA CUDA:** Fully supported, same as Windows. Install CUDA toolkit + cuDNN.
- **AMD ROCm:** **Much better on Linux than Windows.** ROCm is primarily a Linux platform. Community-built CTranslate2 ROCm packages exist. The `faster-whisper` + CTranslate2 ROCm pipeline is well-documented on Linux. Supports gfx900-gfx1151 architectures.
- **Intel oneAPI:** Experimental CTranslate2 support exists.

This is actually a **selling point** for Linux support -- AMD GPU users get better performance on Linux.

**Effort:** None for CPU. Documentation for GPU setup.
**Risk:** None

---

## 3. X11 vs Wayland Compatibility Matrix

| Component | X11 | Wayland | Strategy |
|-----------|-----|---------|----------|
| **Global Hotkeys** | pynput or evdev | evdev only | Use evdev for both |
| **Key Simulation** | xdotool, pynput, or evdev UInput | evdev UInput only | Use evdev UInput for both |
| **Clipboard** | xclip/xsel via pyperclip | wl-clipboard via pyperclip | pyperclip auto-detects |
| **System Tray** | All pystray backends | AppIndicator only | Use AppIndicator backend |
| **Audio Capture** | sounddevice (PortAudio) | sounddevice (PortAudio) | No difference |
| **Audio Playback** | playsound3 | playsound3 | No difference |
| **File Opening** | xdg-open | xdg-open | No difference |
| **Session Detection** | `$XDG_SESSION_TYPE == x11` | `$XDG_SESSION_TYPE == wayland` | Check env var |

**Bottom line:** Using `evdev` for hotkeys + key simulation and `AppIndicator` for system tray gives a unified solution that works on both X11 and Wayland.

---

## 4. Dependency Additions

### Python packages (add to `pyproject.toml`)

```toml
# Linux-only
"evdev>=1.7.0; sys_platform=='linux'",
```

That is the only new Python dependency. Everything else is already cross-platform or covered by existing dependencies.

### System packages (document for users)

**Ubuntu/Debian:**
```bash
# Required
sudo apt install libportaudio2                        # Audio capture (sounddevice)
sudo apt install xclip                                # Clipboard (X11)
sudo apt install wl-clipboard                         # Clipboard (Wayland)
sudo apt install gir1.2-ayatanaappindicator3-0.1      # System tray
sudo usermod -aG input $USER                          # Hotkey permissions (requires logout)

# Usually pre-installed
sudo apt install gstreamer1.0-tools                   # Audio feedback
```

**Fedora:**
```bash
sudo dnf install portaudio
sudo dnf install xclip                                # or wl-clipboard
sudo dnf install libappindicator-gtk3
sudo usermod -aG input $USER
```

**Arch:**
```bash
sudo pacman -S portaudio
sudo pacman -S xclip                                  # or wl-clipboard
sudo pacman -S libappindicator-gtk3
sudo usermod -aG input $USER
```

---

## 5. Risk Areas and Gotchas

### High Risk

1. **`input` group requirement for evdev** -- Users must add themselves to the `input` group and log out/in. This is unfamiliar to many users and the app cannot detect the problem gracefully until hotkey registration fails. Mitigation: Clear error messages, setup documentation, and a permission check on startup.

2. **Wayland hotkey reliability** -- Even with evdev, compositors may have their own global shortcuts that conflict. For example, KDE and GNOME both reserve `Super` key combinations. Mitigation: Good default hotkey choice (e.g., `ctrl+alt+r` instead of `ctrl+super`).

### Medium Risk

3. **PortAudio version** -- Older distros may ship PortAudio 19.6.0 without PulseAudio support, causing `sounddevice` to only see ALSA devices. Mitigation: Document minimum PortAudio version, provide pip-installed libportaudio as fallback.

4. **System tray on GNOME** -- GNOME removed native system tray support. Users need the `gnome-shell-extension-appindicator` extension. Mitigation: Detect GNOME and warn if extension is missing.

5. **System tray on tiling WMs** -- Sway, Hyprland, i3, etc. may not have tray support by default. Mitigation: App already handles tray unavailability gracefully (the `available` flag).

### Low Risk

6. **Clipboard tool missing** -- If neither xclip/xsel (X11) nor wl-clipboard (Wayland) is installed, pyperclip will throw an error. Mitigation: Check on startup and provide install instructions.

7. **playsound3 backend** -- If GStreamer is not installed, playsound3 falls back to aplay/ffmpeg. This usually works but may have slightly different behavior. Mitigation: Recommend GStreamer in setup docs.

8. **Config format change** -- Adding `| linux:` to the platform value syntax is a breaking change for the parser. Mitigation: Make Linux fall through to the default (Windows) value when no `| linux:` is specified, maintaining backward compatibility.

---

## 6. Recommended Implementation Order

### Phase 1: Platform Scaffolding (Small)
1. Update `platform/__init__.py` with Linux detection and `IS_LINUX` flag
2. Create `platform/linux/__init__.py` with module imports
3. Create no-op/trivial modules: `console.py`, `app.py`
4. Create `instance_lock.py` (copy from macOS -- identical `fcntl` code)
5. Create `paths.py` (XDG paths + `xdg-open`)
6. Create `icons.py` (copy icon assets from Windows)
7. Update `config_manager.py` to handle `| linux:` platform values
8. Update `pyproject.toml` with Linux dependency

### Phase 2: Core Functionality (Medium)
9. Create `hotkeys.py` using evdev -- the main engineering challenge
10. Create `keyboard.py` using evdev UInput
11. Create `permissions.py` with input group detection

### Phase 3: Testing and Polish (Medium)
12. Test on X11 desktop (Ubuntu with Xorg)
13. Test on Wayland desktop (Ubuntu with Wayland, or Fedora)
14. Test all hotkey combinations including modifier-only hotkeys
15. Test auto-paste flow end-to-end
16. Update default config with Linux-appropriate hotkey defaults
17. Documentation: setup guide, troubleshooting

### Phase 4: Distribution (Optional)
18. Test pip install on Linux
19. Consider AppImage packaging for single-file distribution
20. Document GPU setup for NVIDIA CUDA and AMD ROCm on Linux

---

## 7. Effort Estimates

| Component | New Files | Effort | Notes |
|-----------|-----------|--------|-------|
| Platform detection | Edit 1 | 1 hour | Modify `__init__.py` |
| Config platform values | Edit 1 | 1-2 hours | Extend parser for `\| linux:` |
| `console.py` | 1 new | 15 min | No-op stub |
| `app.py` | 1 new | 15 min | Simple polling loop |
| `instance_lock.py` | 1 new | 15 min | Copy from macOS |
| `paths.py` | 1 new | 30 min | XDG paths |
| `icons.py` | 1 new + assets | 30 min | Copy approach from Windows |
| `permissions.py` | 1 new | 1-2 hours | Input group check + user guidance |
| **`hotkeys.py`** | **1 new** | **6-10 hours** | **evdev listener, key parsing, modifier tracking** |
| **`keyboard.py`** | **1 new** | **3-5 hours** | **evdev UInput key simulation** |
| `pyproject.toml` | Edit 1 | 15 min | Add evdev dependency |
| Config defaults | Edit 1 | 30 min | Linux hotkey defaults |
| Testing | -- | 4-8 hours | X11 + Wayland + multiple DEs |
| Documentation | 1-2 new | 2-3 hours | Setup guide |
| **Total** | **~10 files** | **~20-30 hours** | |

The bulk of the work is in `hotkeys.py` and `keyboard.py`. Everything else is small.

---

## 8. Files That Need Changes (Existing)

| File | Change |
|------|--------|
| `src/whisper_key/platform/__init__.py` | Add Linux detection, IS_LINUX flag, import linux modules |
| `src/whisper_key/config_manager.py` | Extend `_parse_platform_value()` for `\| linux:` syntax |
| `src/whisper_key/config.defaults.yaml` | Add Linux path docs, Linux hotkey defaults |
| `pyproject.toml` | Add `evdev` Linux dependency, update description |

## 9. New Files Needed

| File | Based On |
|------|----------|
| `src/whisper_key/platform/linux/__init__.py` | Windows/macOS pattern |
| `src/whisper_key/platform/linux/app.py` | Windows version (polling loop) |
| `src/whisper_key/platform/linux/console.py` | macOS version (no-op) |
| `src/whisper_key/platform/linux/hotkeys.py` | New (evdev-based) |
| `src/whisper_key/platform/linux/keyboard.py` | New (evdev UInput) |
| `src/whisper_key/platform/linux/icons.py` | Windows version (same pattern) |
| `src/whisper_key/platform/linux/instance_lock.py` | macOS version (identical) |
| `src/whisper_key/platform/linux/paths.py` | New (XDG standard) |
| `src/whisper_key/platform/linux/permissions.py` | New (input group check) |
| `src/whisper_key/platform/linux/assets/` | Copy tray icons |

---

*Research completed 2026-02-16*
