# Whisper Key - Local Speech-to-Text

Global hotkeys to record speech and transcribe directly to your cursor. 

> **Now on Windows and macOS!** Questions or ideas? [Discord](https://discord.gg/uZnXV8snhz)

## ✨ Features

- **Global Hotkey**: Start recording speech from any app
- **Auto-Paste**: Transcribe directly to cursor
- **Auto-Send**: Optionally auto-send with ENTER keypress
- **Local/Offline**: Voice data never leaves your computer
- **CPU Ready**: Small, efficient models available
- **GPU Ready**: Support for both NVIDIA & AMD cards
- **Cross-platform**: Works on Windows and macOS
- **Configurable**: Customize hotkeys, models, and [much more](#️-configuration)

> **Roadmap**: voice commands → terminal UI → CLI wrapper (`whisper-key claude`) → [etc...](documentation/roadmap/roadmap.md)

## 🚀 Quick Start

### From PyPI (Recommended)

Requires Python 3.11-3.13

```bash
# With pipx (isolated environment)
pipx install whisper-key-local

# Or with pip (simpler)
pip install whisper-key-local
```

Then run: `whisper-key`

### Portable App (Windows Only)

1. [Download the latest release zip](https://github.com/PinW/whisper-key-local/releases/latest)
2. Extract and run `whisper-key.exe`

### From Source

```bash
git clone https://github.com/PinW/whisper-key-local.git
cd whisper-key-local
pip install -e .
python whisper-key.py
```

## ⚡ GPU Acceleration Setup

Whisper Key supports both NVIDIA (CUDA, GTX 900 series or later) and AMD (ROCm, RX 6000 series or later) GPUs, but may require additional setup.

Please refer to the **[GPU Setup Guide](documentation/gpu-setup.md)** for instructions.

## 🎤 Basic Usage

| Hotkey | Windows | macOS |
|--------|---------|-------|
| Start recording | `Ctrl+Win` | `Fn+Ctrl` |
| Stop & transcribe | `Ctrl` | `Fn` |
| Stop & auto-send | `Alt` | `Option` |
| Cancel recording | `Esc` | `Shift` |

Open the system tray / menu bar icon to:
- Toggle auto-paste vs clipboard-only
- Change transcription model
- Select audio device

## ⚙️ Configuration

Local settings at:
- **Windows:** `%APPDATA%\whisperkey\user_settings.yaml`
- **macOS:** `~/Library/Application Support/whisperkey/user_settings.yaml`

Delete this file and restart app to reset to defaults.

| Option | Default | Notes |
|--------|---------|-------|
| **Whisper** |||
| `whisper.model` | `tiny` | Any model defined in `whisper.models` |
| `whisper.device` | `cpu` | cpu or cuda (NVIDIA/AMD GPU) — [setup guide](documentation/gpu-setup.md) |
| `whisper.compute_type` | `int8` | int8/float16/float32 |
| `whisper.language` | `auto` | auto or language code (en, es, fr, etc.) |
| `whisper.beam_size` | `5` | Higher = more accurate but slower (1-10) |
| `whisper.models` | (see config) | Add custom HuggingFace or local models |
| **Hotkeys** |||
| `hotkey.recording_hotkey` | `ctrl+win` / `fn+ctrl` | Windows / macOS |
| `hotkey.stop_with_modifier_enabled` | `true` | Stop with first modifier only |
| `hotkey.auto_enter_enabled` | `true` | Enable auto-send hotkey |
| `hotkey.auto_enter_combination` | `alt` / `option` | Stop + paste + Enter |
| `hotkey.cancel_combination` | `esc` / `shift` | Cancel recording |
| **Voice Activity Detection** |||
| `vad.vad_precheck_enabled` | `true` | Prevent hallucinations on silence |
| `vad.vad_onset_threshold` | `0.7` | Speech detection start (0.0-1.0) |
| `vad.vad_offset_threshold` | `0.55` | Speech detection end (0.0-1.0) |
| `vad.vad_min_speech_duration` | `0.1` | Min speech segment (seconds) |
| `vad.vad_realtime_enabled` | `true` | Auto-stop on silence |
| `vad.vad_silence_timeout_seconds` | `30.0` | Seconds before auto-stop |
| **Audio** |||
| `audio.host` | `null` | Audio API (WASAPI, Core Audio, etc.) |
| `audio.channels` | `1` | 1 = mono, 2 = stereo |
| `audio.dtype` | `float32` | float32/int16/int24/int32 |
| `audio.max_duration` | `900` | Max recording seconds (0 = unlimited) |
| `audio.input_device` | `default` | Device ID or "default" |
| **Clipboard** |||
| `clipboard.auto_paste` | `true` | false = clipboard only |
| `clipboard.paste_hotkey` | `ctrl+v` / `cmd+v` | Paste key simulation |
| `clipboard.preserve_clipboard` | `true` | Restore clipboard after paste |
| `clipboard.key_simulation_delay` | `0.05` | Delay between keystrokes (seconds) |
| **Logging** |||
| `logging.level` | `INFO` | DEBUG/INFO/WARNING/ERROR/CRITICAL |
| `logging.file.enabled` | `true` | Write to app.log |
| `logging.console.enabled` | `true` | Print to console |
| `logging.console.level` | `WARNING` | Console verbosity |
| **Audio Feedback** |||
| `audio_feedback.enabled` | `true` | Play sounds on record/stop |
| `audio_feedback.start_sound` | `assets/sounds/...` | Custom sound file path |
| `audio_feedback.stop_sound` | `assets/sounds/...` | Custom sound file path |
| `audio_feedback.cancel_sound` | `assets/sounds/...` | Custom sound file path |
| **System Tray** |||
| `system_tray.enabled` | `true` | Show tray icon |
| `system_tray.tooltip` | `Whisper Key` | Hover text |
| **Console** |||
| `console.start_hidden` | `false` | Start minimized to tray |

## 📁 Model Cache

Default path for transcription models (via HuggingFace):
- **Windows:** `%USERPROFILE%\.cache\huggingface\hub\`
- **macOS:** `~/.cache/huggingface/hub/`

## 📦 Dependencies

**Cross-platform:**
`faster-whisper` · `numpy` · `sounddevice` · `soxr` · `pyperclip` · `ruamel.yaml` · `pystray` · `Pillow` · `playsound3` · `ten-vad` · `hf-xet`

**Windows:** `global-hotkeys` · `pywin32` · `pyautogui`

**macOS:** `pyobjc-framework-Quartz` · `pyobjc-framework-ApplicationServices`
