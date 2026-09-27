https://github.com/PinW/whisper-key-local

@docs/platform-abstraction.md

## Architecture

- **Start here:** `state_manager.py` coordinates components, recording→transcription→delivery

## Conventions

- Test app startup: `/test-from-wsl` (launch only, no interaction)
- Use explicit variable/function names
- **AVOID COMMENTS** IF AT ALL POSSIBLE! DO NOT WRITE DOCSTRINGS!
- **No backward compatibility** - Break old formats freely
