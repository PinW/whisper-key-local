Local faster-whisper speech-to-text app with global hotkeys for Windows 10+

- Start here: `state_manager.py` coordinates all components workflow
- Constraints: Windows-only runtime libraries (pywin32, global-hotkeys)

## Component Architecture

| Component | File | Primary Responsibility | Key Technologies |
|-----------|------|----------------------|------------------|
| **Entry Point** | `main.py` | Component initialization, signal handling | logging, threading |
| **State Coordination** | `state_manager.py` | Component orchestration & workflow | threading, logging |
| **Audio Capture** | `audio_recorder.py` | Microphone recording & audio buffering | sounddevice, numpy |
| **Audio Feedback** | `audio_feedback.py` | Recording event sound notifications | winsound, threading |
| **Speech Recognition** | `whisper_engine.py` | Audio transcription using AI | faster-whisper, ten-vad |
| **Clipboard Operations** | `clipboard_manager.py` | Text copying & auto-paste functionality | pyperclip, pywin32, pyautogui |
| **Hotkey Detection** | `hotkey_listener.py` | Global hotkey monitoring | global-hotkeys |
| **Configuration** | `config_manager.py` | YAML settings management & validation | ruamel.yaml |
| **System Integration** | `system_tray.py` | System tray icon & menu interface | pystray, Pillow |
| **Instance Management** | `instance_manager.py` | Single instance enforcement | win32api, win32event |
| **Utilities** | `utils.py` | Common utility functions | - |

## Project Structure

```
whisper-key-local/
├── whisper-key.py              # Development wrapper script
├── pyproject.toml              # PyPI package configuration & dependencies
├── CLAUDE.md                   # Claude AI project instructions
├── README.md                   # Project documentation
├── CHANGELOG.md                # Version history and changes
├── app.log                     # Application log file
│
├── src/
│   └── whisper_key/            # Python package
│       ├── __init__.py         # Package initialization
│       ├── main.py             # Main application entry point
│       ├── config.defaults.yaml # Default configuration template
│       ├── assets/             # Application assets (sounds, icons)
│       │   ├── sounds/
│       │   └── *.png
│       ├── audio_feedback.py   # Audio feedback for recording events
│       ├── audio_recorder.py   # Sounddevice audio capture
│       ├── clipboard_manager.py # Clipboard & auto-paste operations
│       ├── config_manager.py   # YAML configuration management
│       ├── hotkey_listener.py  # Global hotkey detection
│       ├── instance_manager.py # Single instance enforcement
│       ├── state_manager.py    # Component coordination & workflow
│       ├── system_tray.py      # System tray icon & menu
│       ├── utils.py            # Common utility functions
│       └── whisper_engine.py   # Faster-whisper transcription
│
├── tools/                      # Utility scripts
│   ├── clear_log.py            # Log file cleanup
│   ├── clear_model_cache.py    # Whisper model cache cleanup
│   ├── create_tray_icons.py    # System tray icon generation
│   ├── key_helper.py           # Interactive hotkey configuration
│   ├── key_helper_alt.py       # Alternative keycode checker (uses global-hotkeys helper)
│   ├── open_user_settings.py   # Open user settings in editor
│   └── reset_user_settings.py  # Configuration reset utility
│
├── assets/                     # Visual & audio resources
│
├── documentation/              # Project documentation
│   ├── project-index.md        # This comprehensive index (YOU ARE HERE)
│   ├── plan-execution.md       # Plan execution instructions
│   ├── plan-writing.md         # Planning documentation
│   ├── roadmap/                # Feature roadmap & user stories
│   │   ├── roadmap.md          # Active feature roadmap
│   │   └── completed.md        # Completed user stories
│   ├── research/               # Research documentation
│   ├── implementation-plans/   # Technical implementation plan .md files
│   └── temp/                   # Temporary documentation files
│
└── py-build/                   # PyInstaller build scripts and configuration
```

---

*Last Updated: 2025-08-19 | Project Status: Active Development*