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

| Hotkey | Windows | macOS |
|--------|---------|-------|
| Start recording | `Ctrl+Win` | `Fn+Ctrl` |
| Stop & transcribe | `Ctrl` | `Fn` |
| Stop & auto-send | `Alt` | `Option` |
| Cancel recording | `Esc` | `Shift` |

Right-click the system tray / menu bar icon to:
- Toggle auto-paste vs clipboard-only
- Change transcription model
- Select audio device

## ⚙️ Configuration

`user_settings.yaml` and `app.log` are stored at:
- **Windows:** `%APPDATA%\whisperkey\`
- **macOS:** `~/Library/Application Support/whisperkey/`

Edit `user_settings.yaml` to customize:
- Whisper model size (tiny/base/small/medium/large)
- Hotkeys
- Automation (auto-paste, auto-ENTER)
- Voice activity detection
- And much more

Delete `user_settings.yaml` and restart to reset to defaults.

## 📦 Dependencies

**Cross-platform:**
`faster-whisper` · `numpy` · `sounddevice` · `soxr` · `pyperclip` · `ruamel.yaml` · `pystray` · `Pillow` · `playsound3` · `ten-vad` · `hf-xet`

**Windows:** `global-hotkeys` · `pywin32` · `pyautogui`

**macOS:** `pyobjc-framework-Quartz` · `pyobjc-framework-ApplicationServices`
