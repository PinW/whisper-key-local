# Win32 Multi-Monitor API Research

## 1. Multi-Monitor APIs (Win32 via ctypes)

### 1.1 EnumDisplayMonitors — Alle Monitore auflisten

Enumeriert alle Display-Monitore und ruft einen Callback pro Monitor auf.

```python
import ctypes
import ctypes.wintypes as wintypes

MonitorEnumProc = ctypes.WINFUNCTYPE(
    wintypes.BOOL, wintypes.HMONITOR, wintypes.HDC,
    ctypes.POINTER(wintypes.RECT), wintypes.LPARAM
)

def get_all_monitors():
    monitors = []

    def callback(hmonitor, hdc, rect, data):
        r = rect.contents
        monitors.append({
            'hmonitor': hmonitor,
            'left': r.left, 'top': r.top,
            'right': r.right, 'bottom': r.bottom,
        })
        return True  # True = weiter enumerieren

    proc = MonitorEnumProc(callback)
    ctypes.windll.user32.EnumDisplayMonitors(None, None, proc, 0)
    return monitors
```

**Wichtig:** Der `proc`-Callback muss als Variable gehalten werden (nicht inline), sonst wird das ctypes-Trampoline garbage-collected und crasht.

### 1.2 GetMonitorInfoW — Position/Groesse eines Monitors

Liefert `rcMonitor` (volle Flaeche) und `rcWork` (ohne Taskbar) sowie `dwFlags` (MONITORINFOF_PRIMARY = 1).

```python
class MONITORINFO(ctypes.Structure):
    _fields_ = [
        ("cbSize", wintypes.DWORD),
        ("rcMonitor", wintypes.RECT),
        ("rcWork", wintypes.RECT),
        ("dwFlags", wintypes.DWORD),
    ]

def get_monitor_info(hmonitor):
    info = MONITORINFO()
    info.cbSize = ctypes.sizeof(MONITORINFO)
    ctypes.windll.user32.GetMonitorInfoW(hmonitor, ctypes.byref(info))
    return info
```

Fuer den Device-Namen braucht man `MONITORINFOEXW`:

```python
class MONITORINFOEXW(ctypes.Structure):
    _fields_ = [
        ("cbSize", wintypes.DWORD),
        ("rcMonitor", wintypes.RECT),
        ("rcWork", wintypes.RECT),
        ("dwFlags", wintypes.DWORD),
        ("szDevice", wintypes.WCHAR * 32),
    ]

def get_monitor_info_ex(hmonitor):
    info = MONITORINFOEXW()
    info.cbSize = ctypes.sizeof(MONITORINFOEXW)
    ctypes.windll.user32.GetMonitorInfoW(hmonitor, ctypes.byref(info))
    return info  # info.szDevice = z.B. "\\\\.\\DISPLAY1"
```

### 1.3 MonitorFromPoint — Monitor unter einem Punkt

```python
MONITOR_DEFAULTTONEAREST = 2

point = wintypes.POINT(x, y)
hmonitor = ctypes.windll.user32.MonitorFromPoint(point, MONITOR_DEFAULTTONEAREST)
```

Flags:
- `MONITOR_DEFAULTTONULL` (0) — gibt NULL wenn kein Monitor
- `MONITOR_DEFAULTTOPRIMARY` (1) — Fallback auf Primaermonitor
- `MONITOR_DEFAULTTONEAREST` (2) — naechster Monitor (empfohlen)

### 1.4 MonitorFromWindow — Monitor eines Fensters

```python
MONITOR_DEFAULTTONEAREST = 2

hwnd = ctypes.windll.user32.GetForegroundWindow()
hmonitor = ctypes.windll.user32.MonitorFromWindow(hwnd, MONITOR_DEFAULTTONEAREST)
```

Gibt den Monitor zurueck, der die groesste Ueberschneidung mit dem Fenster-Rect hat.

### 1.5 GetForegroundWindow — Aktives Fenster

```python
hwnd = ctypes.windll.user32.GetForegroundWindow()
```

Gibt HWND des Fensters zurueck, das aktuell den Eingabefokus hat.

