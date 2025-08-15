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

### Option 2: Manual Installation
**Prerequisites for manual installation:**
- Python 3.8+ installed on Windows

Install the required Python packages:
```powershell
pip install -r requirements.txt
```

Or install manually:
```powershell
pip install faster-whisper numpy sounddevice global-hotkeys pyperclip ruamel.yaml pywin32 pyautogui pystray Pillow hf-xet
pip install git+https://github.com/TEN-framework/ten-vad.git@v1.0-ONNX
```

**Package descriptions:**
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

### Running the App

1. **Run the Full Application**:
   ```powershell
   python whisper-key.py
   ```

2. **Use the App**:
   - Press your configured hotkey (default: `Ctrl+Win`) to start recording
   - Speak clearly into your microphone  
   - Press the hotkey again to stop recording
   - The transcribed text is automatically pasted into the active application
   - Right click the system tray icon for basic settings

3. **Configuration** (Optional):
   - The app automatically creates a user settings file in `%APPDATA%\Roaming\whisperkey\user_settings.yaml` 
     - Change Whisper model size (tiny/base/small/medium/large)
     - Modify hotkeys
     - Configure automation (auto-paste, auto-ENTER)
     - And much more

## 🔧 Troubleshooting

- Check the log file `app.log` for detailed error messages
- Delete the user settings file in `%APPDATA%\Roaming\whisperkey\user_settings.yaml` and restart to reset to defaults
