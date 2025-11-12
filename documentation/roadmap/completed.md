# Windows Whisper Speech-to-Text App - Completed Stories

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

## Resolved Bugs

- Auto-pasting does not work in Notepad (Alt unfocuses text field) `[WON'T FIX]`