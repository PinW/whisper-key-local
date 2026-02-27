# WSL Hotkey Shim: Windows-Side Hotkey Bridge for WSL-Side App

**Date:** 2026-02-16
**Status:** Research Complete
**Scope:** Architecture for a Windows-side hotkey shim communicating with a WSL-side Python app

---

## 1. Executive Summary

A WSL hybrid approach is **viable and practical**. The recommended architecture:

- **WSL side:** Main Python app (audio capture, transcription, state management)
- **Windows side:** Tiny Python script using `ctypes` + `RegisterHotKey` that sends hotkey events over **localhost TCP** to the WSL app

**Recommended IPC:** Localhost TCP socket (port on 127.0.0.1). This is the simplest, most reliable, and best-documented mechanism for WSL2-to-Windows communication. AF_UNIX sockets do NOT work cross-platform in WSL2. Named pipes are not directly accessible. stdin/stdout pipes via WSL interop have known reliability issues.

**Recommended shim:** A single-file Python script (~60 lines) using only `ctypes` (zero dependencies). The WSL-side app spawns it via `python.exe` through WSL interop. No compilation, no extra runtimes.

**Key insight for the wrapping use case** (`wk claude`): We don't need system clipboard or key simulation at all. Transcribed text is written directly to the wrapped subprocess's stdin. The only Windows-side component needed is the hotkey listener.

---

## 2. IPC Mechanism Comparison

### 2.1 Localhost TCP (Recommended)

| Aspect | Detail |
|--------|--------|
| **How it works** | WSL app listens on `127.0.0.1:<port>`, Windows shim connects and sends hotkey events |
| **WSL2 support** | Works out of the box in NAT mode (WSL-listening, Windows-connecting) |
| **Mirrored mode** | Bidirectional localhost works; even better but not required |
| **Reliability** | Very reliable for local connections; no known issues for short-lived messages |
| **Complexity** | ~10 lines each side using Python `socket` stdlib |
| **Latency** | Sub-millisecond for localhost |
| **Firewall** | No firewall rules needed for localhost loopback |

**Direction matters in NAT mode:** A WSL2 process listening on a port is automatically forwarded to Windows localhost by the `localhost` relay process. So the WSL app should be the **server** and the Windows shim should be the **client**.

In mirrored mode (`networkingMode=mirrored` in `.wslconfig`), either direction works via 127.0.0.1. Mirrored mode is available on Windows 11 22H2+.

### 2.2 stdin/stdout Pipes (via WSL Interop)

