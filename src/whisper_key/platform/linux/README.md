# Linux Platform Files

Each file implements something that differs between Linux, macOS, and Windows.

| File | Why it exists |
|------|---------------|
| `hotkeys.py` | Global hotkey capture via X RECORD extension (python-xlib). |
| `keycodes.py` | Maps key names (`ctrl`, `space`, etc.) to X11 keycodes. |
| `keyboard.py` | Simulates key presses for paste/type output via X11 XTest extension. |
| `paths.py` | App data at `~/.whisperkey`, file opener via `xdg-open`. |
| `instance_lock.py` | Prevents running two copies via `fcntl.flock`. |
| `app.py` | Event loop and raw terminal input via `termios`. |
| `permissions.py` | Stub — accessibility permission always returns `True` on Linux. |
| `gpu.py` | GPU detection via `lspci`, `rocminfo`, `nvidia-smi`. |
| `console.py` | Stub — console hide/show are no-ops on Linux. |
| `icons.py` | Tray icon loading from PNG assets. |
