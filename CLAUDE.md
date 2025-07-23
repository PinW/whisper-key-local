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

## Commands
- `python main.py` - Run app
- `python tests/run_component_tests.py` - Test suite
- `python tools/key_helper.py` - Find key combinations for config

## Development Notes
- All testing is done by user on windows (you are in WSL)
- Don't commit before i test