### 1.6 GetWindowRect — Position eines Fensters

```python
rect = wintypes.RECT()
ctypes.windll.user32.GetWindowRect(hwnd, ctypes.byref(rect))
# rect.left, rect.top, rect.right, rect.bottom
```

### 1.7 Kombination: Monitor des aktuell fokussierten Fensters

```python
def get_focused_window_monitor():
    hwnd = ctypes.windll.user32.GetForegroundWindow()
    if not hwnd:
        # Kein fokussiertes Fenster -> Fallback auf Cursor-Position
        point = wintypes.POINT()
        ctypes.windll.user32.GetCursorPos(ctypes.byref(point))
        hmonitor = ctypes.windll.user32.MonitorFromPoint(
            point, MONITOR_DEFAULTTONEAREST
        )
    else:
        hmonitor = ctypes.windll.user32.MonitorFromWindow(
            hwnd, MONITOR_DEFAULTTONEAREST
        )
    info = MONITORINFO()
    info.cbSize = ctypes.sizeof(MONITORINFO)
    ctypes.windll.user32.GetMonitorInfoW(hmonitor, ctypes.byref(info))
    r = info.rcWork  # Arbeitsbereich (ohne Taskbar)
    return r.left, r.top, r.right - r.left, r.bottom - r.top
```

---

## 2. tkinter Multi-Monitor

### 2.1 Grundproblem

- `winfo_screenwidth()` / `winfo_screenheight()` geben NUR den Primaermonitor zurueck
- tkinter hat KEINE eingebaute Multi-Monitor-Erkennung
- Man MUSS externe APIs (ctypes oder `screeninfo`) nutzen

### 2.2 Positionierung auf bestimmtem Monitor

tkinter nutzt den **Virtual Screen** Koordinatenraum. Fenster werden ueber `geometry()` positioniert:

```python
# Fenster auf Monitor 2 (rechts vom Primaermonitor) positionieren
# Wenn Monitor 1 = 1920x1080 bei (0,0), Monitor 2 bei (1920,0):
root.geometry(f"+{1920 + 100}+{100}")  # x=2020, y=100 -> auf Monitor 2

# Negative Koordinaten fuer Monitor links vom Primaermonitor:
root.geometry(f"+{-1920 + 100}+{100}")  # Monitor links
```

### 2.3 Korrekte Positionierung mit Monitor-Info

```python
def position_on_monitor(window, mon_x, mon_y, mon_w, mon_h):
    window.update_idletasks()
    win_w = window.winfo_reqwidth()
    win_h = window.winfo_reqheight()
    # Zentriert unten auf dem Monitor
    x = mon_x + (mon_w - win_w) // 2
    y = mon_y + mon_h - win_h - 80  # 80px Abstand vom unteren Rand
    window.geometry(f"+{x}+{y}")
```

### 2.4 Toplevel fuer mehrere Fenster

```python
# Ein Tk() pro Applikation, weitere Fenster als Toplevel
root = tk.Tk()
root.withdraw()  # Hauptfenster verstecken

# Overlay-Fenster als Toplevel
overlay = tk.Toplevel(root)
overlay.overrideredirect(True)
overlay.attributes("-topmost", True)
overlay.attributes("-alpha", 0.85)
overlay.geometry(f"+{mon2_x}+{mon2_y}")
```

---

## 3. Focus-Follow (Fokuswechsel erkennen)

### 3.1 Polling-Ansatz (einfach)

```python
import threading

def poll_focus(callback, interval=0.3):
    last_hwnd = None
    while True:
        hwnd = ctypes.windll.user32.GetForegroundWindow()
        if hwnd != last_hwnd:
            last_hwnd = hwnd
            hmonitor = ctypes.windll.user32.MonitorFromWindow(
                hwnd, MONITOR_DEFAULTTONEAREST
            )
            callback(hmonitor)
        threading.Event().wait(interval)
```

**Vorteile:** Einfach, keine Abhaengigkeiten, kein Message-Loop noetig.
**Nachteile:** Leichte Verzoegerung (interval), minimaler CPU-Verbrauch.

