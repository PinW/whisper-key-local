---
description: Build PyInstaller executable
argument-hint: "[-NoZip (faster, use for testing)] [-Test (run exe after build)]"
allowed-tools: Bash(powershell.exe:*), Bash(whisper-key.exe:*)
---
[FLAGS]=$ARGUMENTS

1. Build: `powershell.exe -ExecutionPolicy Bypass -File py-build/build-windows.ps1` (add -NoZip if in [FLAGS])
2. Watch for "Build successful!" message
3. Note the "Distribution Directory:" path from output

If -Test in [FLAGS]:
4. Convert dist path to bash-compatible format and run: `"<path>/whisper-key/whisper-key.exe" --test`
   - C:\Users\... → `"/mnt/c/Users/.../whisper-key.exe" --test`
   - \\wsl.localhost\Ubuntu\... → `"\\\\wsl.localhost\\Ubuntu\\...\\whisper-key.exe" --test`
5. Watch for "Application ready!" message (success) or errors
6. KillShell to terminate
7. Ignore exit code 137 (expected from KillShell)
