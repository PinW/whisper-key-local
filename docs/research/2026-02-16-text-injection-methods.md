# Text Injection Methods: Windows & macOS

Research into typing text into the active window WITHOUT using the clipboard.

## Current Whisper-Key Approach

`clipboard_manager.py` uses: `pyperclip.copy(text)` then `keyboard.send_hotkey('ctrl', 'v')` (simulated Ctrl+V). This works universally but clobbers the clipboard (optionally preserved via save/restore).

---

## Method 1: SendInput with KEYEVENTF_UNICODE (Windows)

### How It Works

- Call `SendInput()` with `INPUT_KEYBOARD` structs
- Set `dwFlags = KEYEVENTF_UNICODE (0x0004)`, `wVk = 0`, `wScan = <unicode codepoint>`
- Windows translates this to `WM_KEYDOWN` with `wParam = VK_PACKET`, then `TranslateMessage` posts `WM_CHAR` with the Unicode character
- For each character: one keydown event + one keyup event = 2 INPUT structs per character
- Characters outside the BMP (emoji, etc.) require **surrogate pairs**: split into 2 UTF-16 code units, send each separately (4 INPUT structs per emoji)

### Implementation (Python ctypes or pynput)

**pynput** uses this method. Its `keyboard.Controller().type("text")` calls `SendInput` with `KEYBDINPUT.UNICODE` flag. It handles surrogate pairs by encoding to UTF-16-LE and sending each 16-bit unit separately.

**pyautogui does NOT use this method.** `pyautogui.write()` uses `keybd_event()` with virtual key codes -- it can only type characters that have a VK mapping (ASCII printable chars). It cannot type Unicode beyond what's on the keyboard layout.

### Reliability Across Apps

| App Type | Works? | Notes |
|----------|--------|-------|
| Notepad, native Win32 edit controls | Yes | Fully reliable |
| Web browsers (Chrome, Edge, Firefox) | Yes | Works in text fields, `contenteditable`, etc. |
| Electron apps (Discord, Slack, VS Code) | Yes | These are Chromium-based, same as browsers |
| Windows Terminal (v1.16+) | Yes | Was broken for high codepoints (>U+7FFF), **fixed in v1.16** via PR #13667 |
| Windows Terminal (pre-1.16) | Partial | Characters with codepoints >32767 were clamped/garbled |
| Legacy cmd.exe / conhost | Partial | ANSI auto-conversion may corrupt non-ANSI characters |
| Games / DirectInput apps | No | These often read scancodes or raw input, ignore VK_PACKET |

### Properties

| Property | Value |
|----------|-------|
| Touches clipboard? | **No** |
| Synchronous? | Effectively yes -- `SendInput` injects into the input queue atomically |
| Speed (short text) | Near-instant, no per-character delay needed |
| Speed (long text) | OS may limit to ~5000 events per `SendInput` call (AutoHotkey docs). For 2500 chars that's fine. Longer text: batch into multiple calls |
| Unicode support | Full BMP + supplementary planes via surrogate pairs |
| Newlines (\n) | **Not supported** -- `\n` cannot be typed as a keystroke. Must send `VK_RETURN` separately |
| Tab (\t) | Must send `VK_TAB` separately |
| Known gotchas | Events are flagged `LLMHF_INJECTED` -- some anti-cheat/security software blocks them. UIPI blocks injection into higher-integrity processes (e.g., admin windows from non-admin app). Keyboard layout can interfere if app does its own translation |

---

## Method 2: WM_PASTE / WM_SETTEXT Messages (Windows)

### WM_PASTE

- Sends `WM_PASTE` message to a specific window handle via `SendMessage()`
- **Still uses the clipboard** -- it tells the control to paste from clipboard in CF_TEXT format
- Only works on Win32 Edit controls and ComboBox controls
- Synchronous within `SendMessage`

### WM_SETTEXT

- Sends `WM_SETTEXT` to set the entire text of a control
- **Does not use clipboard**
- **Replaces all text** in the control (not insert-at-cursor)
- Only works on Win32 controls (Edit, Button, Static, ComboBox)
- Does NOT work on: web browsers, Electron apps, modern XAML/WinUI controls, any non-Win32 text field
- Effectively useless for "type into any active window"

### Properties

| Property | WM_PASTE | WM_SETTEXT |
|----------|----------|------------|
| Touches clipboard? | **Yes** | No |
| Synchronous? | Yes | Yes |
| Works on any window? | No (edit controls only) | No (edit controls only) |
| Insert at cursor? | Yes | No (replaces all) |
| Verdict | **Not useful** -- still uses clipboard | **Not useful** -- replaces all text, only Win32 controls |

---

## Method 3: UI Automation API (Windows)

### How It Works

- Get the focused element via `IUIAutomation::GetFocusedElement()`
- Query for `ValuePattern` and call `SetValue("text")`
- Alternative: query for `TextPattern` (multiline controls)
- Python libraries: `uiautomation`, `pywinauto`

### Reliability

