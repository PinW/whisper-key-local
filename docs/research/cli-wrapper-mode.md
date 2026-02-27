# CLI Wrapper Mode Research

## Overview

Wrap CLI tools with `whisper-key <command>` to provide voice input directly to the wrapped process without keyboard simulation or clipboard operations.

```
whisper-key claude
whisper-key python
whisper-key ssh user@host
```

## Architecture

```
┌─────────────────────────────────────────────────────────────┐
│  whisper-key wrapper                                        │
│                                                             │
│  ┌──────────────┐     ┌──────────────┐     ┌─────────────┐ │
│  │ Audio Capture│────►│ Transcription│────►│ PTY Write   │ │
│  └──────────────┘     └──────────────┘     └──────┬──────┘ │
│                                                   │        │
│  ┌────────────────────────────────────────────────┼──────┐ │
│  │ PTY Master                                     │      │ │
│  │                                                ▼      │ │
│  │  write(transcribed_text) ─────────────────────►│      │ │
│  │                                                │      │ │
│  │  read() ◄────────────────────────────────────  │      │ │
│  └────────────────────────────────────────────────┼──────┘ │
│                                                   │        │
│  ┌────────────────────────────────────────────────┼──────┐ │
│  │ PTY Slave (child's stdin/stdout)               │      │ │
│  └────────────────────────────────────────────────┼──────┘ │
│                                                   │        │
│  ┌────────────────────────────────────────────────▼──────┐ │
│  │ Child Process (e.g., claude)                          │ │
│  └───────────────────────────────────────────────────────┘ │
└─────────────────────────────────────────────────────────────┘
```

## Why PTY Instead of Keyboard Simulation

| Approach | Pros | Cons |
|----------|------|------|
| Keyboard simulation | Works with any app | OS-dependent, timing issues, clipboard pollution |
| PTY direct write | Clean, fast, no OS involvement | Only works for wrapped processes |

For wrapper mode, PTY is clearly better - we control the process, so we can write directly to it.

## Visual Layout

Reserve bottom line for status, give child process the rest:

```
┌─────────────────────────────────────────┐
│ $ claude                                │
│                                         │
│ > What would you like to do?            │
│                                         │  ← Child sees (rows-1) rows
│ █                                       │
│                                         │
├─────────────────────────────────────────┤
│ 🎤 Recording... [2.3s]        whisper-key│  ← Status bar (row N)
└─────────────────────────────────────────┘
```

### Implementation

1. Query real terminal size: `rows, cols = os.get_terminal_size()`
2. Create PTY with size `(rows-1, cols)`
3. Child process thinks it has `rows-1` rows
4. Passthrough child output to real terminal (rows 1 to N-1)
5. Draw status bar on row N
6. Handle `SIGWINCH` → resize PTY, redraw status bar

## Libraries

### Unix (Linux/macOS)

**ptyprocess** - Recommended
```python
from ptyprocess import PtyProcessUnicode

proc = PtyProcessUnicode.spawn(
    ['claude'],
    dimensions=(rows-1, cols)
)

# Read child output
output = proc.read(1024)
print(output, end='')

# Write transcription to child
proc.write(transcribed_text)

# Resize on SIGWINCH
proc.setwinsize(new_rows-1, new_cols)
```

**pexpect** - Higher-level, pattern matching
```python
import pexpect
child = pexpect.spawn('claude', dimensions=(rows-1, cols))
child.interact()  # Full passthrough mode
```

### Windows

**pywinpty** - ConPTY wrapper
```python
from winpty import PtyProcess

proc = PtyProcess.spawn('claude.exe')
proc.write('hello\r\n')
output = proc.read()
```

Note: Windows ConPTY (Windows 10+) is the modern equivalent of Unix PTY.

## Key Challenges

### 1. Terminal Mode Handling

Child may switch between:
- **Cooked mode**: Line-buffered, echo on (normal typing)
- **Raw mode**: Character-by-character, no echo (passwords, editors)

