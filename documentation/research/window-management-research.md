# Windows Window Management & Recognition Research

**Goal:** Detect open windows, focused window, available fields, and insert text programmatically.

## Use Cases for Whisper-Key

1. **Smart text insertion** - Insert transcription into specific app/field
2. **Context-aware behavior** - Different actions based on active window
3. **Field detection** - Find text input fields to target
4. **Voice command routing** - Recognize active and open windows to target actions

---

## Part 1: Core Windows APIs

### Win32 API (pywin32) - Low-Level Window Management

Already using `pywin32` in project. Primary low-level access.

#### Key Functions

| Function | Purpose | Notes |
|----------|---------|-------|
| `GetForegroundWindow()` | Get focused window handle | Fast, reliable |
| `EnumWindows()` | List all top-level windows | Callback-based |
| `EnumChildWindows()` | List child controls | For finding Edit controls |
| `GetWindowText()` | Get window title | Can hang on unresponsive windows |
| `GetClassName()` | Get window class | "Edit", "Button", etc. |
| `FindWindow()` | Find by class/title | Exact match only, first match |
| `SetForegroundWindow()` | Change focus | **Restricted by Windows** |
| `GetWindowThreadProcessId()` | Get PID from window | Returns (thread_id, pid) |

#### Complete Window Manager Example

```python
import re
import win32gui
import win32con
import win32process
import win32api
import psutil

class WindowManager:
    def get_focused_window_info(self):
        hwnd = win32gui.GetForegroundWindow()
        title = win32gui.GetWindowText(hwnd)
        _, pid = win32process.GetWindowThreadProcessId(hwnd)

        try:
            process = psutil.Process(pid)
            exe_name = process.name()
        except:
            exe_name = "unknown"

        return {
            "hwnd": hwnd,
            "title": title,
            "pid": pid,
            "exe": exe_name,
            "class": win32gui.GetClassName(hwnd)
        }

    def list_visible_windows(self, with_title_only=True):
        results = []

        def callback(hwnd, _):
            if win32gui.IsWindowVisible(hwnd):
                title = win32gui.GetWindowText(hwnd)
                if not with_title_only or title:
                    results.append({
                        "hwnd": hwnd,
                        "title": title,
                        "class": win32gui.GetClassName(hwnd)
                    })
            return True

        win32gui.EnumWindows(callback, None)
        return results

    def find_by_title_regex(self, pattern):
        result = None

        def callback(hwnd, regex):
            nonlocal result
            if win32gui.IsWindowVisible(hwnd):
                title = win32gui.GetWindowText(hwnd)
                if re.search(regex, title):
                    result = hwnd
                    return False  # Stop enumeration
            return True

        win32gui.EnumWindows(callback, pattern)
        return result

    def get_edit_controls(self, parent_hwnd):
        controls = []

        def callback(hwnd, results):
            classname = win32gui.GetClassName(hwnd)
            if classname == "Edit":
                results.append({
                    "hwnd": hwnd,
                    "text": win32gui.GetWindowText(hwnd),
                    "class": classname
                })
            return True

        win32gui.EnumChildWindows(parent_hwnd, callback, controls)
        return controls
```

#### SetForegroundWindow - The Focus Problem

Windows intentionally restricts `SetForegroundWindow` to prevent focus stealing. Common workarounds:

**Workaround 1: Thread Input Attachment**
```python
import win32gui
import win32process
import win32con

def force_foreground(hwnd):
    if win32gui.IsIconic(hwnd):
        win32gui.ShowWindow(hwnd, win32con.SW_RESTORE)

    if win32gui.GetForegroundWindow() == hwnd:
        return True

    foreground_hwnd = win32gui.GetForegroundWindow()
    foreground_thread, _ = win32process.GetWindowThreadProcessId(foreground_hwnd)
    target_thread, _ = win32process.GetWindowThreadProcessId(hwnd)

    if foreground_thread != target_thread:
        win32process.AttachThreadInput(target_thread, foreground_thread, True)
        win32gui.BringWindowToTop(hwnd)
        win32gui.SetForegroundWindow(hwnd)
        win32process.AttachThreadInput(target_thread, foreground_thread, False)
    else:
        win32gui.BringWindowToTop(hwnd)
        win32gui.SetForegroundWindow(hwnd)

    return win32gui.GetForegroundWindow() == hwnd
```