| App Type | Works? | Notes |
|----------|--------|-------|
| Win32 Edit controls | Yes | ValuePattern supported |
| WPF/WinForms | Yes | Good UIA support |
| Multiline edit controls | No (for ValuePattern) | Must use TextPattern instead |
| Web browsers | Unreliable | UIA support varies, contenteditable is poorly exposed |
| Electron apps | Unreliable | Limited automation patterns |
| Terminal emulators | No | No ValuePattern exposed |

### Properties

| Property | Value |
|----------|-------|
| Touches clipboard? | **No** |
| Synchronous? | Yes |
| Speed | Slow -- COM overhead, element lookup |
| Insert at cursor? | **No** -- `SetValue()` replaces the entire control value |
| Unicode support | Yes |
| Requires admin? | Often yes on Win7+, usually not on Win10/11 |
| Verdict | **Not suitable** for generic "type into any window" -- replaces entire value, unreliable across app types |

---

## Method 4: pyautogui.write() vs pyautogui.hotkey('ctrl','v')

### pyautogui.write()

- Uses `keybd_event()` with **virtual key codes** (NOT `KEYEVENTF_UNICODE`)
- Can only type characters that exist in the keyboard mapping dict (printable ASCII)
- Cannot type: Unicode, accented characters, CJK, emoji
- Has a built-in `interval` delay between characters (default: ~0.1s per char)
- Slow for long text

### pyautogui.hotkey('ctrl','v')

- Simulates Ctrl+V key combination via `keybd_event()`
- Requires text to already be on the clipboard
- Fast for any text length
- Universal across all apps

### Comparison

| Property | pyautogui.write() | pyautogui.hotkey('ctrl','v') |
|----------|-------------------|------------------------------|
| Touches clipboard? | No | **Yes** (relies on it) |
| Unicode support | **ASCII only** | Full (clipboard handles it) |
| Speed | ~10 chars/sec default | Instant |
| Reliability | Only ASCII chars | Universal |
| Verdict | **Unusable** for speech-to-text (no Unicode) | Current method, works well |

---

## Method 5: macOS Approaches

### CGEventKeyboardSetUnicodeString (via PyObjC)

- Create `CGEvent` keyboard event, call `CGEventKeyboardSetUnicodeString(event, length, string)` to set the Unicode payload, then `CGEventPost()` to inject it
- Can set multiple characters per event (up to ~20 reported by some)
- Must handle surrogate pairs for emoji (encode to UTF-16-LE, send each pair)
- **Gotcha**: some apps ignore the Unicode string and do their own key-to-char translation based on the virtual keycode. This is documented as always being a possibility, and reportedly got worse in macOS 12+
- Requires Accessibility permissions

### AppleScript "keystroke"

- `tell application "System Events" to keystroke "text"`
- Simple but requires delays between characters for reliability
- Unicode support depends on the target app
- Requires Accessibility permissions
- Slower than CGEventPost

### macOS Clipboard Approach (current)

- `NSPasteboard` to set clipboard, then simulate Cmd+V
- Most reliable approach on macOS
- Same tradeoff: clobbers clipboard

### macOS Summary

| Method | Clipboard? | Reliability | Speed | Unicode |
|--------|-----------|-------------|-------|---------|
| CGEventKeyboardSetUnicodeString | No | Medium -- some apps ignore Unicode string | Fast | Full (with surrogate handling) |
| AppleScript keystroke | No | Medium -- needs delays | Slow | Partial |
| Clipboard + Cmd+V | **Yes** | **Highest** | Fast | Full |

---

## Comparison Summary for Speech-to-Text Use Case

| Method | Clipboard? | Universal? | Unicode? | Speed | Best For |
|--------|-----------|------------|----------|-------|----------|
| **Clipboard + Ctrl/Cmd+V** | Yes | Highest | Full | Instant | **Current best approach** |
| **SendInput KEYEVENTF_UNICODE** | No | High | Full (with surrogate pairs) | Near-instant | **Best non-clipboard option on Windows** |
| pynput Controller.type() | No | High | Full | Near-instant | Same as above (uses SendInput internally) |
| pyautogui.write() | No | Low | ASCII only | Slow | Not viable |
| WM_SETTEXT | No | Very Low | Yes | Fast | Win32 controls only |
| WM_PASTE | Yes | Low | Yes | Fast | Win32 controls only |
| UI Automation SetValue | No | Low | Yes | Slow | Specific automation scenarios |
| CGEvent Unicode (macOS) | No | Medium | Full | Fast | macOS when clipboard-free needed |

---

## Recommendation for Whisper-Key

### Hybrid Approach: SendInput Unicode as Primary, Clipboard as Fallback

**For Windows**, `SendInput` with `KEYEVENTF_UNICODE` (via pynput or direct ctypes) is the best non-clipboard option:
- Works in browsers, Electron apps (Discord/Slack), Notepad, most modern apps
- Handles full Unicode including emoji via surrogate pairs
- Near-instant, no artificial delays needed
- Does NOT clobber the user's clipboard