### 3.2 Event-basiert: SetWinEventHook (optimal)

```python
import ctypes
import ctypes.wintypes as wintypes

EVENT_SYSTEM_FOREGROUND = 0x0003
EVENT_SYSTEM_MINIMIZEEND = 0x0017
WINEVENT_OUTOFCONTEXT = 0x0000
WINEVENT_SKIPOWNPROCESS = 0x0002

WinEventProcType = ctypes.WINFUNCTYPE(
    None,                    # return: void
    wintypes.HANDLE,         # hWinEventHook
    wintypes.DWORD,          # event
    wintypes.HWND,           # hwnd
    wintypes.LONG,           # idObject
    wintypes.LONG,           # idChild
    wintypes.DWORD,          # idEventThread
    wintypes.DWORD,          # dwmsEventTime
)

def start_focus_listener(on_focus_change):
    """
    on_focus_change(hwnd) wird aufgerufen wenn ein neues Fenster den Fokus bekommt.
    MUSS in eigenem Thread laufen (braucht eigenen Message-Loop).
    """
    def callback(hWinEventHook, event, hwnd, idObject, idChild,
                 dwEventThread, dwmsEventTime):
        if hwnd:
            on_focus_change(hwnd)

    # WICHTIG: Referenz halten damit der GC den Callback nicht loescht!
    win_event_proc = WinEventProcType(callback)

    # Hook fuer Fokuswechsel
    ctypes.windll.user32.SetWinEventHook(
        EVENT_SYSTEM_FOREGROUND,   # eventMin
        EVENT_SYSTEM_FOREGROUND,   # eventMax
        0,                         # hmodWinEventProc (0 = out-of-context)
        win_event_proc,            # pfnWinEventProc
        0,                         # idProcess (0 = alle)
        0,                         # idThread (0 = alle)
        WINEVENT_OUTOFCONTEXT | WINEVENT_SKIPOWNPROCESS,
    )

    # Auch MINIMIZEEND hooken (Foreground-Event wird beim Restore
    # eines minimierten Fensters NICHT gesendet!)
    ctypes.windll.user32.SetWinEventHook(
        EVENT_SYSTEM_MINIMIZEEND,
        EVENT_SYSTEM_MINIMIZEEND,
        0,
        win_event_proc,
        0, 0,
        WINEVENT_OUTOFCONTEXT | WINEVENT_SKIPOWNPROCESS,
    )

    # Windows Message-Loop (blockiert)
    msg = wintypes.MSG()
    while ctypes.windll.user32.GetMessageW(ctypes.byref(msg), 0, 0, 0) != 0:
        ctypes.windll.user32.TranslateMessage(ctypes.byref(msg))
        ctypes.windll.user32.DispatchMessageW(ctypes.byref(msg))
```

**Vorteile:** Sofortige Reaktion, kein Polling, kein CPU-Verbrauch im Leerlauf.
**Nachteile:** Braucht eigenen Thread mit Message-Loop. Callback-Referenz muss gehalten werden.

### 3.3 Empfehlung

- **Polling** reicht fuer unseren Use-Case (Overlay repositionieren) voellig aus
- **SetWinEventHook** ist eleganter, braucht aber einen dedizierten Thread mit Message-Loop
- Fuer ein Overlay das sowieso regelmaessig updated: Polling mit 200-300ms Interval ist optimal

### 3.4 win32-window-monitor Library

```python
# pip install win32-window-monitor
from win32_window_monitor import HookEvent, start_event_hook

def on_event(hook_handle, event_id, hwnd, id_object, id_child,
             event_thread_id, event_time_ms):
    if event_id == HookEvent.SYSTEM_FOREGROUND:
        # Neues Fenster hat Fokus
        pass

start_event_hook(on_event)  # Blockiert (eigener Message-Loop)
```

---

## 4. Overlay auf ALLEN Monitoren

### 4.1 Virtual Screen Koordinaten

