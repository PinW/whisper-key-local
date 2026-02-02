---
description: Test app startup from WSL
allowed-tools: Bash(python.exe:*)
---

Scope: Verify app launches without errors. No interaction testing (hotkeys, tray, etc).

1. Run: `python.exe <windows-path-to-whisper-key.py> --test`
2. Watch output for "Application ready!" message (success) or errors
3. Use KillShell to terminate
4. Ignore exit code 137 (expected from KillShell) - don't mention it

Example: `python.exe \\\\wsl.localhost\\Ubuntu\\home\\user\\whisper-key-local\\whisper-key.py --test`