**Workaround 2: WScript.Shell**
```python
import win32com.client
import win32gui

def focus_with_sendkeys(hwnd):
    shell = win32com.client.Dispatch("WScript.Shell")
    shell.SendKeys('')  # Wake up focus system
    win32gui.SetForegroundWindow(hwnd)
```

#### Safe Text Retrieval (Timeout)

`GetWindowText` can hang on unresponsive windows:

```python
import win32gui
import win32con

def safe_get_window_text(hwnd, timeout_ms=100):
    try:
        buf_size = 1024
        buffer = win32gui.PyMakeBuffer(buf_size)
        flags = win32con.SMTO_ABORTIFHUNG | win32con.SMTO_BLOCK
        _, result = win32gui.SendMessageTimeout(
            hwnd, win32con.WM_GETTEXT, buf_size, buffer, flags, timeout_ms
        )
        if result > 0:
            return buffer[:result]
    except Exception:
        pass
    return ""
```

---

## Part 1b: Active Window Recognition for Voice Commands

### Window Identity Signals

To route voice commands to the right target, capture multiple identifiers per window and keep them in a small cache.

| Signal | Purpose | Notes |
|--------|---------|-------|
| hwnd | Unique window handle | Changes per window instance |
| title | Human label for matching | Often includes document suffixes |
| class | Window class name | Useful for app type detection |
| pid + exe name | Stable app identity | Use for command routing |
| visibility + cloaked | Filter real windows | Skip background or hidden windows |
| z-order position | Pick topmost match | Use foreground or last focused |

### Visible Window Enumeration (Filtered)

```python
import ctypes
import psutil
import win32con
import win32gui
import win32process

DWMWA_CLOAKED = 14

def is_cloaked(hwnd):
    cloaked = ctypes.c_int(0)
    ctypes.windll.dwmapi.DwmGetWindowAttribute(
        hwnd,
        DWMWA_CLOAKED,
        ctypes.byref(cloaked),
        ctypes.sizeof(cloaked)
    )
    return cloaked.value != 0

def list_open_windows():
    windows = []

    def callback(hwnd, _):
        if not win32gui.IsWindowVisible(hwnd):
            return True
        if is_cloaked(hwnd):
            return True
        title = win32gui.GetWindowText(hwnd)
        if not title:
            return True
        exstyle = win32gui.GetWindowLong(hwnd, win32con.GWL_EXSTYLE)
        if exstyle & win32con.WS_EX_TOOLWINDOW:
            return True

        _, pid = win32process.GetWindowThreadProcessId(hwnd)
        exe_name = psutil.Process(pid).name()
        windows.append({
            "hwnd": hwnd,
            "title": title,
            "class": win32gui.GetClassName(hwnd),
            "pid": pid,
            "exe": exe_name
        })
        return True

    win32gui.EnumWindows(callback, None)
    return windows
```

### Active Window Snapshot

```python
import win32gui
import win32process
import psutil

def get_active_window():
    hwnd = win32gui.GetForegroundWindow()
    title = win32gui.GetWindowText(hwnd)
    _, pid = win32process.GetWindowThreadProcessId(hwnd)
    exe_name = psutil.Process(pid).name()
    return {
        "hwnd": hwnd,
        "title": title,
        "pid": pid,
        "exe": exe_name,
        "class": win32gui.GetClassName(hwnd)
    }
```

### Command Routing Heuristics

1. Prefer exe name match for stable routing ("slack.exe", "chrome.exe").
2. Fall back to class name for app families ("Chrome_WidgetWin_1", "Notepad").
3. Use title regex for per-document commands (".* - Notepad").
4. If multiple matches, choose the most recent foreground match or highest z-order.
5. Keep a last-focused cache per app for quick routing to "last Slack window".

### Edge Cases

- UWP apps often show as `ApplicationFrameWindow`, with the real child window inside.
- Minimized windows still enumerate as visible; check `IsIconic` if needed.
- Some background windows report empty titles; keep a short allowlist if they matter.

---

## Part 2: UI Automation (UIA) - Field Detection

### MSAA vs UIA Comparison

| Aspect | MSAA (Legacy) | UI Automation (Modern) |
|--------|---------------|------------------------|
| Interface | `IAccessible` (fixed) | `IUIAutomationElement` (extensible) |
| Properties | Small fixed set | Rich set + control patterns |
| Extensibility | Cannot extend | Custom properties/patterns |
| Performance | Slow cross-process | Better cross-process |
| Text Support | Limited | Full TextPattern support |
| **Recommendation** | Legacy only | **Use for new development** |

