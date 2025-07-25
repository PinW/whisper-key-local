# Windows Whisper Speech-to-Text App

One global hotkey to start/stop recording, transcribe locally, and automatically paste the transcription wherever your cursor is.

## 🎯 Features

- **Global Hotkey**: Press `Ctrl+Tilde` from any application to start/stop recording
- **Local AI**: Uses Whisper AI running entirely on your computer (no internet required)
- **Automatic Pasting**: Transcribed text inserted where your cursor is as soon as it is processed
- **Automatic Clipboard**: Transcribed text is automatically copied for pasting with `Ctrl+V`
- **Privacy-First**: All processing happens locally - your voice data never leaves your computer

## 🚀 Quick Start

### Prerequisites
- Windows 10/11
- Python 3.8+ installed on Windows
- Microphone access

### Installation
Install the required Python packages:
```powershell
pip install faster-whisper sounddevice global-hotkeys pyperclip pyyaml pywin32 pyautogui
```

**Package descriptions:**
- `faster-whisper` - Fast AI speech recognition
- `sounddevice` - Audio recording
- `global-hotkeys` - System-wide hotkey detection  
- `pyperclip` - Clipboard operations
- `pyyaml` - Configuration file parsing
- `pywin32` - Windows API access for direct paste method
- `pyautogui` - Key simulation for Ctrl+V auto-paste (recommended for best compatibility)

### Running the App

1. **Run the Full Application**:
   ```powershell
   python main.py
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


**Hotkeys not working globally:**
- Try running PowerShell as Administrator
- Check for antivirus blocking global hotkey registration
- Use `python tools/key_helper.py` to test key detection
- Test different hotkey combinations in `test_hotkeys.py`

**Microphone not detected:**
- Check Windows microphone permissions
- Test with `test_audio.py` to isolate the issue
- Verify default recording device in Windows sound settings

**Whisper model download slow:**
- First run downloads the AI model (~39MB for tiny model)
- Subsequent runs are much faster
- Check internet connection for initial download

**Auto-paste not working:**
- Install `pyautogui` for key simulation: `pip install pyautogui`
- Try switching paste methods in `config.yaml`:
  - `paste_method: "key_simulation"` (works with most apps)
  - `paste_method: "windows_api"` (faster but less compatible)
- If both methods fail, set `auto_paste: false` to use manual clipboard pasting

### Testing Tools
1. Run `python tests/run_component_tests.py` to identify which component is failing
2. Check the log file `whisper_app.log` for detailed error messages
3. Test individual components with their respective test scripts

## 🔒 Privacy & Security

- All speech processing happens locally on your computer
- No internet connection required after initial model download
- No voice data is sent to external servers
- Transcriptions are only stored in clipboard temporarily