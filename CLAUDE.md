# Whisper Speech-to-Text App
*Learning project for beginner coder - provide detailed explanations*

## Project Overview
Local faster-whisper speech-to-text with global hotkey. Uses tiny model by default.

## Tech Stack
- **Python** with faster-whisper, sounddevice, global-hotkeys, pyperclip
- **Default model**: tiny (39MB)
- **Platform**: Windows 10+ (runs on Windows Python, dev in WSL)

## Architecture
See `documentation/components.md` for detailed component structure and responsibilities.

## Configuration
All settings in `config.yaml`:
- **Whisper**: model size, language, beam_size
- **Hotkey**: combination (default: ctrl+shift+space) 
- **Audio**: sample_rate, channels, max_duration
- **Logging**: level, file/console output

## Commands
- `python main.py` - Run app
- `python tests/run_component_tests.py` - Test suite