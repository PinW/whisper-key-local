# Whisper Key Local - Roadmap
@completed.md

## Bugs
- **Ctrl+C doesn't work during HuggingFace download** - shutdown signal not caught while model is downloading
- **(macOS) System freezes on transcription** - needs verification
- **CUDA 13.1 fails** - `cublas64_12.dll` is not found or cannot be loaded

## Next
- As a *user* I want **support for more hotkeys** (F13-F24, Insert) so I can use StreamDeck or AutoHotkey triggers (#14)
- As a *user* I want **lock output to window/field** so I don't need to click back into Claude Code terminal before start record
- As a *user* I want **config table in readme** so I can understand the types of functionality available before downloading
- As a *user*, I want to add **custom words** so rare words that I say often are translated accurately
- As a *contributor* I want a **LICENSE** so I know the terms for using and contributing

## Backlog

### macOS
- As a *mac user*, I want **better default hotkey** so fn doesn't conflict with emoji picker
- As a *mac user*, I want **CGEventTap hotkeys** so I can use ESC or Cmd+. to cancel recording
- As a *mac user*, I want **monochrome menu bar icons** so the app conforms to Apple's template icon guidelines

### Onboarding
- As a *new user* I want **first-run onboarding** so I can configure model, audio device, and auto-paste without editing YAML
  - As a *new user* I want **model selection** so I can choose a Whisper model that balances speed vs accuracy without editing YAML
  - As a *new user* I want **auto NVIDIA GPU detection** so CUDA mode is enabled automatically when a compatible GPU is available
  - As a *new user* I want **CPU/GPU selection** so I can use my NVIDIA GPU for faster transcription or fall back to CPU
  - As a *new user* I want **audio device selection** so I can pick my preferred microphone from a list of detected devices
  - As a *new user* I want **language selection** so I can set my transcription language without editing YAML
  - As a *new user* I want **system tray preference** so I can decide whether to show the tray icon or run in background
  - As a *new user* I want **auto-paste preference** so I can choose between direct paste or clipboard-only mode
  - As a *new user* I want **auto-set key simulation delay based on machine specs** so slower computers don't miss keystrokes during auto-paste ([#21](https://github.com/PinW/whisper-key-local/issues/21))
  - As a *new user* I want **onboarding re-run option** so I can reconfigure settings by resetting onboarding_complete

### Transcription History
- As a *user* I want a **transcriptions log** so I can review my past transcriptions and look at accidental cancels or overwrites

### Voice Commands
- As a *user* I want **voice commands API** so I can do more than just transcribe voice
- As a *user* I want **voice commands** so I can quickly activate tasks
- As a *user* I want **verbal stop recording** command so I don't need to hit the hotkey

### Packaging & Updates
- As a *user*, I want [**pyapp**](https://github.com/ofek/pyapp) so I can install without worrying about python/pip/etc
  - As a *developer*, I want **pyapp** so I can avoid PyInstaller's fragile build process and hidden import headaches
- As a *user*, I want **automatic updates** to get new features
- As a *user*, I want **config version tracking with auto-reset on breaking changes** so my settings don't cause errors after major updates ([#22](https://github.com/PinW/whisper-key-local/issues/22))

### Terminal UI
- As a *user* I want **on-screen hotkey hints** so I can see available controls at a glance like a video game HUD
- As a *user*, I want a **terminal UI** so I can control the app without leaving the command line
- As a *user*, I want a **terminal status bar** so I can see app state, model, and recording status at a glance
- As a *user*, I want **terminal colors and styling** so the CLI feels modern like coding tools (Claude Code, lazygit)
- As a *user*, I want **terminal settings control** so I can change settings interactively without editing YAML
  - As a *user* I want **language selection in CLI** so I can switch transcription language without editing YAML
- As a *user*, I want a **cleaner model download display** so I see progress without HuggingFace cluttering the terminal

### CLI
- As a *user* I want a **CLI interface** so other tools and agents can invoke transcription programmatically

### Desktop App
- As a *user*, I want a **desktop GUI** so that I can change settings without editing files

### Real-Time Transcription
- As a *user* I want **real-time transcription** so I can preview text as I speak
- As a *user* I want **meeting mode** so I can transcribe an entire meeting in real-time

### Cross-Platform
- As a phone *user*, I want this app on **mobile**

### Transcription Quality
- As a *user*, I want **parakeet models** so I can get transcriptions faster wit more accuracy
- As a *user*, I want **automatic punctuation and text formatting** so the output is human-friendly (not just LLM)
- As a *user*, I want to see my **transcription history** so I can search through it

### Recording
- As a *user* I want **hotkey-per-audio-source bindings** so I can quickly switch between microphone input and speaker/system audio capture
- As a *user*, I want **real-time transcription** so that I can get immediate feedback

### Developer Use Cases
- As a *developer* I want **project file context** so I can reference files in voice and tag them in chats hands free

### Agent & API Integration
- As a *user* I want **server mode** so I can run transcription on one machine and send audio/receive text from other devices on my LAN (centralized processing for multiple users)
- As a *user* I want **headless/API input mode** so I can receive audio from external sources instead of local microphone
- As a *user* I want **headless/API output mode** so transcriptions can be sent to external services instead of clipboard
- As a *user* I want to **send transcriptions to CLI agents** (Claude Code, Codex, etc.) so I can voice-control coding assistants
- As a *user* I want **Telegram bot integration** so I can transcribe voice messages for bots like OpenClaw

### Discord Integration
- As a *user* I want to **transcribe and post commands to CLI agent at home** so I can control my home server remotely via Discord
- As a *user* I want a **Discord bot for voice commands** so I can trigger actions remotely with my voice
- As a *user* I want to **listen for commands from multiple users** so a shared server can accept voice input from authorized people