# Windows Whisper Speech-to-Text App - Roadmap
@completed.md

## Bugs

## Next
- As a *developer*, I want **beginner comments removed** so that the code is forced to be readable and can be read easily
- As a *user*, I want **cancel recording action** so I can reset if I mess up too much without going through transcription and deleting what was pasted
- As a *user*, I want **audio recording length** so I can get a feel for transcription times
- As a *tester*, I want **PyPi** so I can easily install the app

### Recording Modes
- As a *user*, I want **recording mode option** (hold key vs start/stop) so that I can choose my preferred interaction style

## Backlog

### Packaging & Updates
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

## Keyword Controls
- As a *user* I want **auto-stop recording** so I don't need to hit the hotkey again when i'm lazy
- As a *user* I want **verbal stop recording** command si I don't need to hit the hotkey

### Voice Commands
- As a *user* I want **voice API** so I can do more than just transcribe voice
- As a *user* I want **voice commands** so I can quickly activate tasks

### Technical
- As a *developer* I want a **simplified config manager** so that DHH won't cry

### Learning & Code Exploration
- Try something out with **Python decorators** - explore using decorators for timing, caching, or retry logic in the codebase

### Cross-Platform
- As a Mac *user*, I want to use this app on **macOS**
- As a phone *user*, I want this app on **mobile**

### Transcription Quality
- As a *user*, I want to choose different **languages for transcription** to improve accuracy
- As a *user*, I want to add **custom words** to improve accuracy
- As a *user*, I want **automatic punctuation and text formatting** so the output is human-friendly (not just LLM)
- As a *user*, I want to see my **transcription history** so I can search through it

### Recording
- As a user, I want **real-time transcription** so that I can get immediate feedback