### Python Libraries for UIA

| Library | Install | Best For | Notes |
|---------|---------|----------|-------|
| `uiautomation` | `pip install uiautomation` | Direct UIA access | Lightweight, fast |
| `pywinauto` | `pip install pywinauto` | Full automation | Two backends (win32/uia) |
| `comtypes` | `pip install comtypes` | Raw COM access | Very verbose |

### uiautomation Library

```python
import uiautomation as auto

# Get focused control
focused = auto.GetFocusedControl()
print(f"Type: {focused.ControlTypeName}")
print(f"Name: {focused.Name}")
print(f"Class: {focused.ClassName}")

# Check if it's an editable field
def is_editable_field(control):
    editable_types = ['EditControl', 'DocumentControl', 'ComboBoxControl']
    if control.ControlTypeName not in editable_types:
        return False

    if not control.IsEnabled or not control.IsKeyboardFocusable:
        return False

    value_pattern = control.GetValuePattern()
    if value_pattern:
        try:
            return not value_pattern.IsReadOnly
        except:
            pass

    return True

# Find window and edit control (with depth limits for speed)
notepad = auto.WindowControl(searchDepth=1, ClassName='Notepad')
edit = notepad.EditControl(searchDepth=1)

# Set text via ValuePattern
pattern = edit.GetValuePattern()
if pattern:
    pattern.SetValue('Hello World')
```

### pywinauto Library

```python
from pywinauto import Application, Desktop

# UIA backend (for modern apps: WPF, UWP, Electron)
app = Application(backend='uia').connect(path='notepad.exe')
dlg = app.window(title_re='.*Notepad.*')

# Check if editable (UIA backend only)
edit = dlg.child_window(control_type='Edit')
if edit.is_editable():
    edit.set_edit_text('Hello World')

# Win32 backend (for legacy apps, faster)
app = Application(backend='win32').connect(path='notepad.exe')
```

### Backend Selection Guide

| Application Type | Recommended Backend |
|------------------|---------------------|
| MFC, VB6, VCL, legacy | Win32 (faster) |
| WinForms | Either (Win32 faster) |
| WPF, UWP | UIA |
| Qt5 | UIA |
| Electron, Chrome | UIA (with accessibility flag) |
| Store apps | UIA |

### Control Patterns

| Pattern | Purpose | Use Case |
|---------|---------|----------|
| **ValuePattern** | Get/set single-line text | Edit boxes, combos |
| **TextPattern** | Read-only rich text | Documents (read-only!) |
| **TextEditPattern** | Text editing with caret | Modern editors |
| **SelectionPattern** | Selection management | List boxes |

**Important:** `ValuePattern.SetValue()` replaces entire text, doesn't insert at cursor.

### Performance Optimization

UIA can be **1000x slower** than Win32. Critical optimizations:

1. **Limit search depth**
   ```python
   # BAD: Deep search from root
   edit = auto.EditControl()

   # GOOD: Hierarchical with depth limits
   window = auto.WindowControl(searchDepth=1, ClassName='Notepad')
   edit = window.EditControl(searchDepth=1)
   ```

2. **Use specific search criteria**
   ```python
   # SLOW
   app.child_window(title='OK')

   # FASTER
   app.child_window(class_name='Button', auto_id='OKButton', control_type='Button')
   ```

3. **Cache wrappers**
   ```python
   wrapper = dlg.child_window(title='Edit').wrapper_object()
   wrapper.set_edit_text('text1')  # Reuse, don't re-query
   wrapper.set_edit_text('text2')
   ```

4. **Connect by path, not title**
   ```python
   # SLOWER
   app.connect(title='Calculator')

   # FASTER
   app.connect(path='calculator.exe')
   ```

### Enabling Accessibility for Electron/Chrome

Many Electron apps and Chrome don't expose UIA by default:

```bash
# Chrome
chrome.exe --force-renderer-accessibility

# Or per-page: chrome://accessibility/
```

```javascript
// Electron main process
app.setAccessibilitySupportEnabled(true);
```

---

## Part 3: Text Insertion Methods

### Comparison Table

