Local faster-whisper speech-to-text app with global hotkeys for Windows 10+ and macOS

- Start here: `state_manager.py` coordinates all components workflow

## Component Architecture

| Component | File | Primary Responsibility | Key Technologies |
|-----------|------|----------------------|------------------|
| **Entry Point** | `main.py` | Component initialization, signal handling | logging, threading |
| **State Coordination** | `state_manager.py` | Component orchestration & workflow | threading, logging |
| **Audio Capture** | `audio_recorder.py` | Microphone recording & audio buffering | sounddevice, numpy |
| **Audio Feedback** | `audio_feedback.py` | Recording event sound notifications | playsound3 |
| **Speech Recognition** | `whisper_engine.py` | Audio transcription using AI | faster-whisper |
| **Model Management** | `model_registry.py` | Whisper model registry & cache detection | faster-whisper |
| **Voice Activity Detection** | `voice_activity_detection.py` | Continuous VAD monitoring & silence detection | ten-vad, threading |
| **Clipboard Operations** | `clipboard_manager.py` | Text copying & auto-paste functionality | pyperclip, pyautogui (Win), Quartz (Mac) |
| **Hotkey Detection** | `hotkey_listener.py` | Global hotkey monitoring | global-hotkeys (Win), NSEvent (Mac) |
| **Configuration** | `config_manager.py` | YAML settings management & validation | ruamel.yaml |
| **System Integration** | `system_tray.py` | System tray icon & menu interface | pystray, Pillow |
| **Console Management** | `console_manager.py` | Console window visibility control (exe only) | win32console (Win) |
| **Instance Management** | `instance_manager.py` | Single instance enforcement | win32event (Win), fcntl (Mac) |
| **Platform Abstraction** | `platform/` | OS-specific implementations | pywin32 (Win), pyobjc (Mac) |
| **Utilities** | `utils.py` | Common utility functions | - |

## Project Structure

```
whisper-key-local/
├── whisper-key.py                     # Development wrapper script
├── pyproject.toml                     # Dependencies & PyPI config
├── CLAUDE.md                          # Claude AI project instructions
├── README.md                          # Project documentation
├── CHANGELOG.md                       # Version history and changes
│
├── src/
│   └── whisper_key/                   # Python package
│       ├── __init__.py                # Package initialization
│       ├── main.py                    # Main application entry point
│       ├── config.defaults.yaml       # Default configuration template
│       ├── assets/                    # Application assets
│       │   ├── sounds/                # Audio feedback sounds
│       │   └── version.txt            # Build version file
│       ├── platform/                  # Platform abstraction layer
│       │   ├── __init__.py            # Platform detection & import routing
│       │   └── {macos,windows}/       # Platform-specific implementations
│       │       ├── assets/            # Platform-specific assets
│       │       ├── app.py             # Thread requirements
│       │       ├── hotkeys.py         # Hotkey detection
│       │       ├── icons.py           # Tray icons
│       │       ├── instance_lock.py   # Instance control
│       │       ├── keyboard.py        # Key simulation
│       │       ├── paths.py           # Path management
│       │       └── permissions.py     # Permission management
│       ├── audio_feedback.py          # Audio feedback for recording events
│       ├── audio_recorder.py          # Sounddevice audio capture
│       ├── clipboard_manager.py       # Clipboard & auto-paste operations
│       ├── config_manager.py          # YAML configuration management
│       ├── console_manager.py         # Console window visibility control
│       ├── hotkey_listener.py         # Global hotkey detection
│       ├── instance_manager.py        # Single instance enforcement
│       ├── model_registry.py          # Whisper model registry & caching
│       ├── state_manager.py           # Component coordination & workflow
│       ├── system_tray.py             # System tray icon & menu
│       ├── utils.py                   # Common utility functions
│       ├── voice_activity_detection.py # Voice activity detection
│       └── whisper_engine.py          # Faster-whisper transcription
│
├── documentation/                     # Project documentation
│   ├── project-index.md
│   ├── design/                        # Design docs
│   ├── implementation-plans/          # Implementation docs
│   ├── research/                      # Research docs
│   ├── roadmap/                       # Feature roadmap & user stories
│   │   ├── roadmap.md                 # Active feature roadmap
│   │   └── completed.md               # Completed user stories
│   └── temp/                          # Temporary documentation files
│
└── py-build/                          # PyInstaller scripts and config
```

---

*Last Updated: 2026-02-04 | Project Status: Active Development*