**Limitations to handle:**
- Newlines: send `VK_RETURN` as a separate virtual key event
- Tabs: send `VK_TAB` as a separate virtual key event
- Very long text (>2500 chars): may need batching
- UIPI: cannot inject into admin/elevated windows from non-admin process
- Legacy terminals (pre-1.16 Windows Terminal): may garble high codepoints

**Fallback**: keep clipboard + Ctrl+V as a user-configurable fallback for edge cases or as the default if reliability is paramount.

**For macOS**, clipboard + Cmd+V remains the most reliable approach. `CGEventKeyboardSetUnicodeString` is a viable alternative but has known unreliability in some apps (especially post-macOS 12).

### Implementation Sketch (Windows, using ctypes directly)

```python
import ctypes
from ctypes import wintypes

KEYEVENTF_UNICODE = 0x0004
KEYEVENTF_KEYUP = 0x0002
INPUT_KEYBOARD = 1
VK_RETURN = 0x0D

class KEYBDINPUT(ctypes.Structure):
    _fields_ = [
        ("wVk", wintypes.WORD),
        ("wScan", wintypes.WORD),
        ("dwFlags", wintypes.DWORD),
        ("time", wintypes.DWORD),
        ("dwExtraInfo", ctypes.POINTER(ctypes.c_ulong)),
    ]

class INPUT(ctypes.Structure):
    class _INPUT(ctypes.Union):
        _fields_ = [("ki", KEYBDINPUT)]
    _fields_ = [("type", wintypes.DWORD), ("_input", _INPUT)]

def type_unicode_char(char):
    code_units = char.encode('utf-16-le')
    inputs = []
    for i in range(0, len(code_units), 2):
        code = code_units[i] | (code_units[i + 1] << 8)
        # key down
        inp_down = INPUT(type=INPUT_KEYBOARD)
        inp_down._input.ki = KEYBDINPUT(wVk=0, wScan=code, dwFlags=KEYEVENTF_UNICODE)
        # key up
        inp_up = INPUT(type=INPUT_KEYBOARD)
        inp_up._input.ki = KEYBDINPUT(wVk=0, wScan=code, dwFlags=KEYEVENTF_UNICODE | KEYEVENTF_KEYUP)
        inputs.extend([inp_down, inp_up])

    arr = (INPUT * len(inputs))(*inputs)
    ctypes.windll.user32.SendInput(len(inputs), arr, ctypes.sizeof(INPUT))

def type_text(text):
    for char in text:
        if char == '\n':
            # send VK_RETURN instead
            send_vk(VK_RETURN)
        else:
            type_unicode_char(char)
```

Or simpler: use **pynput** which already handles all of this:

```python
from pynput.keyboard import Controller
keyboard = Controller()
keyboard.type("Hello world! 你好 🎉")
```

---

## Sources

- [SendInput function - Microsoft Learn](https://learn.microsoft.com/en-us/windows/win32/api/winuser/nf-winuser-sendinput)
- [KEYBDINPUT structure - Microsoft Learn](https://learn.microsoft.com/en-us/windows/win32/api/winuser/ns-winuser-keybdinput)
- [Windows Terminal Unicode bug #12977](https://github.com/microsoft/terminal/issues/12977)
- [WM_PASTE message - Microsoft Learn](https://learn.microsoft.com/en-us/windows/win32/dataxchg/wm-paste)
- [Edit Control Text Operations - Microsoft Learn](https://learn.microsoft.com/en-us/windows/win32/controls/edit-controls-text-operations)
- [pynput keyboard _win32.py source](https://github.com/moses-palmer/pynput/blob/master/lib/pynput/keyboard/_win32.py)
- [pyautogui _pyautogui_win.py source](https://github.com/asweigart/pyautogui/blob/master/pyautogui/_pyautogui_win.py)
- [KeyWin - fast SendInput wrapper](https://github.com/winstxnhdw/KeyWin)
- [AutoHotkey Send documentation](https://www.autohotkey.com/docs/v1/lib/Send.htm)
- [Using SendInput for Unicode characters](https://batchloaf.wordpress.com/2014/10/02/using-sendinput-to-type-unicode-characters/)
- [Python-UIAutomation-for-Windows](https://github.com/yinkaisheng/Python-UIAutomation-for-Windows)
- [ValuePattern.SetValue - Microsoft Learn](https://learn.microsoft.com/en-us/dotnet/api/system.windows.automation.valuepattern.setvalue)
- [CGEventKeyboardSetUnicodeString - Apple Developer](https://developer.apple.com/documentation/coregraphics/cgevent/1456028-keyboardsetunicodestring)
- [CGEventPost emoji issues - Apple Developer Forums](https://developer.apple.com/forums/thread/706245)
- [pyobjc CGEvent Unicode issue - Bitbucket](https://bitbucket.org/ronaldoussoren/pyobjc/issues/162/quartz-cgeventkeyboardsetunicodestring-no)
- [Paste as keystrokes macOS gist](https://gist.github.com/sscotth/310db98e7c4ec74e21819806dc527e97)