| Method | Unicode | Speed | Focus Required | Best For |
|--------|---------|-------|----------------|----------|
| Clipboard + Ctrl+V | Full | Fast | Yes | **Universal fallback** |
| WM_SETTEXT | Full | Fastest | No | Win32 Edit controls |
| UI Automation ValuePattern | Full | Medium | No | Modern apps (WPF/UWP) |
| SendKeys/PyAutoGUI | Limited | Slow | Yes | Simple automation |
| SendInput | Full | Medium | Yes | Low-level control |

### Recommended: Clipboard Paste (Current Approach)

```python
import pyperclip
import pyautogui
import time

def insert_via_clipboard(text, preserve_clipboard=True):
    if preserve_clipboard:
        original = pyperclip.paste()

    pyperclip.copy(text)
    time.sleep(0.05)  # Allow clipboard to sync
    pyautogui.hotkey('ctrl', 'v')

    if preserve_clipboard:
        time.sleep(0.05)
        pyperclip.copy(original)
```

**Pros:**
- Works with virtually all applications
- Full Unicode support
- Fast (entire text at once)

**Cons:**
- Requires focus
- Overwrites clipboard (mitigated with preserve)
- Some paste-restricted fields block it

### WM_SETTEXT (Fastest for Win32)

```python
import win32gui
import win32con

def set_edit_text(edit_hwnd, text):
    win32gui.SendMessage(edit_hwnd, win32con.WM_SETTEXT, 0, text)

# Insert at cursor position (not replace all)
def insert_at_cursor(edit_hwnd, text):
    win32gui.SendMessage(edit_hwnd, win32con.EM_REPLACESEL, True, text)
```

**Works on:** Notepad, simple Win32 Edit controls
**Doesn't work on:** WPF, browsers, Electron, Word/Excel

### UI Automation ValuePattern

```python
import uiautomation as auto

focused = auto.GetFocusedControl()
pattern = focused.GetValuePattern()
if pattern and not pattern.IsReadOnly:
    pattern.SetValue('new text')  # Replaces all text
```

**Note:** Cannot insert at cursor - replaces entire value.

### SendInput with Unicode (VK_PACKET)

For paste-restricted fields as fallback:

```python
import ctypes
from ctypes import wintypes

user32 = ctypes.windll.user32

INPUT_KEYBOARD = 1
KEYEVENTF_UNICODE = 0x0004
KEYEVENTF_KEYUP = 0x0002

class KEYBDINPUT(ctypes.Structure):
    _fields_ = [
        ("wVk", wintypes.WORD),
        ("wScan", wintypes.WORD),
        ("dwFlags", wintypes.DWORD),
        ("time", wintypes.DWORD),
        ("dwExtraInfo", ctypes.POINTER(ctypes.c_ulong))
    ]

class INPUT(ctypes.Structure):
    _fields_ = [("type", wintypes.DWORD), ("ki", KEYBDINPUT)]

def send_unicode_char(char):
    inputs = (INPUT * 2)()

    # Key down
    inputs[0].type = INPUT_KEYBOARD
    inputs[0].ki.wScan = ord(char)
    inputs[0].ki.dwFlags = KEYEVENTF_UNICODE

    # Key up
    inputs[1].type = INPUT_KEYBOARD
    inputs[1].ki.wScan = ord(char)
    inputs[1].ki.dwFlags = KEYEVENTF_UNICODE | KEYEVENTF_KEYUP

    user32.SendInput(2, ctypes.byref(inputs), ctypes.sizeof(INPUT))

def type_unicode_string(text):
    for char in text:
        send_unicode_char(char)
```

---

## Part 4: Screen Reader Techniques

### How NVDA/JAWS Detect Focus

1. **UI Automation**: `GetFocusedElement()` + focus change events
2. **IAccessible2**: For Chrome/Firefox web content
3. **Virtual Buffer**: Pre-traversed DOM for web pages

### Focus Detection Code

```python
import uiautomation as auto

class FocusMonitor:
    def __init__(self):
        self.last_control_id = None

    def poll_focused(self, callback, interval=0.1):
        import time
        while True:
            try:
                current = auto.GetFocusedControl()
                current_id = (current.ControlTypeName, current.Name, current.ClassName)

                if current_id != self.last_control_id:
                    callback(current)
                    self.last_control_id = current_id
            except Exception:
                pass

            time.sleep(interval)

    def on_focus_change(self, control):
        if control.ControlTypeName in ['EditControl', 'DocumentControl']:
            print(f"Editable field focused: {control.Name}")
```

### Identifying Text Input Fields

