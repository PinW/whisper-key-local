# Whisper Key - Local Speech-to-Text

Global hotkey to start/stop recording and auto-paste transcription wherever your cursor is. Now on Windows and macOS!

Questions or ideas? [Discord Server](https://discord.gg/uZnXV8snhz)

## 🎯 Features

- **Global Hotkey**: Press `Ctrl+Win` to start recording, `Ctrl` to stop
- **Auto-Paste**: Transcription inserted at your cursor via auto-paste
- **Auto-Send**: Press `Alt` to stop, auto-paste, and auto-send with ENTER keypress
- **Offline Capable**: No internet required after models downloaded
- **Local Processing**: Voice data never leaves your computer
- **Voice activity detection**: Prevent hallucinations, auto-stop accidental hotkey presses
- **Configurable**: Customize hotkeys, models, and much more

## 🚀 Quick Start

| OS | Install Options |
|--|--|
| **Windows** | [Portable App](#portable-app-windows) &nbsp;·&nbsp; [pipx](#pipx-windows) |
| **macOS** | [pipx](#pipx-macos) |
| **Any** | [Development](#development) |

---

### Portable App (Windows)

1. [Download the latest release zip](https://github.com/PinW/whisper-key-local/releases/latest)
2. Extract the zip file
3. Run `whisper-key.exe`

### pipx (Windows)

Requires Python 3.11-3.13 and [pipx](https://pipx.pypa.io/)

```bash
pipx install whisper-key-local
whisper-key
```

### pipx (macOS)

Requires Python 3.11-3.13 and [pipx](https://pipx.pypa.io/)

```bash
pipx install whisper-key-local
whisper-key
```

### Development

Requires Python 3.11-3.13

```bash
git clone https://github.com/PinW/whisper-key-local.git
cd whisper-key-local
pip install -e .
python whisper-key.py
```

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

## 🎮 Basic Usage

- Boot the app, the "tiny" model will download and start
- Press `Ctrl+Win` to start recording
- Speak into your microphone  
- Press `Ctrl` to stop recording and transcribe
- The transcribed text is auto-pasted on your text cursor
- Alternatively press `Alt` to stop recording, auto-paste, and also send an ENTER keypress
- Right click the system tray icon to change models

### Configuration
The app automatically creates a user settings file in `%APPDATA%\Roaming\whisperkey\user_settings.yaml`, where you can:
- Change whisper model size (tiny/base/small/medium/large)
- Hotkeys
- Configure automation (auto-paste, auto-ENTER)
- Voice activity detection
- And much more

## 🔧 Troubleshooting

- Check the log file `app.log` for detailed error messages
- Delete the user settings file in `%APPDATA%/whisperkey/user_settings.yaml` and restart to reset to defaults
