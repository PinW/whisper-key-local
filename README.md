# Whisper Key - Local Speech-to-Text for Windows

Global hotkey to start/stop recording and auto-paste transcription wherever your cursor is.

## 🎯 Features

- **Global Hotkey**: Press `Ctrl+Win` to start recording, `Ctrl` to stop
- **Auto-Paste**: Transcription inserted at your cursor via auto-paste
- **Auto-Send**: Press `Alt` to stop, auto-paste, and auto-send with ENTER keypress
- **Offline Capable**: No internet required after models downloaded
- **Local Processing**: Voice data never leaves your computer
- **Configurable**: Customize hotkeys, model, transcription actions, and audio settings

## 🚀 Quick Start

### Prerequisites
- Windows 10/11
- Microphone

### Option 1: Download Portable App
1. [Download the latest release zip](https://github.com/PinW/whisper-key-local/releases/latest)
2. Extract the zip file
3. Run `whisper-key.exe`

### Option 2: Install via pipx
**Prerequisites:**
- Python 3.8+ installed on Windows
- pipx installed (`pip install pipx`)

Install the application globally:
```powershell
pipx install whisper-key-local
```

Add VAD support (prevents silence hallucinations):
```powershell
pipx inject whisper-key-local git+https://github.com/TEN-framework/ten-vad.git@v1.0-ONNX
```

Run from anywhere:
```powershell
whisper-key
```

### Option 3: Development Installation
**Prerequisites:**
- Python 3.8+ installed on Windows

Clone the repository:
```powershell
git clone https://github.com/PinW/whisper-key-local.git
cd whisper-key-local
```

Install the dependencies:
```powershell
pip install -e .
```

Add VAD support (prevents silence hallucinations):
```powershell
pip install git+https://github.com/TEN-framework/ten-vad.git@v1.0-ONNX
```

Run the application:
```powershell
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
- Alternatively press `Alt` to stop recording, and 
- Right click the system tray icon to change models

### Configuration
The app automatically creates a user settings file in `%APPDATA%\Roaming\whisperkey\user_settings.yaml`, where you can:
- Change whisper model size (tiny/base/small/medium/large)
- Hotkeys
- Configure automation (auto-paste, auto-ENTER)
- And much more

## 🔧 Troubleshooting

- Check the log file `app.log` for detailed error messages
- Delete the user settings file in `%APPDATA%\Roaming\whisperkey\user_settings.yaml` and restart to reset to defaults
