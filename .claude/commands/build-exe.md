---
description: Build PyInstaller executable
argument-hint: "[-NoZip] - skip zip creation for testing"
allowed-tools: Bash(powershell.exe:*)
---

1. Build: `powershell.exe -ExecutionPolicy Bypass -File py-build/build-windows.ps1 $ARGUMENTS`
2. Watch for "Build successful!" message
3. Note the "Distribution Directory:" path from output
4. If successful, test exe startup: `<dist-path>\whisper-key\whisper-key.exe --test`
5. Watch for "Application ready!" message (success) or errors
6. KillShell to terminate, tell user to close from tray
7. Ignore exit code 137 (expected from KillShell)