```python
import uiautomation as auto

def get_focused_field_info():
    ctrl = auto.GetFocusedControl()

    info = {
        "type": ctrl.ControlTypeName,
        "name": ctrl.Name,
        "class": ctrl.ClassName,
        "is_text_field": False,
        "is_editable": False,
        "is_password": False
    }

    # Check if text field type
    text_types = ['EditControl', 'DocumentControl', 'ComboBoxControl']
    if ctrl.ControlTypeName in text_types:
        info["is_text_field"] = True

        # Check editability
        if ctrl.IsEnabled and ctrl.IsKeyboardFocusable:
            value_pattern = ctrl.GetValuePattern()
            if value_pattern:
                try:
                    info["is_editable"] = not value_pattern.IsReadOnly
                except:
                    info["is_editable"] = True

    return info
```

---

## Part 5: Tools for Development

### Inspect.exe (Windows SDK)

Best tool for exploring UIA tree structure.

**Location:** `C:\Program Files (x86)\Windows Kits\10\bin\<version>\x64\Inspect.exe`

**Key shortcuts:**
- `Ctrl+Shift+F4` - Focus element under cursor
- `Ctrl+Shift+F6` - Parent element
- `Ctrl+Shift+F7` - First child

### Accessibility Insights for Windows

Modern Microsoft tool, more user-friendly than Inspect.exe.
Download: https://accessibilityinsights.io/

### Spy++ (Visual Studio)

For Win32 window/message inspection. Limited UIA support.

---

## Part 6: Application Compatibility Matrix

| Application | Window Detection | Field Detection | Text Insertion |
|-------------|-----------------|-----------------|----------------|
| Notepad | Win32 | Win32 Edit | WM_SETTEXT |
| VS Code | Win32 | UIA (needs flag) | Clipboard |
| Chrome | Win32 | UIA (needs flag) | Clipboard |
| Firefox | Win32 | UIA | Clipboard |
| Word/Excel | Win32 | COM Automation | COM or Clipboard |
| WPF apps | Win32 | UIA | ValuePattern |
| UWP apps | UIA | UIA | ValuePattern |
| Electron | Win32 | UIA (needs flag) | Clipboard |
| Qt5 | Win32 | UIA (partial) | Clipboard |
| Terminal | Win32 | Limited | SendInput |

---

## Open Questions

- [ ] Event-driven focus monitoring vs polling - performance comparison?
- [ ] Can we detect password fields reliably across all apps?
- [ ] How to handle apps that block paste?
- [ ] Multi-monitor focus edge cases?
- [ ] Threading model for UIA in background monitoring?

---

## Next Research Areas

1. **Event-driven UIA** - Focus change events via COM
2. **Browser-specific** - Chrome DevTools Protocol, Firefox Marionette
3. **Specific app APIs** - VS Code extension API, Office COM
4. **Performance profiling** - Real measurements of different approaches

---

*Last Updated: 2026-01-28 | Research Round: 1*

---

## Round 1 Summary

**Key findings:**
- **Win32 + UIA hybrid** is optimal: Win32 for window detection (fast), UIA for field detection (rich)
- **SetForegroundWindow** is restricted by Windows; use thread attachment workaround
- **UIA is 1000x slower** than Win32 - must limit search depth and cache wrappers
- **Clipboard paste** is best universal text insertion method; preserve original clipboard
- **Electron/Chrome** need `--force-renderer-accessibility` flag for UIA access
- **ValuePattern.SetValue()** replaces all text, cannot insert at cursor
- **uiautomation** library preferred over pywinauto for lightweight focus monitoring

**Recommended approach for Whisper-Key:**
1. Detect focused window: `win32gui.GetForegroundWindow()` + psutil for exe name
2. Detect if text field: `uiautomation.GetFocusedControl()` → check ControlTypeName
3. Insert text: Clipboard paste with preservation (current approach is good)

---

## Round 2 Notes: UIA Quick Test

**Apps tested:** Windows Terminal, Cursor (Electron)

**Findings:**
- Windows Terminal exposed focused `TextControl` with class `TermControl`, but no editable controls were discoverable.
- Cursor exposed only the top-level `RootWebArea` `DocumentControl` and no editable controls; terminal surface was not exposed.
- UIA visibility for Electron apps still appears limited without accessibility flags, and even with UIA visibility, editability is not guaranteed.

**Conclusion:** Field focusing via UIA is not reliable enough for this project right now; continue using window focus + clipboard paste.
