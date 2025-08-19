*Learning project for beginner coder: explain concepts in conversation (not in comments)*

@documentation/project-index.md

- Build PyInstaller: `powershell.exe -ExecutionPolicy Bypass -File /home/pin/whisper-key-local/py-build/build-windows.ps1` optional:`-NoZip`
- Build PyPI: `powershell.exe -Command "python -m build"`
- DO NOT TEST! You are in WSL, app runs on Windows
- Ask user to test before committing
- Prefer elegant code that is modular and consistent
- Use clear variable/function names
- AVOID COMMENTS IF AT ALL POSSIBLE! DO NOT WRITE DOCSTRINGS!
- We are in ALPHA, don't bother with backward compatibility or too much testing
- When I say "to temp": `documentation/temp/`
