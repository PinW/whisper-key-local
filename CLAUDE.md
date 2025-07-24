# Whisper Speech-to-Text App
*Learning project for beginner coder - provide detailed explanations*

## Project Overview
Local faster-whisper speech-to-text with global hotkey. Uses tiny model by default.

## Tech Stack
- **Python** with faster-whisper, sounddevice, global-hotkeys, pyperclip
- **Default model**: tiny (75MB)
- **Platform**: Windows 10+ (runs on Windows Python, dev in WSL)

## Roadmap
See `.documentation/roadmap.md`

## Architecture
See `.documentation/components.md` for details

## Configuration
See `config.yaml`

## Commands
- `python main.py` - Run app
- `python tests/run_component_tests.py` - Test suite
- `python tools/key_helper.py` - Find key combinations for config

## Development Notes
- DO NOT TEST (you are in WSL, and the app is run from windows)
- Ask the user to test for you if needed
- Don't commit before I test