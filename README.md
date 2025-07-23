# Windows Whisper Speech-to-Text App

A local speech-to-text application that runs OpenAI's Whisper AI on your computer. Press a hotkey anywhere in Windows to record speech, and the transcribed text is automatically copied to your clipboard for pasting in any application.

## 🎯 Features

- **Global Hotkey**: Press `Ctrl+Shift+Space` from any application to start/stop recording
- **Local AI**: Uses Whisper AI running entirely on your computer (no internet required)
- **Automatic Clipboard**: Transcribed text is automatically copied for pasting with `Ctrl+V`
- **Privacy-First**: All processing happens locally - your voice data never leaves your computer
- **Beginner-Friendly**: Extensively commented code for learning Python and AI concepts

## 🚀 Quick Start

### Prerequisites
- Windows 10/11
- Python 3.8+ installed on Windows (not WSL)
- Microphone access

### Installation
All required Python packages should already be installed:
- `faster-whisper` - Fast AI speech recognition
- `sounddevice` - Audio recording
- `global-hotkeys` - System-wide hotkey detection  
- `pyperclip` - Clipboard operations
- `pyyaml` - Configuration file parsing

### Running the App

1. **Test Components First** (Recommended for learning):
   ```powershell
   cd \\wsl$\Ubuntu\home\pin\whisper-key-local
   python tests/run_component_tests.py
   ```
   This runs individual tests for each component so you understand how they work.

2. **Run the Full Application**:
   ```powershell
   python main.py
   ```

3. **Configuration** (Optional):
   - Edit `config.yaml` to customize settings:
     - Change Whisper model size (tiny/base/small)
     - Modify hotkey combination (use `python tools/key_helper.py` to find key combinations)
     - Adjust audio settings
     - Configure logging preferences

4. **Use the App**:
   - Press your configured hotkey (default: `Ctrl+Shift+Space`) to start recording
   - Speak clearly into your microphone  
   - Press the hotkey again to stop recording
   - The transcribed text is copied to your clipboard
   - Paste anywhere with `Ctrl+V`

## 📚 Learning Guide

This project is designed for learning. Each component is explained in detail:

### Individual Component Tests
Run these to understand how each part works:

```powershell
python tests/component/test_clipboard.py    # Learn clipboard operations
python tests/component/test_audio.py        # Learn audio recording
python tests/component/test_whisper.py      # Learn AI transcription  
python tests/component/test_hotkeys.py      # Learn global hotkeys
```

### Code Architecture
- `main.py` - Application entry point and coordinator
- `src/audio_recorder.py` - Microphone recording with sounddevice
- `src/whisper_engine.py` - AI transcription with faster-whisper
- `src/hotkey_listener.py` - Global hotkey detection
- `src/clipboard_manager.py` - Clipboard copy/paste operations
- `src/state_manager.py` - Coordinates all components

## 🛠️ Development Setup

This project uses a hybrid WSL + Windows approach:
- **Development**: Files are edited in WSL
- **Execution**: Python runs on Windows (for system API access)
- **Execution Path**: Windows PowerShell navigates to WSL directory

### Why This Approach?
- WSL provides better development tools and file management
- Windows Python can access system APIs (microphone, hotkeys, clipboard)
- Best of both environments

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

**Import errors:**
- Ensure you're running Python from Windows, not WSL
- Verify all packages are installed in Windows Python environment

### Getting Help
1. Run `python tests/run_component_tests.py` to identify which component is failing
2. Check the log file `whisper_app.log` for detailed error messages
3. Test individual components with their respective test scripts

## 🎓 Learning Objectives

By studying this project, you'll learn:

1. **Python Application Architecture**
   - Modular design with separate responsibilities
   - Class-based programming
   - Error handling and logging

2. **Audio Processing**
   - Recording audio from microphone
   - Working with numpy arrays for audio data
   - Sample rates and audio formats

3. **AI Integration**
   - Using pre-trained AI models locally
   - Speech-to-text transcription
   - Model management and optimization

4. **System Integration**
   - Global hotkeys across applications
   - Clipboard operations
   - Background service patterns

5. **Threading and Concurrency**
   - Background audio recording
   - Non-blocking user interfaces
   - Coordinating multiple components

## 📈 Next Steps

After mastering the basics, consider these enhancements:

- **GUI Interface**: Add a system tray icon for visual feedback
- **Model Selection**: Allow switching between tiny/base/small models
- **Custom Hotkeys**: Add hotkey customization in settings
- **Language Support**: Add multi-language transcription
- **Voice Activity Detection**: Automatically start/stop on speech
- **Transcription History**: Save and search previous transcriptions

## 🔒 Privacy & Security

- All speech processing happens locally on your computer
- No internet connection required after initial model download
- No voice data is sent to external servers
- Transcriptions are only stored in clipboard temporarily

---

*This is a learning project designed to teach Python, AI integration, and system programming concepts through a practical, useful application.*