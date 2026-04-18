Builds `whisper-key.exe` using [pyapp](https://github.com/ofek/pyapp) (Rust wrapper that bootstraps Python + pip install at first launch).

## Prerequisites

- Windows with Rust toolchain (`cargo`)
- [pyapp source](https://github.com/ofek/pyapp/releases/latest) extracted locally

## Setup

Copy `build-config.example.json` to `build-config.json` and set paths:
- `pyapp_source_path`: where you extracted pyapp source
- `dist_path`: output directory for built exe

## Build

Use `/build-pyapp-exe` or run directly:

```powershell
powershell.exe -ExecutionPolicy Bypass -File pyapp-build/build-pyapp.ps1
```

`-Clean` flag forces full Rust rebuild.

Produces two executables: `whisper-key.exe` (console) and `whisper-key-hideable.exe` (GUI subsystem, for start_hidden/minimize-to-tray).
