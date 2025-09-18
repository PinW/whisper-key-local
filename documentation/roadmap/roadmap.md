# Windows Whisper Speech-to-Text App - Roadmap
@completed.md

## Bugs

## Next
- As a *user* I want **lock output to window/field** so I don't need to click back into Claude Code terminal before start record
- As a *user* I want **config table in readme** so I can understand the types of functionality available before downloading

### Cross-Platform
- As a *mac user*, I want to use this app on **macOS**
    - As a *mac user*, I want 
    - As a *developer*, I want **removed window handle support** so I'll have one less Windows-dependant dependancy

## Backlog

### Packaging & Updates
- As a *user*, I want [**pyapp**](https://github.com/ofek/pyapp) so I can install without worrying about python/pip/etc
- As a *user*, I want **automatic updates** to get new features

### GUI
- As a *user*, I want **better icons** so that I can easily identify the app state in the system tray
- As a *user*, I want a **GUI interface** so that I can change settings without editing files:
- Settings
    - Hotkey management
    - Model management
        - progress bar for downloading
    - Paste mode
        - Preserve clipboard as sub-option (auto-paste only)
    - Language

### Transcription History
- As a *user* I want a **transcriptions log** so I can review my past transcriptions and look at accidental cancels or overwrites

### VAD & Keyword Controls
- As a *user* I want **verbal stop recording** command so I don't need to hit the hotkey

### Voice Commands
- As a *user* I want **voice API** so I can do more than just transcribe voice
- As a *user* I want **voice commands** so I can quickly activate tasks

### Meeting Mode
- As a *user* I want **meeting mode** so I can transcribe an entire meeting in real-time

### Technical
- As a *developer*, I want **end-to-end tests** so that I can refactor with confidence

### Cross-Platform
- As a phone *user*, I want this app on **mobile**

### Transcription Quality
- As a *user*, I want **parakeet models** so I can get transcriptions faster wit more accuracy
- As a *user*, I want to choose different **languages for transcription** to improve accuracy
- As a *user*, I want to add **custom words** to improve accuracy
- As a *user*, I want **automatic punctuation and text formatting** so the output is human-friendly (not just LLM)
- As a *user*, I want to see my **transcription history** so I can search through it

### Recording
- As a *user*, I want **real-time transcription** so that I can get immediate feedback

### Developer Use Cases
- As a *developer* I want **project file context** so I can reference files in voice and tag them in chats hands free