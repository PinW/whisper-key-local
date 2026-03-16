---
description: Manage local pyapp venv (status, editable install, reset)
argument-hint: "<status|install|reset> [worktree-path]"
allowed-tools: Bash(powershell.exe:*), Bash(whisper-key.exe:*), Bash(ls:*), Bash(cat:*)
---
[ACTION]=$ARGUMENTS

Pyapp venv lives at: `%LOCALAPPDATA%\pyapp\data\whisper-key-local\<hash>\<version>\`
The exe path comes from `pyapp-build/build-config.json` → `dist_path` field (append `\whisper-key.exe`).
Convert Windows path to WSL: `C:\Users\...` → `/mnt/c/Users/.../`

## Actions

### status (default if no action given)
1. Read `pyapp-build/build-config.json` to get dist_path for the exe location
2. Find venv: `powershell.exe -Command "Get-ChildItem -Path \"$env:LOCALAPPDATA\pyapp\data\whisper-key-local\" -Recurse -Directory | Where-Object { Test-Path (Join-Path $_.FullName 'Scripts\python.exe') } | Select-Object -ExpandProperty FullName"`
3. Show installed package info: run `"<exe-wsl-path>" self pip show whisper-key-local`
4. Check if editable: Location field shows source path if editable, site-packages if normal install
5. Report: venv path, installed version, editable or not, which source path if editable

### install [worktree-path]
Installs current worktree (or specified path) as editable into the pyapp venv.
1. Read `pyapp-build/build-config.json` to get dist_path for the exe location
2. Determine source path:
   - If worktree-path given in [ACTION]: use it
   - Otherwise: use current working directory
3. Convert to Windows path if needed (WSL `/home/...` → `\\wsl.localhost\Ubuntu\home\...`)
4. Run: `"<exe-wsl-path>" self pip install -e <windows-source-path>`
5. Verify with `"<exe-wsl-path>" self pip show whisper-key-local`

### reset
Nukes the pyapp venv so next launch re-creates it from PyPI.
1. Confirm with user before proceeding
2. Delete the venv: `powershell.exe -Command 'Remove-Item -Path "$env:LOCALAPPDATA\pyapp\data\whisper-key-local" -Recurse -Force'`
3. Verify deleted: `powershell.exe -Command 'Test-Path "$env:LOCALAPPDATA\pyapp\data\whisper-key-local"'` should return False
4. Report completion — next exe launch will bootstrap fresh
