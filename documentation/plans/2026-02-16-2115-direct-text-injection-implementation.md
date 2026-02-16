# Direct Text Injection

As a *user* I want **direct text injection** so transcriptions reliably reach the target app without clipboard race conditions

Design: @../design/auto-paste-reliability.md

## Background

Auto-paste currently writes text to the clipboard, simulates Ctrl+V, then restores the clipboard. The target app reads the clipboard asynchronously — if the restore happens before the read, the app gets empty text. Windows provides no API to detect clipboard reads, so any clipboard-based approach is inherently timing-dependent.

Direct text injection uses `SendInput` with `KEYEVENTF_UNICODE` to type text directly into the active window. The clipboard is never involved, eliminating both the restore race and clipboard lock contention.

## Current Architecture

```
clipboard_manager.py  →  platform/windows/keyboard.py (pyautogui wrapper)
                      →  pyperclip (clipboard read/write)

Delivery flow:
  pyperclip.copy(text) → pyautogui.hotkey('ctrl','v') → pyperclip.copy(original)
```

## Target Architecture

```
clipboard_manager.py  →  platform/windows/keyboard.py (native ctypes SendInput)
                      →  pyperclip (only when delivery_method="paste")

Delivery flow (type):
  keyboard.type_text(text)

Delivery flow (paste):
  pyperclip.copy(text) → keyboard.send_hotkey('ctrl','v') → delayed restore
```

## Implementation Plan

1. Native Windows key simulation
- [ ] Rewrite `platform/windows/keyboard.py` using ctypes `SendInput`
- [ ] Implement virtual key code mapping (modifiers, enter, tab, function keys)
- [ ] Implement `send_key(key)` — single keystroke via virtual key code
- [ ] Implement `send_hotkey(*keys)` — modifier combo via virtual key codes
- [ ] Implement `type_text(text)` — bulk Unicode injection via `KEYEVENTF_UNICODE`
- [ ] Handle `\n` as `VK_RETURN`, `\t` as `VK_TAB`
- [ ] Handle surrogate pairs for characters above U+FFFF (emoji)
- [ ] Own delay via explicit `time.sleep()` in `set_delay()`
- [ ] **Test:** verify `send_key('enter')` works
- [ ] **Test:** verify `send_hotkey('ctrl', 'v')` works (for paste mode)
- [ ] **Test:** verify `type_text()` delivers text to Notepad, Claude Code, browser

2. macOS keyboard stub
- [ ] Add `type_text(text)` to `platform/macos/keyboard.py`
- [ ] Implement as clipboard + Cmd+V (same as current paste, most reliable on macOS)
- [ ] No-op for now — macOS doesn't use pyautogui, no regression

3. Update clipboard_manager.py
- [ ] Accept `delivery_method` config ("type" or "paste")
- [ ] When `delivery_method="type"`: call `keyboard.type_text(text)` — no clipboard, no restore
- [ ] When `delivery_method="paste"`: current clipboard flow with `clipboard_restore_delay`
- [ ] Auto-enter (`send_enter_key`) unchanged — already uses `send_key('enter')`
- [ ] Update `_print_status()` to show delivery method

4. Config
- [ ] Add `delivery_method: type` to clipboard section in `config.defaults.yaml`
- [ ] Add `clipboard_restore_delay: 0.5` for paste mode
- [ ] Wire up new settings in `config_manager.py` and `main.py`

5. Remove pyautogui
- [ ] Remove `pyautogui` from `pyproject.toml` dependencies
- [ ] Update `README.md` dependencies list
- [ ] Update `documentation/project-index.md` (clipboard_manager technologies)

6. Test
- [ ] **Test:** type mode delivers text to Claude Code terminal
- [ ] **Test:** type mode delivers text to browser text field
- [ ] **Test:** type mode handles multi-line transcriptions
- [ ] **Test:** paste mode still works as before
- [ ] **Test:** auto-enter works in both modes
- [ ] **Test:** app starts and runs with pyautogui fully removed

## Implementation Details

### platform/windows/keyboard.py — type_text()

Batch all characters into a single `SendInput` call for atomic delivery:

```python
import ctypes
from ctypes import wintypes

user32 = ctypes.windll.user32

def type_text(text):
    inputs = []
    for char in text:
        if char == '\n':
            inputs.extend(_vk_pair(VK_RETURN))
        elif char == '\t':
            inputs.extend(_vk_pair(VK_TAB))
        else:
            code = ord(char)
            if code > 0xFFFF:
                high, low = _surrogate_pair(code)
                inputs.extend(_unicode_pair(high))
                inputs.extend(_unicode_pair(low))
            else:
                inputs.extend(_unicode_pair(code))

    array = (INPUT * len(inputs))(*inputs)
    user32.SendInput(len(inputs), array, ctypes.sizeof(INPUT))
```

### clipboard_manager.py — deliver_transcription routing

```python
# Before (always clipboard)
def execute_auto_paste(self, text, preserve_clipboard):
    original = pyperclip.paste()
    pyperclip.copy(text)
    keyboard.send_hotkey(*self.paste_keys)
    pyperclip.copy(original)

# After (configurable)
def execute_delivery(self, text):
    if self.delivery_method == "type":
        keyboard.type_text(text)
    else:
        self._clipboard_paste(text)
```

### config.defaults.yaml

```yaml
clipboard:
  auto_paste: true
  delivery_method: type    # "type" = direct injection, "paste" = clipboard + Ctrl+V
  paste_hotkey: "ctrl+v | macos: cmd+v"
  preserve_clipboard: true
  clipboard_restore_delay: 0.5  # seconds, only applies to paste mode
  key_simulation_delay: 0.05
```

## Scope

| File | Change |
|------|--------|
| `platform/windows/keyboard.py` | Full rewrite: ctypes SendInput replacing pyautogui |
| `platform/macos/keyboard.py` | Add `type_text()` stub |
| `clipboard_manager.py` | Route delivery by config, add paste-mode delay |
| `config.defaults.yaml` | Add `delivery_method`, `clipboard_restore_delay` |
| `config_manager.py` | Wire new settings |
| `main.py` | Pass `delivery_method` to ClipboardManager |
| `pyproject.toml` | Remove pyautogui dependency |
| `README.md` | Update dependencies |
| `documentation/project-index.md` | Update technologies |

## Success Criteria

- [ ] Default mode (type): transcription appears in target app without touching clipboard
- [ ] Paste mode: transcription delivered via clipboard with configurable restore delay
- [ ] Auto-enter works correctly in both modes
- [ ] pyautogui fully removed from project
- [ ] No regression on macOS (clipboard + Cmd+V continues to work)
