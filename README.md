# Whisper Key - Local Speech-to-Text for Windows

Global hotkey to start/stop recording and auto-paste transcription wherever your cursor is.

## 🎯 Features

- **Global Hotkey**: Press `Ctrl+Tilde` from any application to start/stop recording
- **Automatic Pasting**: Transcribed text inserted where your cursor is as soon as it is processed
- **Offline Capable**: Faster-whisper runs locally (no internet needed after setup)
- **Private Processing**: All processing happens locally, voice data never leaves your computer
- **Configurable**: Customize hotkeys, model, transcription actions, and audio settings

## 🚀 Quick Start

### Prerequisites
- Windows 10/11
- Python 3.8+ installed on Windows
- Microphone access

### Installation
Install the required Python packages:
```powershell
pip install -r requirements.txt
```

Or install manually:
```powershell
pip install faster-whisper numpy sounddevice global-hotkeys pyperclip ruamel.yaml pywin32 pyautogui pystray Pillow hf-xet
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

### Running the App

1. **Run the Full Application**:
   ```powershell
   python whisper-key.py
   ```

2. **Configuration** (Optional):
   - Edit `config.yaml` to customize settings:
     - Change Whisper model size (tiny/base/small)
     - Modify hotkey combination (use `python tools/key_helper.py` to find key combinations)
     - Configure auto-paste behavior:
       - `auto_paste: true/false` - Enable/disable automatic pasting
       - `paste_method: "key_simulation"/"windows_api"` - Choose paste method
     - Adjust audio settings
     - Configure logging preferences

3. **Use the App**:
   - Press your configured hotkey (default: `Ctrl+Tilde`) to start recording
   - Speak clearly into your microphone  
   - Press the hotkey again to stop recording
   - The transcribed text is automatically pasted into the active application
   - If auto-paste is disabled, text is copied to clipboard for manual pasting with `Ctrl+V`

## 🛠️ Configuration Tools

### Key Helper Utility
Use the key helper to find the right key combination for your hotkey:

```powershell
python tools/key_helper.py
```

This interactive tool will:
- Detect any key combination you press
- Show you the exact format to use in `config.yaml`
- Help you avoid conflicts with other applications

## 🔧 Troubleshooting

### Common Issues

**Microphone not detected:**
- Check Windows microphone permissions
- Test with `test_audio.py` to isolate the issue
- Verify default recording device in Windows sound settings

**Whisper model download slow:**
- First run downloads the AI model (39MB for tiny model up to 2.9GB for large)
- Models are cached locally for fast loading
- Use `python tools/clear_model_cache.py` to reset model cache

**Auto-paste not working:**
- Auto-paste uses key simulation by default
- Can try switching paste methods in `config.yaml`:
  - `paste_method: "key_simulation"` (works with most apps)
  - `paste_method: "windows_api"` (faster but not compatible with many apps)
- If both methods fail, set `auto_paste: false` to use manual clipboard pasting

### Testing Tools
- Run `python tests/run_component_tests.py` to identify which component is failing
- Check the log file `app.log` for detailed error messages
- Use `python tools/reset_user_settings.py` and restart app to reset to defaults
