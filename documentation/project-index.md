Local faster-whisper speech-to-text app with global hotkeys for Windows 10+

- Start here: `state_manage.py` coordinates all components workflow
- Constraints: Windows-only runtime libraries (pywin32, global-hotkeys)

## Component Architecture

| Component | File | Primary Responsibility | Key Technologies |
|-----------|------|----------------------|------------------|
| **Entry Point** | `whisper-key.py` | Application orchestration & startup | logging, threading |
| **Audio Capture** | `audio_recorder.py` | Microphone recording & audio buffering | sounddevice, numpy |
| **Audio Feedback** | `audio_feedback.py` | Recording event sound notifications | winsound, asyncio |
| **Speech Recognition** | `whisper_engine.py` | Audio transcription using AI | faster-whisper |
| **Clipboard Operations** | `clipboard_manager.py` | Text copying & auto-paste functionality | pyperclip, pywin32, pyautogui |
| **Hotkey Detection** | `hotkey_listener.py` | Global hotkey monitoring | global-hotkeys |
| **Configuration** | `config_manager.py` | YAML settings management & validation | ruamel.yaml |
| **System Integration** | `system_tray.py` | System tray icon & menu interface | pystray, Pillow |
| **State Coordination** | `state_manager.py` | Component orchestration & workflow | threading, logging |
| **Instance Management** | `instance_manager.py` | Single instance enforcement & window focusing | win32api, win32event, win32gui |
| **Utilities** | `utils.py` | Common utility functions | - |

## Project Structure

```
whisper-key-local/
├── whisper-key.py              # Main application entry point
├── config.defaults.yaml        # Default configuration template
├── requirements.txt            # Python dependencies
├── CLAUDE.md                   # Claude AI project instructions
├── README.md                   # Project documentation
├── app.log                     # Application log file
│
├── src/                        # Core application modules
│   ├── __init__.py             
│   ├── audio_feedback.py       # audio feedback for recording events
│   ├── audio_recorder.py       # sounddevice audio capture
│   ├── clipboard_manager.py    # clipboard & auto-paste operations
│   ├── config_manager.py       # YAML configuration management
│   ├── hotkey_listener.py      # global hotkey detection
│   ├── instance_manager.py     # single instance enforcement
│   ├── state_manager.py        # component coordination & workflow
│   ├── system_tray.py          # system tray icon & menu
│   ├── utils.py                # common utility functions
│   └── whisper_engine.py       # faster-whisper transcription
│
├── tests/                      # Test suite
│   ├── component/              # Unit tests for individual components
│   │   ├── test_audio.py       # Audio recording tests
│   │   ├── test_clipboard.py   # Clipboard operations tests
│   │   ├── test_hotkeys.py     # Hotkey listener tests
│   │   └── test_whisper.py     # Whisper engine tests
│   └── run_component_tests.py  # Test runner script
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
├── assets/                     # Visual & audio resources resources
│
├── documentation/              # Project documentation
│   ├── project-index.md        # This comprehensive index (YOU ARE HERE)
│   ├── plan-execution.md       # Plan execution instructions
│   ├── plan-writing.md         # Planning documentation
│   ├── roadmap/                # Feature roadmap & user stories
│   │   ├── roadmap.md          # Active feature roadmap
│   │   └── completed.md        # Completed user stories
│   ├── research/               # Research documentation
│   └── implementation-plans/   # Technical implementation plan .md files
│
└── .github/                    # GitHub Actions workflows
    └── workflows/
        └── claude-code-review.yml  # Automated code review workflow
```

---

*Last Updated: 2025-08-04 | Project Status: Active Development*