```python
SM_XVIRTUALSCREEN = 76   # X-Koordinate des Virtual Screen
SM_YVIRTUALSCREEN = 77   # Y-Koordinate
SM_CXVIRTUALSCREEN = 78  # Breite
SM_CYVIRTUALSCREEN = 79  # Hoehe
SM_CMONITORS = 80        # Anzahl Monitore

vx = ctypes.windll.user32.GetSystemMetrics(SM_XVIRTUALSCREEN)
vy = ctypes.windll.user32.GetSystemMetrics(SM_YVIRTUALSCREEN)
vw = ctypes.windll.user32.GetSystemMetrics(SM_CXVIRTUALSCREEN)
vh = ctypes.windll.user32.GetSystemMetrics(SM_CYVIRTUALSCREEN)
# vx kann negativ sein wenn ein Monitor links vom Primaermonitor steht
```

**Achtung:** `GetSystemMetrics` ist NICHT DPI-aware. Fuer korrekte Werte bei verschiedenen DPI-Skalierungen `GetSystemMetricsForDpi()` verwenden oder vorher `SetProcessDpiAwareness(2)` aufrufen.

### 4.2 Ein tkinter-Fenster ueber alle Monitore

```python
# Gesamten Virtual Screen abdecken
root.geometry(f"{vw}x{vh}+{vx}+{vy}")
```

**Problem:** Ein riesiges transparentes Fenster ueber alle Monitore ist Ressourcen-intensiv und kann Input auf allen Monitoren blockieren (auch mit `-alpha`). Nicht empfohlen fuer ein kleines Overlay.

### 4.3 Separates Toplevel pro Monitor (empfohlen)

```python
def create_overlay_per_monitor(root):
    overlays = {}
    monitors = get_all_monitors_with_info()

    for i, mon in enumerate(monitors):
        overlay = tk.Toplevel(root)
        overlay.overrideredirect(True)
        overlay.attributes("-topmost", True)
        overlay.attributes("-alpha", 0.85)
        overlay.withdraw()  # Erstmal versteckt

        label = tk.Label(overlay, text="", font=..., fg="#fff", bg="#1e1e1e")
        label.pack()
        overlays[i] = (overlay, label, mon)

    return overlays
```

**Vorteile:**
- Jedes Overlay ist nur so gross wie noetig
- Kann gezielt ein-/ausgeblendet werden
- Kein Input-Blocking auf anderen Monitoren
- Weniger Ressourcen

**Nachteile:**
- Mehr Code zum Verwalten
- Muss bei Monitor-Konfigurationsaenderungen neu erstellt werden

### 4.4 Empfehlung fuer unser Overlay

**Ein einziges Fenster, repositioniert je nach Modus:**
- "Follow Cursor" -> MonitorFromPoint(GetCursorPos)
- "Follow Focus" -> MonitorFromWindow(GetForegroundWindow)
- "Fixed Monitor" -> Fester Monitor aus Config
- "All Monitors" -> Nicht empfohlen, oder: ein Toplevel pro Monitor

---

## 5. DPI-Awareness

### 5.1 SetProcessDpiAwareness

MUSS frueh aufgerufen werden, BEVOR tkinter oder andere UI-APIs initialisiert werden:

```python
import ctypes

PROCESS_DPI_UNAWARE = 0
PROCESS_SYSTEM_DPI_AWARE = 1
PROCESS_PER_MONITOR_DPI_AWARE = 2

try:
    ctypes.windll.shcore.SetProcessDpiAwareness(PROCESS_PER_MONITOR_DPI_AWARE)
except Exception:
    # Windows 8.0 oder aelter - Fallback
    try:
        ctypes.windll.user32.SetProcessDPIAware()
    except Exception:
        pass
```

**Wichtig:**
- Nur ein einziger Aufruf moeglich (danach E_ACCESSDENIED)
- Wert 2 (PER_MONITOR) noetig damit EnumDisplayMonitors/GetMonitorInfo korrekte Werte bei unterschiedlichen DPI-Skalierungen liefern
- MUSS vor `tk.Tk()` aufgerufen werden
- tkinter selbst ruft ggf. `SetProcessDPIAware()` auf (Wert 1) — daher so frueh wie moeglich aufrufen

### 5.2 Auswirkung auf tkinter

