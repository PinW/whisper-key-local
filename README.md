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
- `pywin32` - Windows API access for direct paste method
- `pyautogui` - Key simulation for Ctrl+V auto-paste (recommended for best compatibility)
- `pystray` - System tray integration
- `Pillow` - Image processing for system tray icons
- `hf-xet` - Cache management for Hugging Face models
- `ten-vad` - Voice Activity Detection to prevent transcription of silent recordings

### Running the App

1. **Run the Full Application**:
   ```powershell
   python whisper-key.py
   ```

2. **Configuration** (Optional):
   - The app automatically creates a user settings file in `%APPDATA%\Roaming\whisperkey\user_settings.yaml` 
     - Change Whisper model size (tiny/base/small/medium/large)
     - Modify hotkey combination (use `python tools/key_helper.py` to find key combinations)
     - Configure auto-paste behavior and paste method
     - And much more

3. **Use the App**:
   - Press your configured hotkey (default: `Ctrl+Win`) to start recording
   - Speak clearly into your microphone  
   - Press the hotkey again to stop recording
   - The transcribed text is automatically pasted into the active application
   - If auto-paste is disabled, text is copied to clipboard for manual pasting with `Ctrl+V`

## 🔧 Troubleshooting

### Common Issues

**Microphone not detected:**
- Check Windows microphone permissions
- Test with `test_audio.py` to isolate the issue
- Verify default recording device in Windows sound settings

**Whisper model download slow:**
- First run downloads the AI model (74MB for base model up to 2.9GB for large)
- Models are cached locally for fast loading
- Use `python tools/clear_model_cache.py` to reset model cache

**Auto-paste not working:**
- Auto-paste uses key simulation by default
- Can try switching paste methods in your user settings file:
  - `paste_method: "key_simulation"` (works with most apps)
  - `paste_method: "windows_api"` (faster but not compatible with many apps)
- If both methods fail, set `auto_paste: false` to use manual clipboard pasting

### Testing Tools
- Run `python tests/run_component_tests.py` to identify which component is failing
- Check the log file `app.log` for detailed error messages
- Use `python tools/reset_user_settings.py` and restart app to reset to defaults
