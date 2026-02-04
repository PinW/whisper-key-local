# Whisper Key - Local Speech-to-Text

Global hotkey to start/stop recording and auto-paste transcription wherever your cursor is.

**Now on Windows and macOS!**

Questions or ideas? [Discord](https://discord.gg/uZnXV8snhz)

## 🎯 Features

- **Global Hotkey**: Press `Ctrl+Win` to start recording, `Ctrl` to stop
- **Auto-Paste**: Transcription inserted at your cursor via auto-paste
- **Auto-Send**: Press `Alt` to stop, auto-paste, and auto-send with ENTER keypress
- **Offline Capable**: No internet required after models downloaded
- **Local Processing**: Voice data never leaves your computer
- **Voice activity detection**: Prevent hallucinations, auto-stop accidental hotkey presses
- **Configurable**: Customize hotkeys, models, and much more

## 🚀 Quick Start

### pipx (Recommended)

Requires Python 3.11-3.13 and [pipx](https://pipx.pypa.io/)

```bash
pipx install whisper-key-local
whisper-key
```

### Portable App (Windows only)

1. [Download the latest release zip](https://github.com/PinW/whisper-key-local/releases/latest)
2. Extract and run `whisper-key.exe`

### Development

Requires Python 3.11-3.13

```bash
git clone https://github.com/PinW/whisper-key-local.git
cd whisper-key-local
pip install -e .
python whisper-key.py
```

## 🎤 Basic Usage

- Boot the app, the "tiny" model will download and start
- Press `Ctrl+Win` to start recording
- Speak into your microphone
- Press `Ctrl` to stop recording and transcribe
- The transcribed text is auto-pasted on your text cursor
- Alternatively press `Alt` to stop recording, auto-paste, and also send an ENTER keypress
- Right click the system tray icon to change models

## ⚙️ Configuration

Settings and log files are stored at:
- **Windows:** `%APPDATA%\whisperkey\`
- **macOS:** `~/Library/Application Support/whisperkey/`

The app creates `user_settings.yaml` in this folder. Edit it to customize:
- Whisper model size (tiny/base/small/medium/large)
- Hotkeys
- Automation (auto-paste, auto-ENTER)
- Voice activity detection
- And much more

Delete `user_settings.yaml` and restart to reset to defaults.

## 📦 Package Dependencies

- `faster-whisper` - Fast AI speech recognition
- `numpy` - Numerical computing support
- `sounddevice` - Audio recording
- `global-hotkeys` - System-wide hotkey detection
- `pyperclip` - Clipboard operations
- `ruamel.yaml` - Configuration file parsing (YAML)
- `pyautogui` - Key simulation for Ctrl+V auto-paste and auto-ENTER
- `pywin32` - Windows API access for window management
- `pystray` - System tray integration
- `Pillow` - Image processing for system tray icons
- `hf-xet` - Cache management for Hugging Face models
- `ten-vad` - Voice Activity Detection to prevent silent hallucinations