Wenn `SetProcessDpiAwareness(2)` gesetzt ist:
- `winfo_screenwidth/height` gibt physische Pixel zurueck (korrekt)
- `geometry()` Koordinaten sind in physischen Pixeln
- Font-Groessen muessen ggf. skaliert werden

Wenn NICHT gesetzt:
- Windows skaliert das Fenster (kann unscharf sein)
- `GetMonitorInfo` liefert skalierte (falsche) Werte
- Overlay kann am falschen Ort landen bei verschiedenen DPI pro Monitor

---

## 6. Python-Libraries (Alternativen zu reinem ctypes)

### 6.1 screeninfo

```
pip install screeninfo
```

```python
from screeninfo import get_monitors

for m in get_monitors():
    print(f"{m.name}: {m.width}x{m.height} at ({m.x},{m.y}) primary={m.is_primary}")
```

**Monitor-Attribute:** `x`, `y`, `width`, `height`, `width_mm`, `height_mm`, `name`, `is_primary`

**Vorteile:**
- Plattformuebergreifend (Windows, macOS, Linux)
- Einfache API
- Nutzt intern EnumDisplayMonitors + GetMonitorInfo
- Setzt `SetProcessDpiAwareness(2)` automatisch

**Nachteile:**
- Externe Abhaengigkeit
- Kennt nur statische Monitor-Info (kein Fokus-Tracking)
- Keine rcWork (Arbeitsbereich ohne Taskbar)

### 6.2 PyGetWindow / PyWinCtl

```
pip install pygetwindow   # nur Windows
pip install pywinctl       # plattformuebergreifend
```

```python
import pygetwindow as gw
win = gw.getActiveWindow()
print(win.title, win.left, win.top, win.width, win.height)
```

**Kann:** Aktives Fenster finden, Position/Groesse lesen.
**Kann nicht:** Monitor-Info, Focus-Events.

### 6.3 win32-window-monitor

```
pip install win32-window-monitor
```

Wrapper um `SetWinEventHook`. Trackt Fokus-Wechsel mit Callback.
Siehe Abschnitt 3.4.

### 6.4 pywin32 (win32api)

```
pip install pywin32
```

```python
import win32api
monitors = win32api.EnumDisplayMonitors()
for hmon, hdcmon, rect in monitors:
    info = win32api.GetMonitorInfo(hmon)
    print(info)
    # {'Monitor': (0, 0, 1920, 1080), 'Work': (0, 0, 1920, 1040),
    #  'Flags': 1, 'Device': '\\\\.\\DISPLAY1'}
```

**Vorteile:** Komfortabler als ctypes, gibt Dicts zurueck.
**Nachteile:** Grosse Abhaengigkeit (pywin32), nicht plattformuebergreifend.

### 6.5 Empfehlung

**Fuer unser Projekt: Reines ctypes verwenden.**
- Keine zusaetzliche Abhaengigkeit
- Wir brauchen nur wenige Funktionen
- Die aktuelle preview_overlay.py nutzt bereits ctypes
- Volle Kontrolle ueber DPI-Awareness
- Alle benoetigten Funktionen in <30 Zeilen implementierbar

---

## 7. Komplettes Referenz-Beispiel: Monitor-Utility

