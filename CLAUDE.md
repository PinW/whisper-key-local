# Project Instructions for Claude

## Learning Project Context
This is a learning project for a beginner coder - provide detailed explanations and educational context for all code and concepts.

## Project Overview
Windows Whisper Speech-to-Text App - A local implementation of OpenAI's Whisper speech-to-text for Windows 10 that:
- Uses the smallest Whisper model (tiny) running locally with CPU
- Runs as a Windows 10 background application
- Provides a global hotkey to start/stop recording
- Automatically pastes voice transcription into active application input

## Technology Stack
- **Language**: Python
- **Speech Recognition**: `faster-whisper` (4x faster than openai-whisper)
- **Audio Recording**: `sounddevice` (modern, efficient)
- **Global Hotkeys**: `global-hotkeys` (Windows-optimized)
- **Clipboard**: `pyperclip` (cross-platform clipboard handling)
- **System Tray**: `pystray` (optional)

## Architecture & Components

### File Structure
```
whisper-key-local/
├── main.py                 # Application entry point
├── src/                    # Source modules
│   ├── __init__.py
│   ├── audio_recorder.py   # Audio recording module
│   ├── whisper_engine.py   # Whisper transcription engine
│   ├── clipboard_manager.py # Clipboard integration
│   ├── hotkey_listener.py  # Global hotkey management
│   └── state_manager.py    # Application state coordination
├── tests/                  # Test suite
│   ├── component/          # Component tests
│   └── run_component_tests.py
└── documentation/          # Project documentation
```

### Component Responsibilities
1. **Global Hotkey Listener** (`src/hotkey_listener.py`)
   - Monitor for configured hotkey press
   - Toggle recording state
   - Handle key conflicts gracefully

2. **Audio Recording Module** (`src/audio_recorder.py`)
   - Start/stop recording on command
   - Buffer audio data in memory
   - Handle microphone permissions

3. **Whisper Transcription Engine** (`src/whisper_engine.py`)
   - Load selected model once at startup (default: tiny)
   - Support runtime model switching (tiny/base/small)
   - Process recorded audio with faster-whisper
   - Return text transcription with confidence scores

4. **Clipboard Integration** (`src/clipboard_manager.py`)
   - Paste transcribed text to active application
   - Handle different input contexts
   - Error recovery for paste failures

5. **Application State Manager** (`src/state_manager.py`)
   - Coordinate between components
   - Handle configuration and model selection
   - Manage logging and errors

## Configuration Options
- **Hotkey Combination**: Default `Ctrl+Shift+Space`
- **Recording Mode**: Toggle vs Hold-to-record
- **Model Selection**: tiny/base/small (runtime switching)
- **Audio Device**: Microphone selection
- **Model Language**: Force language vs auto-detect
- **Paste Behavior**: Immediate vs clipboard-only

## Development Commands
- **Run Application**: `python main.py`
- **Run Tests**: `python tests/run_component_tests.py`
- **Test Individual Components**: `python tests/component/test_[component].py`

## Performance Specifications
- **Model Size**: ~39MB (tiny model)
- **Cold Start**: 2-3 seconds (model loading)
- **Transcription**: 1-2 seconds for 10-second audio clip
- **Memory Usage**: ~200-300MB during transcription
- **Idle Usage**: ~50MB background service