# macOS Compatibility Analysis

## Overview

Analysis of what would be required to make whisper-key-local runnable on macOS, examining Windows-specific dependencies and their cross-platform alternatives.

**★ Key Insight:** Your codebase shows excellent architectural foresight - you already have platform-specific dependencies in pyproject.toml with conditions like `platform_system=='Windows'`. This suggests the foundation for cross-platform support was already considered.

## Current Windows Dependencies

I've identified **5 core components** that rely on Windows-specific libraries:

| Component | Windows Library | Usage | Complexity |
|-----------|----------------|--------|------------|
| **Audio Feedback** | `winsound` | Playing notification sounds | 🟢 Low |
| **Clipboard Operations** | `pywin32` + `pyautogui` | Window handles, auto-paste | 🟡 Medium |
| **Hotkey Detection** | `global-hotkeys` | Global hotkey monitoring | 🔴 High |
| **Instance Management** | `win32api` + `win32event` | Single instance enforcement | 🟢 Low |
| **System Tray** | `pystray` + `Pillow` | Cross-platform (already works!) | ✅ Done |

## Required macOS Alternatives

### 1. Audio Feedback (`audio_feedback.py:4`)
- **Replace:** `winsound` 
- **With:** `playsound` or `pygame.mixer` for cross-platform audio
- **Challenge:** Thread management for async playback

### 2. Clipboard Operations (`clipboard_manager.py:6,7`)
- **Replace:** `win32gui.GetForegroundWindow()` 
- **With:** `AppKit.NSWorkspace.sharedWorkspace().frontmostApplication()` 
- **Replace:** `pyautogui` key simulation
- **With:** `pynput.keyboard` for cross-platform key simulation
- **Challenge:** macOS accessibility permissions for automation

### 3. Hotkey Detection (`hotkey_listener.py:3`)
- **Replace:** `global-hotkeys` library
- **With:** `pynput.keyboard.GlobalHotKeys` or `keyboard` library
- **Challenge:** This is the **biggest blocker** - global hotkey libraries have different APIs and reliability varies significantly on macOS

### 4. Instance Management (`instance_manager.py:5,6`)
- **Replace:** `win32event.CreateMutex()` 
- **With:** File-based locking using `fcntl` or `psutil` process checking
- **Challenge:** Race conditions and cleanup on crash

## Technical Implementation Strategy

**★ Key Insight:** The cleanest approach would be a **platform abstraction layer** - create interface classes that switch implementations based on `platform.system()`. This maintains your existing API while allowing platform-specific implementations underneath.

### Phase 1: Quick Wins (1-2 days)
```python
# Add to pyproject.toml dependencies:
"playsound>=1.3.0; platform_system=='Darwin'",
"pynput>=1.7.6; platform_system=='Darwin'", 
"psutil>=5.9.0; platform_system=='Darwin'",
```

### Phase 2: Platform Abstraction (3-5 days)
- Create `platform_audio.py`, `platform_clipboard.py`, `platform_instance.py`
- Each module detects platform and imports appropriate implementation
- Minimal changes to existing component interfaces

### Phase 3: macOS-Specific Challenges (5-10 days)
- **Hotkey detection:** Test multiple libraries (`pynput`, `keyboard`, `pystray` global shortcuts)
- **Accessibility permissions:** Handle macOS security prompts gracefully
- **App bundling:** Research `py2app` vs PyInstaller for macOS .app creation

## Biggest Risk: Global Hotkeys

The `global-hotkeys` library you're using is Windows-focused. macOS alternatives have **significant differences**:

- **API differences:** Different callback patterns, key naming conventions
- **Permission requirements:** macOS requires explicit accessibility permissions
- **Reliability issues:** Some libraries don't work well with system hotkeys on macOS
- **Testing complexity:** Hard to test without physical macOS machine

## Estimated Effort

- **Minimum viable port:** 1-2 weeks (basic functionality, rough edges)
- **Production-ready port:** 3-4 weeks (polished UX, proper error handling)
- **Ongoing maintenance:** Platform-specific bugs and testing overhead

## Recommendation

**Start with audio feedback replacement** as a proof-of-concept since it's the easiest component to make cross-platform. This would validate your platform abstraction approach before tackling the more complex hotkey system.

## Analysis Date
Generated: 2025-08-27

## Source Files Analyzed
- `/home/pin/whisper-key-local/pyproject.toml` - Dependencies and platform conditions
- `/home/pin/whisper-key-local/src/whisper_key/audio_feedback.py` - winsound usage
- `/home/pin/whisper-key-local/src/whisper_key/clipboard_manager.py` - pywin32 + pyautogui usage
- `/home/pin/whisper-key-local/src/whisper_key/instance_manager.py` - win32api + win32event usage
- `/home/pin/whisper-key-local/src/whisper_key/hotkey_listener.py` - global-hotkeys usage
- `/home/pin/whisper-key-local/src/whisper_key/system_tray.py` - Already cross-platform