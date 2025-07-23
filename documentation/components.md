# Component Architecture

## File Structure
```
main.py                    # Entry point
src/
├── audio_recorder.py      # sounddevice recording
├── whisper_engine.py      # faster-whisper transcription
├── clipboard_manager.py   # pyperclip operations
├── hotkey_listener.py     # global hotkey detection
└── state_manager.py       # component coordination
tests/component/           # Individual component tests
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
- Paste transcribed text to active application
- Handle different input contexts
- Error recovery for paste failures

### state_manager.py
- Coordinate between components
- Handle configuration and model selection
- Manage logging and errors