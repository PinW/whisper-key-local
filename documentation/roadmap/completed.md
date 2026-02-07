# Whisper Key - Completed Stories

- As a *user*, I want **audio recording length** so I can get a feel for transcription times
- As a *user*, I want **distinct cancel sound** so I can immediately tell when I cancelled vs stopped recording
- As a *developer*, I want **beginner comments removed** so that the code is forced to be readable and can be read easily
- As a *developer* I want a **simplified config manager** so that DHH won't cry
- As a *deveoper*, I want **github release** so that users can download a zip package
- As a *developer*, I want **CHANGELOG.md** so I can track progress across releases
- As a *developer*, I want **version management** so that I can release the app
- As a *user*, I want **1 instance running limit** so I won't double transcribe
- As a *user*, I want **VAD pass** so silences aren't transformed into 20 word hallucination
- As a *user*, I want **better default model** so I won't get low quality STT as 1st xp
- As a *user*, I want **auto-send** so I don't need to hit ENTER for chat/LLM use cases
- As a *user*, I want **multiple hotkeys** so I can utilize different recording modes without changing settings
- As a *user*, I want a **Windows executable installer** so I can install without setting up python and depdencies
- As a *user*, I want **Start Menu launch compatibility** so the app works when launched from Windows Start Menu
- As a *user*, I want **cancel recording action** so I can reset if I mess up too much without going through transcription and deleting what was pasted
- As a *tester*, I want **PyPI** so I can easily install the app
- As a *user* I want **auto-stop recording** so I won't record to the limit when I accidentally turn it on or forget it is on
- As a *user*, I want to **hide the console window** so the app runs cleanly in the background ([#8](https://github.com/PinW/whisper-key-local/issues/8))
- As a *user*, I want to **select audio source** so I can transcribe from different microphones or system audio ([#12](https://github.com/PinW/whisper-key-local/issues/12))
- As a *developer*, I want to **WASAPI loopback supported out of the box** so I can implement features like meeting transcription based on audio outputs
- As a *user*, I want to **load custom local models** so I can use specialized or fine-tuned models ([#10](https://github.com/PinW/whisper-key-local/issues/10))
- As a *user*, I want **shortcuts to access log and settings** in the systray menu so I can quickly troubleshoot issues ([#9](https://github.com/PinW/whisper-key-local/issues/9))
- As a *mac user*, I want **Fn key as modifier** so I can use the ergonomic bottom-left corner for recording
- As a *user*, I want to choose different **languages for transcription** so that I can get a free/passive accuracy boost
- As a *developer*, I want **WASAPI support without scipy** so that the package is smaller and more efficient
- As a *user*, I want **better icons** so that I can easily identify the app state in the system tray
- As a *user* I want **support for more hotkeys** (F13-F24, Insert) so I can use StreamDeck or AutoHotkey triggers ([#14](https://github.com/PinW/whisper-key-local/issues/14))
- As a *user* I want **config table in readme** so I can understand the types of functionality available before downloading
- As a *contributor* I want a **LICENSE** so I know the terms for using and contributing
- As a *user* I want **AMD GPU support** so I can use my AMD GPU for faster transcription via ROCm
- As a *user* I want **distil-whisper models** so I get faster transcription with a smaller download

## Resolved Bugs

- Auto-pasting does not work in Notepad (Alt unfocuses text field) `[WON'T FIX]`