For voice input, we probably want to inject text regardless of mode, but may need to handle differently.

### 2. SIGWINCH (Terminal Resize)

```python
import signal

def handle_resize(signum, frame):
    rows, cols = os.get_terminal_size()
    proc.setwinsize(rows-1, cols)
    redraw_status_bar()

signal.signal(signal.SIGWINCH, handle_resize)
```

### 3. Full-Screen Applications

Apps like vim, htop, or fzf use the entire terminal. Options:
- Let them overwrite status bar (acceptable)
- Use alternate screen buffer detection
- Document as limitation

For `claude` CLI specifically: mostly line-based, should work fine.

### 4. ANSI Escape Sequence Passthrough

Child output contains colors, cursor movement, etc. Must pass through unchanged:
```python
# Good: raw passthrough
sys.stdout.write(proc.read())
sys.stdout.flush()

# Bad: any processing that might corrupt escape sequences
print(proc.read())  # Adds newline
```

### 5. Input Handling

Need to handle both:
- Voice input → write to PTY
- Keyboard input → write to PTY (user can still type)

```python
import select
import sys

while proc.isalive():
    # Check for keyboard input and PTY output
    readable, _, _ = select.select([sys.stdin, proc.fd], [], [], 0.1)

    for fd in readable:
        if fd == sys.stdin:
            # Forward keyboard to child
            proc.write(sys.stdin.read(1))
        elif fd == proc.fd:
            # Forward child output to terminal
            sys.stdout.write(proc.read())
```

## Status Bar Design

Minimal, informative:

```
│ 🎤 Recording... [2.3s]        whisper-key│  Recording
│ ⏳ Transcribing...            whisper-key│  Processing
│ ✓ Ready                       whisper-key│  Idle
│ ✗ Error: No speech detected   whisper-key│  Error
```

Use ANSI escape codes:
```python
def draw_status(message):
    rows, cols = os.get_terminal_size()
    # Save cursor, move to last row, clear line, draw, restore cursor
    sys.stdout.write(f"\0337\033[{rows};1H\033[2K{message}\0338")
    sys.stdout.flush()
```

## Hotkey Considerations

Current whisper-key uses global hotkeys (F13, etc.). In wrapper mode:

**Option A: Same global hotkey**
- Works across windows
- Familiar to existing users

**Option B: Terminal-specific key**
- Could intercept specific key in PTY input
- e.g., Ctrl+R (if not used by child)
- Stays within terminal context

**Option C: Both**
- Global hotkey always works
- Optional terminal-specific binding

## Implementation Phases

### Phase 1: Basic Wrapper
- Spawn process in PTY
- Passthrough I/O
- No voice yet, just prove the wrapper works

### Phase 2: Status Bar
- Reserve bottom line
- Show whisper-key status
- Handle resize

### Phase 3: Voice Integration
- Existing audio capture
- Existing transcription
- New: write to PTY instead of clipboard

### Phase 4: Polish
- Error handling
- Clean shutdown
- Configuration options

## Platform Differences

| Feature | Unix | Windows |
|---------|------|---------|
| PTY library | ptyprocess | pywinpty |
| Resize signal | SIGWINCH | ConPTY resize API |
| Raw mode | termios | Console mode flags |
| Select on stdin | select.select() | Different approach needed |

May need platform abstraction similar to existing `platform/` module.

## References

- [ptyprocess docs](https://ptyprocess.readthedocs.io/)
- [pywinpty](https://github.com/andfoy/pywinpty)
- [Python pty module](https://docs.python.org/3/library/pty.html)
- [Windows ConPTY](https://learn.microsoft.com/en-us/windows/console/creating-a-pseudoconsole-session)
- [rlwrap source](https://github.com/hanslub42/rlwrap) - canonical CLI wrapper
- [pyte](https://github.com/selectel/pyte) - terminal emulator in Python (if needed)