```python
import ctypes
import ctypes.wintypes as wintypes

MONITOR_DEFAULTTONEAREST = 2
SM_CMONITORS = 80

class MONITORINFO(ctypes.Structure):
    _fields_ = [
        ("cbSize", wintypes.DWORD),
        ("rcMonitor", wintypes.RECT),
        ("rcWork", wintypes.RECT),
        ("dwFlags", wintypes.DWORD),
    ]

MonitorEnumProc = ctypes.WINFUNCTYPE(
    wintypes.BOOL, wintypes.HMONITOR, wintypes.HDC,
    ctypes.POINTER(wintypes.RECT), wintypes.LPARAM,
)

user32 = ctypes.windll.user32


def set_dpi_aware():
    try:
        ctypes.windll.shcore.SetProcessDpiAwareness(2)
    except Exception:
        try:
            user32.SetProcessDPIAware()
        except Exception:
            pass


def enumerate_monitors():
    """Alle Monitore mit Work-Area (ohne Taskbar) zurueckgeben."""
    results = []

    def callback(hmonitor, hdc, rect, data):
        info = MONITORINFO()
        info.cbSize = ctypes.sizeof(MONITORINFO)
        user32.GetMonitorInfoW(hmonitor, ctypes.byref(info))
        r = info.rcWork
        results.append({
            'hmonitor': hmonitor,
            'x': r.left,
            'y': r.top,
            'w': r.right - r.left,
            'h': r.bottom - r.top,
            'is_primary': bool(info.dwFlags & 1),
        })
        return True

    proc = MonitorEnumProc(callback)
    user32.EnumDisplayMonitors(None, None, proc, 0)
    return results


def get_monitor_count():
    return user32.GetSystemMetrics(SM_CMONITORS)


def get_cursor_monitor():
    """Monitor unter der aktuellen Mausposition."""
    point = wintypes.POINT()
    user32.GetCursorPos(ctypes.byref(point))
    hmon = user32.MonitorFromPoint(point, MONITOR_DEFAULTTONEAREST)
    info = MONITORINFO()
    info.cbSize = ctypes.sizeof(MONITORINFO)
    user32.GetMonitorInfoW(hmon, ctypes.byref(info))
    r = info.rcWork
    return r.left, r.top, r.right - r.left, r.bottom - r.top


def get_focused_window_monitor():
    """Monitor des aktuell fokussierten Fensters."""
    hwnd = user32.GetForegroundWindow()
    if not hwnd:
        return get_cursor_monitor()
    hmon = user32.MonitorFromWindow(hwnd, MONITOR_DEFAULTTONEAREST)
    info = MONITORINFO()
    info.cbSize = ctypes.sizeof(MONITORINFO)
    user32.GetMonitorInfoW(hmon, ctypes.byref(info))
    r = info.rcWork
    return r.left, r.top, r.right - r.left, r.bottom - r.top


def get_monitor_by_index(index):
    """Monitor nach Index (0-basiert, sortiert links->rechts)."""
    monitors = enumerate_monitors()
    monitors.sort(key=lambda m: (m['x'], m['y']))
    if 0 <= index < len(monitors):
        m = monitors[index]
        return m['x'], m['y'], m['w'], m['h']
    return get_cursor_monitor()  # Fallback
```

---

## 8. Zusammenfassung fuer die Implementierung

| Feature | API | Aufwand |
|---------|-----|---------|
| Alle Monitore auflisten | `EnumDisplayMonitors` + `GetMonitorInfoW` | Klein |
| Monitor unter Cursor | `GetCursorPos` + `MonitorFromPoint` | Bereits implementiert |
| Monitor des aktiven Fensters | `GetForegroundWindow` + `MonitorFromWindow` | Klein |
| Fester Monitor (Config) | `EnumDisplayMonitors` + Index | Klein |
| Fokus-Follow (Event) | `SetWinEventHook` + Message-Loop | Mittel |
| Fokus-Follow (Polling) | `GetForegroundWindow` in Timer | Klein |
| DPI-Awareness | `SetProcessDpiAwareness(2)` | Einzeiler, aber frueh |
| Overlay repositionieren | `tkinter.geometry("+x+y")` | Bereits implementiert |

### Empfohlene Konfigurationsoptionen

```yaml
overlay:
  monitor: "cursor"         # "cursor" | "focus" | 0 | 1 | 2 ...
  position: "bottom_center" # "bottom_center" | "top_center" | "center"
  offset_y: -80             # Pixel-Offset vom berechneten Punkt
```

### Prioritaet

1. `SetProcessDpiAwareness(2)` einbauen (frueh in main.py)
2. `get_focused_window_monitor()` als Alternative zu `get_cursor_monitor()`
3. `enumerate_monitors()` + Index fuer feste Monitor-Zuweisung
4. Config-Option `overlay.monitor` mit den drei Modi
5. Optional: Polling-Timer der bei Fokuswechsel das Overlay repositioniert
