# Component Architecture

## File Structure
```
main.py                    # Entry point
src/
├── audio_recorder.py      # sounddevice recording
├── whisper_engine.py      # faster-whisper transcription
├── clipboard_manager.py   # clipboard operations with auto-paste
├── hotkey_listener.py     # global hotkey detection
├── config_manager.py      # YAML configuration management
├── system_tray.py         # system tray icon and menu
└── state_manager.py       # component coordination
tests/component/           # Individual component tests
tools/key_helper.py        # Interactive key configuration utility
```

## Component Responsibilities

### hotkey_listener.py
- Monitor for configured hotkey press
- Toggle recording state
- Handle key conflicts gracefully

### audio_recorder.py
- Start/stop recording on command
- Buffer audio data in memory
- Handle microphone permissions

### whisper_engine.py
- Load selected model once at startup (default: tiny)
- Support runtime model switching (tiny/base/small)
- Process recorded audio with faster-whisper
- Return text transcription with confidence scores

### clipboard_manager.py
- Copy transcribed text to clipboard with notifications
- Auto-paste functionality via Windows API or key simulation
- Support for multiple paste methods (windows_api, key_simulation)
- Fallback mechanisms when paste methods fail
- Active window detection and direct message sending

### config_manager.py
- Load and validate YAML configuration files
- Provide default configuration values
- Validate settings for audio, whisper, hotkeys, clipboard, and logging
- Support for auto-paste and paste method configuration

### system_tray.py
- Display system tray icon with status indicators
- Show different icons for idle/recording/processing states
- Provide context menu for app controls and status
- Run in separate thread to avoid blocking main application
- Handle graceful startup/shutdown with fallback support

### state_manager.py
- Coordinate workflow between all components
- Handle recording/processing state transitions
- Implement auto-paste logic based on configuration
- Manage error handling and user notifications
- Process complete recording-to-paste pipeline
- Update system tray status during state changes