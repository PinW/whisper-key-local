# Custom Hotwords Implementation Plan

## Overview

Add a `hotwords` config list that gets passed to faster-whisper's `model.transcribe(hotwords=...)` parameter, biasing the model toward user-specified words during decoding.

## How It Works

faster-whisper's `hotwords` parameter accepts a string of comma-separated words. These get tokenized and injected into the decoder prompt for **every** audio segment, giving them higher probability during beam search. This is different from `initial_prompt` which only affects the first 30-second window.

Constraints:
- Shares a ~224 token budget (roughly 50-100 words)
- Works best with `beam_size >= 5` (we already default to 5)
- More effective on larger models (medium, large); less responsive on tiny/base

## Changes

### 1. `config.defaults.yaml` — add hotwords list

Add under the `whisper` section, after `beam_size`:

```yaml
  # Custom hotwords — words the model should favor during transcription
  # Useful for names, technical terms, or domain-specific vocabulary
  # Example: ["CTranslate2", "PyInstaller", "Whisper Key"]
  hotwords: []
```

An empty list means the feature is inactive (no parameter passed to transcribe).

### 2. `whisper_engine.py` — accept and pass hotwords

- Add `hotwords: list` parameter to `__init__()`, store as `self.hotwords`
- In `transcribe_audio()`, if `self.hotwords` is non-empty, join into a comma-separated string and pass as `hotwords=` to `model.transcribe()`
- Add `update_hotwords(hotwords: list)` method for future runtime updates

### 3. `main.py` — wire config to engine

- In `setup_whisper_engine()`, pass `whisper_config['hotwords']` to `WhisperEngine`

### 4. `config_manager.py` — validation (minimal)

- No validation needed beyond what `_remove_unused_keys_from_user_config` already handles
- The config merge system will use the default `[]` if the user hasn't set anything

## Data Flow

```
config.defaults.yaml        user_settings.yaml
    hotwords: []         →   hotwords: ["Pinwa", "CTranslate2"]
         │                            │
         └──── ConfigManager merges ──┘
                      │
              whisper_config['hotwords']
                      │
              main.py passes to WhisperEngine.__init__()
                      │
              self.hotwords = ["Pinwa", "CTranslate2"]
                      │
              transcribe_audio() joins → "Pinwa, CTranslate2"
                      │
              model.transcribe(hotwords="Pinwa, CTranslate2")
```

## Files Changed

| File | Change |
|------|--------|
| `config.defaults.yaml` | Add `hotwords: []` under `whisper` |
| `whisper_engine.py` | Accept `hotwords` param, pass to `model.transcribe()` |
| `main.py` | Pass `hotwords` from config to engine constructor |

3 files, ~10 lines of code.