| Aspect | Detail |
|--------|--------|
| **How it works** | WSL spawns `python.exe shim.py` via `subprocess.Popen` with `PIPE` |
| **WSL2 support** | Works but has known reliability issues |
| **Reliability** | Historical bugs with stdin/stdout marshalling (Issue #2406, #3160, #6547). Fixed in newer builds but some edge cases remain |
| **Complexity** | Simplest setup (no port allocation), but error handling is harder |
| **Latency** | Very low |
| **Risk** | Pipe can break silently; harder to detect and recover |

**Verdict:** Workable as a fallback but TCP is more robust.

### 2.3 AF_UNIX Sockets (Cross-Platform)

| Aspect | Detail |
|--------|--------|
| **WSL1** | Works via DrvFS paths (`/mnt/c/...`) |
| **WSL2** | **Does NOT work.** `OSError: [Errno 95] Operation not supported` (Issue #5961, open since Sept 2020, still unfixed as of Feb 2024) |

**Verdict:** Not viable for WSL2.

### 2.4 Windows Named Pipes

| Aspect | Detail |
|--------|--------|
| **Direct access** | Not available from WSL2 |
| **Via npiperelay** | Requires extra tool (npiperelay + socat), significant complexity |
| **Microsoft's position** | "Socket is the documented way to bridge Win32 and WSL side. Pipe is hidden." |

**Verdict:** Not recommended. Over-engineered for this use case.

### 2.5 Summary

| Mechanism | WSL2 Works | Reliability | Complexity | Recommendation |
|-----------|-----------|------------|------------|----------------|
| **Localhost TCP** | Yes | High | Low | **Use this** |
| stdin/stdout | Yes* | Medium | Low | Fallback option |
| AF_UNIX | No | N/A | N/A | Not viable |
| Named pipes | No (direct) | N/A | High | Not recommended |

---

## 3. Windows Hotkey Shim Implementation Options

### 3.1 Python + ctypes (Recommended)

**Zero dependencies.** Uses only `ctypes` from the Python stdlib to call Win32 `RegisterHotKey` API. Runs via the Windows-native `python.exe`.

Advantages:
- No compilation step
- No extra installs (Python is already on the system for the main app)
- Easy to update hotkey config dynamically
- Single file, ~60 lines
- Communicates back to WSL over TCP

### 3.2 AutoHotKey Script (compiled to .exe)

Advantages:
- Native global hotkey support
- Can compile to tiny .exe via Ahk2Exe
- Built-in TCP socket support via DllCall to Ws2_32.dll

Disadvantages:
- Requires AutoHotKey runtime or compilation step
- Another language to maintain
- Less control over protocol format

### 3.3 Compiled Executable (C/Rust/Go)

Advantages:
- Smallest binary size
- No runtime dependencies

Disadvantages:
- Requires build toolchain
- More complex to modify
- Overkill for this use case

### 3.4 PowerShell Script

Advantages:
- Ships with Windows, no extra install

Disadvantages:
- Awkward Win32 API access (requires Add-Type with C# inline)
- Slow startup
- Poor developer experience

### 3.5 Recommendation

**Python + ctypes** wins decisively. The user already has `python.exe` installed on Windows for the build environment. Zero new dependencies. Easy to maintain alongside the main Python codebase.

---

## 4. Shim Code Sketch

### 4.1 Windows-Side Shim (`hotkey_shim.py`)

This runs via `python.exe` on the Windows side. Pure stdlib, zero dependencies:

```python
import sys
import json
import socket
import ctypes
from ctypes import wintypes

user32 = ctypes.windll.user32

WM_HOTKEY = 0x0312
MOD_ALT = 0x0001
MOD_CONTROL = 0x0002
MOD_SHIFT = 0x0004
MOD_WIN = 0x0008
MOD_NOREPEAT = 0x4000

MODIFIER_MAP = {
    'alt': MOD_ALT,
    'ctrl': MOD_CONTROL,
    'control': MOD_CONTROL,
    'shift': MOD_SHIFT,
    'win': MOD_WIN,
    'windows': MOD_WIN,
    'super': MOD_WIN,
}

def parse_hotkey(hotkey_str):
    parts = [p.strip().lower() for p in hotkey_str.split('+')]
    modifiers = 0
    vk = 0
    for part in parts:
        if part in MODIFIER_MAP:
            modifiers |= MODIFIER_MAP[part]
        elif len(part) == 1:
            vk = ord(part.upper())
        elif part.startswith('f') and part[1:].isdigit():
            vk = 0x70 + int(part[1:]) - 1  # VK_F1 = 0x70
        elif part == 'escape' or part == 'esc':
            vk = 0x1B
        elif part == 'space':
            vk = 0x20
    return modifiers | MOD_NOREPEAT, vk


def main():
    port = int(sys.argv[1])
    hotkeys_json = sys.argv[2]
    hotkeys = json.loads(hotkeys_json)

    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.connect(('127.0.0.1', port))

    for i, hk in enumerate(hotkeys):
        modifiers, vk = parse_hotkey(hk['combination'])
        if not user32.RegisterHotKey(None, i + 1, modifiers, vk):
            sock.sendall(json.dumps({'error': f'Failed to register: {hk["combination"]}'}).encode() + b'\n')
            return

    sock.sendall(json.dumps({'status': 'ready'}).encode() + b'\n')

    try:
        msg = wintypes.MSG()
        while user32.GetMessageA(ctypes.byref(msg), None, 0, 0) != 0:
            if msg.message == WM_HOTKEY:
                hotkey_id = msg.wParam
                if 1 <= hotkey_id <= len(hotkeys):
                    event = {'hotkey': hotkeys[hotkey_id - 1]['name']}
                    sock.sendall(json.dumps(event).encode() + b'\n')
            user32.TranslateMessage(ctypes.byref(msg))
            user32.DispatchMessageA(ctypes.byref(msg))
    finally:
        for i in range(len(hotkeys)):
            user32.UnregisterHotKey(None, i + 1)
        sock.close()


if __name__ == '__main__':
    main()
```

### 4.2 WSL-Side Listener (in the platform module)

```python
import json
import socket
import subprocess
import threading
import logging

class WslHotkeyBridge:
    def __init__(self, hotkey_bindings, python_exe='python.exe'):
        self.logger = logging.getLogger(__name__)
        self.hotkey_bindings = hotkey_bindings
        self.python_exe = python_exe
        self.server_socket = None
        self.client_socket = None
        self.shim_process = None
        self.listener_thread = None
        self.running = False

    def start(self):
        self.server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.server_socket.bind(('127.0.0.1', 0))
        port = self.server_socket.getsockname()[1]
        self.server_socket.listen(1)

        hotkeys_config = json.dumps([
            {'combination': b[0], 'name': f'hotkey_{i}'}
            for i, b in enumerate(self.hotkey_bindings)
        ])

        shim_path = self._get_shim_windows_path()
        self.shim_process = subprocess.Popen(
            [self.python_exe, shim_path, str(port), hotkeys_config]
        )

        self.client_socket, _ = self.server_socket.accept()

        ready_line = self._read_line()
        ready_msg = json.loads(ready_line)
        if 'error' in ready_msg:
            raise RuntimeError(f"Shim failed: {ready_msg['error']}")

        self.running = True
        self.listener_thread = threading.Thread(target=self._listen_loop, daemon=True)
        self.listener_thread.start()

    def _listen_loop(self):
        buffer = ''
        while self.running:
            data = self.client_socket.recv(4096)
            if not data:
                break
            buffer += data.decode()
            while '\n' in buffer:
                line, buffer = buffer.split('\n', 1)
                event = json.loads(line)
                self._dispatch_hotkey(event['hotkey'])

    def _dispatch_hotkey(self, hotkey_name):
        idx = int(hotkey_name.split('_')[1])
        if idx < len(self.hotkey_bindings):
            callback = self.hotkey_bindings[idx][1]
            if callback:
                callback()

    def _read_line(self):
        buffer = ''
        while '\n' not in buffer:
            data = self.client_socket.recv(4096)
            buffer += data.decode()
        return buffer.split('\n')[0]

    def _get_shim_windows_path(self):
        # Convert WSL path to Windows path for python.exe
        # The shim file lives alongside the package
        pass  # Implementation depends on package layout

    def stop(self):
        self.running = False
        if self.shim_process:
            self.shim_process.terminate()
        if self.client_socket:
            self.client_socket.close()
        if self.server_socket:
            self.server_socket.close()
```

### 4.3 Protocol

Newline-delimited JSON over TCP:

```
WSL app -> (spawns) -> python.exe hotkey_shim.py <port> <hotkeys_json>
Shim    -> WSL app:    {"status": "ready"}\n
Shim    -> WSL app:    {"hotkey": "hotkey_0"}\n     (on each hotkey press)
Shim    -> WSL app:    {"hotkey": "hotkey_1"}\n
Shim    -> WSL app:    {"error": "..."}\n           (on failure)
```

---

## 5. Spawning the Shim from WSL

### 5.1 WSL Interop (Direct Execution)

WSL2 can run Windows executables directly thanks to binfmt interop. The kernel intercepts `.exe` launches via a registered binfmt interpreter (`/init`), which creates a bridge to Windows process creation.

```python
import subprocess

# Direct execution of Windows Python
proc = subprocess.Popen(
    ['python.exe', 'C:\\path\\to\\hotkey_shim.py', '12345', '...'],
    # No PIPE needed since we communicate over TCP
)
```

Key considerations:
- `python.exe` must be on the Windows PATH (or use full path like `/mnt/c/Users/.../python.exe`)
- The shim script must be on a Windows-accessible path (DrvFS, e.g., `/mnt/c/...`)
- No stdin/stdout pipes needed since IPC is over TCP
- The process runs as a Windows process but is a child of the WSL process

### 5.2 Path Translation

The shim `.py` file must be accessible from Windows. Options:

1. **Store on DrvFS:** Place the shim at `/mnt/c/Users/<user>/AppData/Local/whisperkey/hotkey_shim.py`. Windows sees `C:\Users\<user>\AppData\Local\whisperkey\hotkey_shim.py`.

2. **Use `wslpath`:** Convert WSL paths to Windows paths at runtime:
   ```python
   import subprocess
   win_path = subprocess.check_output(['wslpath', '-w', '/home/pin/shim.py']).decode().strip()
   # Returns: \\wsl.localhost\Ubuntu\home\pin\shim.py
   ```

3. **UNC path:** Windows can access WSL files via `\\wsl.localhost\<distro>\path`. However, this is slower and less reliable than DrvFS.

**Recommendation:** Copy the shim to a DrvFS path on first run, or store it in the Windows AppData directory.

### 5.3 Finding python.exe

```python
import shutil
import subprocess

# Option 1: Check PATH
python_exe = shutil.which('python.exe')

# Option 2: Use where.exe via WSL interop
result = subprocess.run(['where.exe', 'python'], capture_output=True, text=True)
python_path = result.stdout.strip().split('\n')[0]

# Option 3: Well-known paths
PYTHON_CANDIDATES = [
    '/mnt/c/Python312/python.exe',
    '/mnt/c/Python311/python.exe',
    '/mnt/c/Users/*/AppData/Local/Programs/Python/Python3*/python.exe',
]
```

---

## 6. WSL Environment Detection

### 6.1 Detecting WSL

```python
import os
import platform

def detect_wsl():
    if platform.system() != 'Linux':
        return None

    try:
        with open('/proc/version', 'r') as f:
            version = f.read().lower()
    except FileNotFoundError:
        return None

    if 'microsoft-standard-wsl2' in version:
        return 'wsl2'
    elif 'microsoft' in version:
        return 'wsl1'
    return None

def is_wsl():
    return detect_wsl() is not None

def is_wsl2():
    return detect_wsl() == 'wsl2'
```

Secondary checks:
- `$WSL_DISTRO_NAME` environment variable (injected by WSL, but may be absent after `su`)
- `$WSL_INTEROP` environment variable (present in WSL2)
- `/mnt/wslg/` directory existence (indicates WSLg is available)

### 6.2 Detecting WSLg

```python
import os

def has_wslg():
    return os.path.exists('/mnt/wslg/')

def has_wslg_audio():
    return os.path.exists('/mnt/wslg/PulseServer')

def has_wslg_display():
    return os.environ.get('WAYLAND_DISPLAY') is not None or os.environ.get('DISPLAY') is not None
```

### 6.3 Platform Detection Integration

Current `platform/__init__.py` only handles Windows vs macOS. For WSL:

```python
import platform as _platform

PLATFORM = 'macos' if _platform.system() == 'Darwin' else 'windows'

# Future extension:
if _platform.system() == 'Linux':
    wsl_version = detect_wsl()
    if wsl_version:
        PLATFORM = 'wsl'
    else:
        PLATFORM = 'linux'

IS_MACOS = PLATFORM == 'macos'
IS_WINDOWS = PLATFORM == 'windows'
IS_WSL = PLATFORM == 'wsl'
IS_LINUX = PLATFORM == 'linux'
```

---

## 7. Audio in WSL

### 7.1 Architecture

WSL2 has no native ALSA sound cards. WSLg exposes audio via PulseAudio over RDP:
- **RDPSink** - audio playback (sound effects)
- **RDPSource** - audio capture (microphone)

The audio path: Microphone -> Windows -> RDP -> WSLg PulseAudio -> ALSA shim -> PortAudio -> sounddevice

### 7.2 Setup Requirements

1. **Windows permission:** Settings -> Privacy & security -> Microphone -> Enable for terminal app
2. **WSL packages:** `sudo apt install -y libasound2-plugins pulseaudio-utils`
3. **ALSA config** (`~/.asoundrc`):
   ```
   pcm.!default { type pulse fallback "sysdefault" }
   ctl.!default { type pulse fallback "sysdefault" }
   ```
4. **PulseAudio server:**
   ```bash
   export PULSE_SERVER=unix:/mnt/wslg/PulseServer
   ```
5. **Verify:** `pactl list sources short` should show `RDPSource`

### 7.3 sounddevice Compatibility

The `sounddevice` library (which whisper-key uses) relies on PortAudio. With the ALSA-to-PulseAudio shim configured, PortAudio can see the RDP audio devices and record from the microphone.

```bash
python3 -c "import sounddevice as sd; print(sd.query_devices())"
```

Should list at least one input device.

### 7.4 Latency

Audio passes through RDP bridging, adding some latency compared to native Windows. For speech-to-text this is acceptable since:
- Whisper processes full utterances, not real-time streaming
- The latency is in the low-tens-of-milliseconds range
- Recording start/stop timing is not latency-sensitive

### 7.5 Gotchas

- ALSA errors in console output are harmless but noisy; they come from missing native ALSA devices
- First-time microphone access may require enabling Windows privacy permission
- WSLg must be enabled (default on Windows 11 with WSL2)
- Older WSL2 versions without WSLg require manual PulseAudio setup over TCP

---

## 8. Clipboard in WSL

### 8.1 For the Wrapping Use Case (`wk claude`)

**No clipboard needed.** Transcribed text is written directly to the wrapped subprocess's stdin:

```python
proc = subprocess.Popen(['claude'], stdin=subprocess.PIPE, ...)
# After transcription:
proc.stdin.write(transcribed_text.encode())
proc.stdin.flush()
```

This is the cleanest approach and avoids all clipboard complexity.

### 8.2 For the Standalone Use Case (Paste to Active Window)

Multiple options exist, each with tradeoffs:

| Method | How | Limitations |
|--------|-----|-------------|
| **pyperclip + xclip** | WSLg provides X11, xclip works | Requires xclip installed; WSLg clipboard bridges to Windows |
| **pyperclip + wl-clipboard** | Wayland clipboard | Requires wl-clipboard installed |
| **clip.exe** | `echo text \| clip.exe` | ASCII only -- no Unicode support, no paste simulation |
| **PowerShell** | `powershell.exe -c "Set-Clipboard ..."` | Slow startup, but Unicode works |
| **Windows shim** | Extend the hotkey shim to also handle paste | Most reliable, but more complex shim |

**pyperclip in WSL2** has known issues:
- Issue #144: Crashes when `appendWindowsPath=false` in wsl.conf (can't find clip.exe)
- Issue #169: Intermittent failures
- Issue #244: Encoding issues with non-ASCII text

**Recommendation for standalone mode:** Extend the Windows-side shim to accept paste commands over the TCP connection. The shim calls `pyperclip.copy()` + `pyautogui.hotkey('ctrl', 'v')` on the Windows side where these operations work reliably.

### 8.3 Key Simulation for Paste

For the standalone use case, key simulation (Ctrl+V) must happen on the **Windows side** since the active window is a Windows application. The WSL app cannot simulate keypresses in Windows windows.

This means the Windows shim would need to handle two directions:
- **Windows -> WSL:** Hotkey press events
- **WSL -> Windows:** Paste commands (clipboard text + paste key simulation)

---

## 9. Architecture Diagram

```
┌─────────────────────────────────────────────────────────────┐
│ WINDOWS SIDE                                                │
│                                                             │
│  ┌──────────────────────────┐                               │
│  │  hotkey_shim.py          │                               │
│  │  (python.exe)            │                               │
│  │                          │                               │
│  │  RegisterHotKey(...)     │                               │
│  │  GetMessageA loop        │──── TCP 127.0.0.1:PORT ──┐   │
│  │  [Optional: paste cmds]  │                           │   │
│  └──────────────────────────┘                           │   │
│                                                         │   │
├─────────────────── WSL2 VM ─────────────────────────────┼───┤
│                                                         │   │
│  ┌──────────────────────────┐     ┌──────────────────┐  │   │
│  │  whisper-key (main app)  │     │ WslHotkeyBridge  │◄─┘   │
│  │                          │◄────│ (TCP server)     │      │
│  │  state_manager.py        │     └──────────────────┘      │
│  │  audio_recorder.py       │                               │
│  │  whisper_engine.py       │     ┌──────────────────┐      │
│  │  clipboard_manager.py    │     │ WSLg PulseAudio  │      │
│  │                          │◄────│ (mic via RDP)    │      │
│  └──────────────────────────┘     └──────────────────┘      │
│           │                                                  │
│           │ (wrapping mode: write to stdin)                  │
│           ▼                                                  │
│  ┌──────────────────────────┐                               │
│  │  claude (subprocess)     │                               │
│  │  stdin ◄── text          │                               │
│  └──────────────────────────┘                               │
│                                                              │
└──────────────────────────────────────────────────────────────┘

Communication flow:
  1. WSL app starts, opens TCP server on 127.0.0.1:0 (ephemeral port)
  2. WSL app spawns python.exe hotkey_shim.py <port> <config>
  3. Shim registers hotkeys, connects to TCP, sends {"status":"ready"}
  4. User presses hotkey → Windows posts WM_HOTKEY
  5. Shim sends {"hotkey":"hotkey_0"} over TCP
  6. WSL app receives event, triggers recording/transcription
  7. Transcription complete → write to subprocess stdin (wrapping mode)
                            → or send paste command to shim (standalone mode)
```

---

## 10. Gotchas and Limitations

### 10.1 Networking

- **NAT mode (default):** WSL listening port is auto-forwarded to Windows localhost. Windows shim connects to `127.0.0.1:<port>` and it reaches WSL. But a Windows server is NOT reachable from WSL via localhost in NAT mode -- must use host IP.
- **Mirrored mode:** Both directions work via localhost. Recommended if available (Windows 11 22H2+).
- **Sleep/resume:** TCP connections over localhost may break after Windows sleep. Need reconnection logic.
- **Port conflicts:** Use ephemeral port (bind to port 0) to avoid conflicts.

### 10.2 WSL Interop

- `python.exe` must be findable. If `appendWindowsPath=false` in `/etc/wsl.conf`, Windows executables won't be on PATH. Must use full path (`/mnt/c/.../python.exe`).
- The shim script must be on a path accessible from Windows. Storing on DrvFS (`/mnt/c/...`) is simplest.
- WSL interop can be disabled entirely in wsl.conf (`[interop] enabled=false`). Should detect this and fail gracefully.

### 10.3 Audio

- Microphone privacy permission must be enabled in Windows Settings for the WSL terminal app.
- ALSA error messages are noisy but harmless.
- WSLg must be present. Without WSLg (older WSL2 or Windows 10), manual PulseAudio-over-TCP setup is needed.
- Audio device enumeration can be slower than native.

### 10.4 Windows Python

- The shim runs on `python.exe` (Windows Python), not the WSL Python. These are different installations.
- The shim must use only stdlib modules. No `pip install` on the Windows side.
- If the user only has WSL Python and no Windows Python, the shim can't run. Must detect and report clearly.

### 10.5 Hotkey Registration

- `RegisterHotKey` is per-thread and requires a Win32 message loop. The shim's main thread must run the message loop.
- If another application already registered the same hotkey, `RegisterHotKey` fails. Must detect and report.
- `MOD_NOREPEAT` flag prevents repeated events from held keys.

### 10.6 Process Lifecycle

- If the WSL app crashes, the shim continues running as an orphaned Windows process. Need cleanup strategy (e.g., shim polls TCP connection health, exits on disconnect).
- If the shim crashes, the WSL app loses hotkey capability. Need detection and restart logic.

---

## 11. Prior Art and References

### Projects

- **npiperelay** ([jstarks/npiperelay](https://github.com/jstarks/npiperelay)) - Bridges Windows named pipes to WSL via stdin/stdout and socat. Shows the socat+relay pattern.
- **wslbridge** ([rprichard/wslbridge](https://github.com/rprichard/wslbridge)) - Bridge from Cygwin to WSL pty/pipe I/O. Demonstrates cross-environment process communication.
- **wsl2-ssh-bridge** ([KerickHowlett/wsl2-ssh-bridge](https://github.com/KerickHowlett/wsl2-ssh-bridge)) - SSH agent forwarding from Windows to WSL2. Shows the relay pattern.
- **1Password WSL integration** - Uses npiperelay+socat to bridge the 1Password SSH agent from Windows to WSL. Well-documented community pattern.

### Documentation

- [WSL Networking (Microsoft Learn)](https://learn.microsoft.com/en-us/windows/wsl/networking) - Official networking architecture
- [AF_UNIX WSL Interop (Microsoft Blog)](https://devblogs.microsoft.com/commandline/windowswsl-interop-with-af_unix/) - AF_UNIX sockets (WSL1 only)
- [AF_UNIX WSL2 issue #5961](https://github.com/microsoft/WSL/issues/5961) - Confirms AF_UNIX cross-platform is broken in WSL2
- [WSL Interop documentation](https://wsl.dev/technical-documentation/interop/) - How WSL runs Windows executables
- [Tim Golden: System-wide hotkeys](https://timgolden.me.uk/python/win32_how_do_i/catch_system_wide_hotkeys.html) - RegisterHotKey pattern
- [WSL2 Microphone Guide (Voice Mode)](https://voice-mode.readthedocs.io/en/stable/troubleshooting/wsl2-microphone-access/) - Audio setup in WSL2
- [WSLg PulseAudio (GitHub #9624)](https://github.com/microsoft/WSL/discussions/9624) - PyAudio in WSL2
- [Pyperclip WSL crash (Issue #144)](https://github.com/asweigart/pyperclip/issues/144) - Clipboard issues in WSL
- [Detect WSL from Python](https://www.scivision.dev/python-detect-wsl/) - WSL detection methods

### No Direct Prior Art Found

No existing project was found that specifically builds a "global hotkey bridge" from Windows to WSL. This is a novel pattern. The closest analogues are SSH agent forwarding bridges (npiperelay, socat patterns) and the wsl-terminal hotkey binding (which launches a terminal, not a hotkey bridge).

---

## 12. Recommended Implementation Plan

### Phase 1: Proof of Concept (Wrapping Mode Only)

1. Create `src/whisper_key/platform/wsl/` directory mirroring the platform contract
2. Implement `detect_wsl()` in `platform/__init__.py`
3. Create the hotkey shim (`hotkey_shim.py`) -- single file, pure ctypes
4. Create `WslHotkeyBridge` class implementing the `hotkeys` platform module API (`register()`, `start()`, `stop()`)
5. Test with `wk claude` wrapping mode (no clipboard/paste needed)

### Phase 2: Audio Validation

6. Verify `sounddevice` microphone recording works in WSL2 with WSLg
7. Create setup guide for ALSA/PulseAudio config
8. Test full flow: hotkey -> record -> transcribe -> write to stdin

### Phase 3: Standalone Mode (Optional)

9. Extend shim to accept paste commands over TCP
10. Implement Windows-side clipboard + key simulation in the shim
11. Test with standalone mode (paste to active Windows application)

### Platform Module Mapping

```
platform/wsl/
├── __init__.py          # (empty or re-exports)
├── app.py               # Thread requirements (same as Linux/macOS)
├── hotkeys.py           # WslHotkeyBridge wrapping the TCP shim
├── icons.py             # Tray icons (Linux/WSLg or no-op)
├── instance_lock.py     # fcntl-based (same as macOS)
├── keyboard.py          # No-op for wrapping mode; shim-delegated for standalone
├── paths.py             # XDG paths (~/.config/whisperkey)
├── permissions.py       # Check WSLg, PulseAudio, python.exe availability
└── assets/
    └── hotkey_shim.py   # The Windows-side shim script
```
