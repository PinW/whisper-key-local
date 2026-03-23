# Code-Analyse: Overlay, System Tray & Monitor-Handling

## 1. IST-Zustand

### 1.1 Preview Overlay (`preview_overlay.py`, 115 Zeilen)

**Architektur:**
- Eigener tkinter-Thread (daemon), gestartet im `__init__`
- `threading.Event` (`_ready`) synchronisiert Initialisierung (max 5s timeout)
- Ein einziges `tk.Tk()` Fenster, kein zweites Toplevel
- Fenster ist `overrideredirect(True)` + `topmost` + alpha 0.85

**Thread-Safety-Pattern:**
- Alle UI-Mutationen laufen ueber `self._root.after(0, callback)` — das ist korrekt, weil `after()` in die tkinter-Mainloop einreiht
- Aeussere Methoden (`update_text`, `show`, `hide`) sind threadsafe aufrufbar

**Positionierung (`_position_bottom_center`):**
- Ruft `_get_active_monitor()` auf — ermittelt den Monitor unter dem **Mauszeiger**
- Positioniert das Fenster horizontal zentriert, 80px ueber dem unteren Rand der Work Area (`rcWork`)
- Wird bei jedem `update_text()` Aufruf neu berechnet — d.h. der Monitor wird bei jedem Text-Update bestimmt

**Monitor-Erkennung (`_get_active_monitor`):**
- Win32 API direkt via ctypes:
  1. `GetCursorPos()` — aktuelle Mausposition
  2. `MonitorFromPoint(point, 2)` — Monitor der den Punkt enthaelt (Flag 2 = MONITOR_DEFAULTTONEAREST)
  3. `GetMonitorInfoW()` — Work Area Bounds (rcWork, exkl. Taskbar)
- Fallback bei Exception: primaerer Monitor via `winfo_screenwidth()/winfo_screenheight()`
- **Kein Caching** — wird bei jedem Text-Update neu abgefragt
- **Nur Windows** — kein macOS-Pfad (ctypes.windll ist Windows-only)

**Lifecycle:**
- Erstellt in `main.py` Zeile 330, nur wenn `listening.preview_show_overlay == True`
- Zugewiesen an `state_manager.preview_overlay`
- Kein expliziter `destroy()`/Cleanup — Thread ist daemon, stirbt mit Prozess

### 1.2 System Tray (`system_tray.py`, 423 Zeilen)

**Architektur:**
- pystray-basiert, laeuft via `icon.run_detached()` (eigener Thread)
- Haelt Referenzen auf `state_manager`, `config_manager`, `model_registry`
- Menu wird bei jedem State-Update komplett neu erzeugt (`_create_menu()`)

**Menu-Struktur (aktuell):**
```
Open log file...
Open model cache...
---
Open config folder...
Open settings file...
Open commands file...        (nur wenn voice_commands.enabled)
---
Audio Host >                 (Submenu, Radiobuttons)
Audio Source >               (Submenu, Radiobuttons)
---
Auto-paste                   (Radio)
Copy to clipboard            (Radio)
---
Model: {current} >           (Submenu, Radiobuttons pro Gruppe mit Separatoren)
---
Listening Mode >             (Submenu: Hotkey/Continuous/Wake Word als Radio)
Preview                      (Checkbox)
---
Exit
```

**Pattern fuer Radiobutton-Gruppen (Beispiel: Listening Mode):**
```python
# 1. Aktuellen Wert lesen
current_listening_mode = mode_info["mode"]

# 2. Closure-Factories fuer checked/action
def make_mode_selector(mode):
    return lambda icon, item: self._select_listening_mode(mode)

def make_is_mode(mode_value):
    return lambda item: current_listening_mode == mode_value

# 3. MenuItem mit radio=True, checked=closure
pystray.MenuItem("Hotkey", make_mode_selector(ListeningMode.HOTKEY),
                 radio=True, checked=make_is_mode("hotkey"))

# 4. Handler ruft state_manager + rebuild menu
def _select_listening_mode(self, mode):
    self.state_manager.set_listening_mode(mode)
    self.icon.menu = self._create_menu()
```

**Config-Aenderung zur Laufzeit:**
- Tray-Handler ruft `state_manager.xyz()` — der ruft `config_manager.update_user_setting(section, key, value)`
- `update_user_setting` aendert `self.config` in-memory + schreibt `_save_user_overrides()` (nur Diffs zum Default)
- Danach `self.icon.menu = self._create_menu()` — Menu wird komplett neu aufgebaut

**Submenu-Pattern:**
```python
pystray.MenuItem("Label", pystray.Menu(*sub_items))
```
pystray unterstuetzt beliebige Tiefe, aber tiefe Verschachtelung ist UX-maessig problematisch.

### 1.3 Config (`config.defaults.yaml` + `config_manager.py`)

**Relevante bestehende Keys:**
```yaml
listening:
  mode: hotkey
  preview_enabled: false
  preview_show_tooltip: true
  preview_show_overlay: false    # <-- Overlay an/aus
  preview_interval_sec: 1.5
  preview_max_audio_seconds: 30.0
  pre_buffer_duration_sec: 0.3
  post_speech_silence_ms: 800
  max_speech_duration_sec: 60.0
  min_speech_duration_sec: 0.5
```

**Es gibt KEINE Config-Keys fuer:**
- Monitor-Auswahl (fester Monitor, Focus-Follow, alle Monitore)
- Overlay-Position (immer bottom-center)
- Overlay-Aussehen (Farbe, Groesse, Transparenz)

### 1.4 State Manager (`state_manager.py`)

**Overlay-Interaktion:**
- `preview_overlay` ist ein optionales Attribut (None oder PreviewOverlay-Instanz)
- Wird in `handle_streaming_result()` angesprochen:
  - Bei nicht-finalem Text: `preview_overlay.update_text(text)` — zeigt laufende Vorschau
  - Bei finalem Text: `preview_overlay.update_text(text)` + `Timer(2.0, hide)` — 2s Timeout dann verstecken
- `preview_show_overlay` boolean entscheidet ob Overlay-Methoden aufgerufen werden

---

## 2. Gaps fuer neue Features

### 2.1 "Fester Monitor" Konfiguration

**Was fehlt:**
- Config-Key: `listening.overlay_monitor` (z.B. `"auto"`, `1`, `2`, `3`, ...)
- Methode zum Enumerieren aller Monitore mit Name/Index (`EnumDisplayMonitors` auf Windows)
- `_get_active_monitor()` muss den konfigurierten Monitor zurueckgeben statt immer Cursor-Position
- Tray-Submenu: "Overlay Monitor > Auto (Maus) / Monitor 1 / Monitor 2 / ..."
- Handler: `_select_overlay_monitor(monitor_id)` analog zu `_select_audio_device`

**Implementierungshinweise:**
- Monitor-Enumeration via `EnumDisplayMonitors` + `GetMonitorInfoW` (ctypes, analog zum bestehenden Code)
- Monitor-IDs koennen sich aendern (wie Audio-Devices) — Monitor-Name als Identifier robuster als Index
- Braucht plattform-abstrahierten Monitor-Enumeration-Layer (macOS: NSScreen)

### 2.2 "Focus-Follow" (Overlay folgt Fokusfenster)

**Was fehlt:**
- Config-Key: z.B. `listening.overlay_monitor: "focus"` als Modus
- Ermittlung des Fokus-Fensters: `GetForegroundWindow()` + `MonitorFromWindow()` (Windows)
- Polling oder Event-Hook:
  - Option A: `SetWinEventHook(EVENT_SYSTEM_FOREGROUND)` — eventbasiert, effizienter
  - Option B: Polling in Intervallen (z.B. 200ms) — einfacher, aber CPU-Last
- `_get_active_monitor()` muss zwischen Cursor/Focus/Fixed Modus unterscheiden
- Muss auch bei Aufruf ausserhalb von `update_text()` funktionieren (z.B. Pre-Positioning)

**Implementierungshinweise:**
- `SetWinEventHook` braucht eine Message-Pump — tkinter-Mainloop koennte dafuer genutzt werden
- Alternativ: Hook im tkinter-Thread registrieren
- macOS: `NSWorkspace.shared().frontmostApplication` + Window-Bounds via Accessibility API

### 2.3 "Alle Monitore" (Overlay auf jedem Monitor)

**Was fehlt:**
- Config-Key: z.B. `listening.overlay_monitor: "all"`
- Mehrere tkinter-Fenster gleichzeitig — ein Toplevel pro Monitor
- Synchrones Text-Update auf allen Fenstern
- Lifecycle-Management: Fenster erstellen/zerstoeren bei Monitor-Hotplug

**Implementierungshinweise:**
- tkinter erlaubt nur EIN `Tk()` — weitere Fenster muessen `Toplevel(root)` sein
- Alle muessen im selben Thread laufen (tkinter ist single-threaded)
- Bestehender Code hat `self._root = tk.Tk()` + `self._label` — muss zu einer Liste von Fenstern/Labels refactored werden
- Performance: N Fenster mit identischem Text — `update_text` loopt ueber alle

### 2.4 Context-Menu Einstellungen im Tray

**Was fehlt (neue Menu-Eintraege):**
```
Overlay Monitor >
  Auto (Mauszeiger)        (Radio, Default)
  Focus-Follow             (Radio)
  Alle Monitore            (Radio)
  ---
  Monitor 1: "Dell U2720Q"  (Radio)
  Monitor 2: "LG 27UK850"   (Radio)
```

**Pattern folgt dem bestehenden Radiobutton-Muster** (s. Listening Mode):
1. Monitor-Liste dynamisch via Enumeration
2. Closure-Factories fuer `checked` und `action`
3. Handler ruft `state_manager` + `config_manager.update_user_setting` + Menu-Rebuild

**Platzierung im Menu:** nach "Preview" Checkbox, vor dem letzten Separator/Exit.

### 2.5 Neue Config-Keys (Vorschlag)

```yaml
listening:
  # ... bestehende Keys ...
  overlay_monitor: "auto"
  # Moegliche Werte:
  #   "auto"    — Monitor unter Mauszeiger (aktuelles Verhalten)
  #   "focus"   — Monitor des Fokus-Fensters
  #   "all"     — alle Monitore gleichzeitig
  #   1, 2, ... — fester Monitor-Index
```

---

## 3. Risiken & Technische Bedenken

### 3.1 tkinter Thread-Safety bei Monitor-Wechsel

**Risiko: MITTEL**
- Aktuell korrekt geloest: alle UI-Ops laufen via `root.after(0, callback)`
- Bei Focus-Follow: der Monitor-Wert muss atomar lesbar sein (z.B. via threading.Lock oder da nur im tkinter-Thread gelesen)
- Bei "alle Monitore": Fenster-Erstellung muss im tkinter-Thread passieren (`after()`-Pattern beibehalten)
- **Achtung:** `_get_active_monitor()` wird aktuell INNERHALB von `_position_bottom_center()` aufgerufen, was wiederum in `_update()` via `after()` laeuft — d.h. bereits im tkinter-Thread. Das ist korrekt und muss so bleiben.

### 3.2 Performance bei Polling fuer Focus-Follow

**Risiko: NIEDRIG bis MITTEL**
- Polling alle 200ms: vernachlaessigbar (~0.1% CPU)
- Besser: `SetWinEventHook` eventbasiert — kein Polling noetig
- Preview-Text-Updates passieren ohnehin alle 1.5s (`preview_interval_sec`) — Monitor-Check dabei mitzumachen ist kostenlos
- **Empfehlung:** Monitor nur bei `update_text()` neu bestimmen (wie aktuell), NICHT per separatem Polling. Das ist ausreichend fuer die meisten Use-Cases.

### 3.3 Mehrere tkinter-Fenster gleichzeitig ("alle Monitore")

**Risiko: MITTEL bis HOCH**
- tkinter ist single-threaded — alle N Fenster muessen im selben Thread verwaltet werden
- `Toplevel()` Fenster sind Standard-tkinter und funktionieren zuverlaessig
- Potenzielle Probleme:
  - `overrideredirect(True)` + `topmost` kann sich pro Monitor unterschiedlich verhalten
  - DPI-Scaling: verschiedene Monitore koennen verschiedene DPI haben — Font-Groesse und Fenster-Groesse muessen pro Monitor angepasst werden
  - Monitor-Hotplug: Fenster auf abgestecktem Monitor — tkinter gibt keine Events dafuer
- **Empfehlung:** Toplevel-Fenster bei jedem `update_text()` gegen aktuelle Monitor-Liste abgleichen (Create/Destroy bei Aenderung)

### 3.4 pystray Menu-Tiefe (Submenus)

**Risiko: NIEDRIG**
- pystray unterstuetzt verschachtelte Submenus problemlos (wird bereits fuer Model/Audio/Listening Mode verwendet)
- Ein weiteres Submenu "Overlay Monitor" ist kein technisches Problem
- Dynamische Monitor-Liste analog zur dynamischen Audio-Device-Liste
- **Einzige Einschraenkung:** pystray-Menus werden bei jedem Zugriff komplett neu erstellt — das ist bereits das bestehende Pattern und funktioniert

### 3.5 Plattform-Kompatibilitaet

**Risiko: MITTEL**
- `_get_active_monitor()` ist aktuell **rein Windows** (ctypes.windll)
- `EnumDisplayMonitors` fuer Monitor-Liste ist ebenfalls Windows-only
- Focus-Follow via `GetForegroundWindow` ist Windows-only
- **Empfehlung:** Monitor-Funktionalitaet in `platform/` abstrahieren:
  - `platform/windows/monitors.py` — Win32 API
  - `platform/macos/monitors.py` — NSScreen API
  - Oder: `preview_overlay.py` bleibt Windows-only mit Graceful Fallback (wie aktuell)

### 3.6 Monitor-ID Stabilitaet

**Risiko: NIEDRIG**
- Windows Monitor-Indizes koennen sich bei Plug/Unplug aendern
- Monitor-Name (z.B. "\\.\DISPLAY1") ist stabiler
- Config sollte entweder Index + Validierung oder Device-Name speichern
- Bei ungueltigem Monitor: Fallback auf "auto" (Maus-basiert)

---

## 4. Zusammenfassung der Erweiterungspunkte

| Datei | Was aendern | Aufwand |
|-------|-------------|---------|
| `config.defaults.yaml` | `listening.overlay_monitor: "auto"` hinzufuegen | Klein |
| `config_manager.py` | Getter fuer neuen Key, evtl. Validation | Klein |
| `preview_overlay.py` | Monitor-Enumeration, Modi (auto/focus/fixed/all), Multi-Window | Gross |
| `system_tray.py` | "Overlay Monitor" Submenu mit Radiobuttons | Mittel |
| `state_manager.py` | Handler fuer Monitor-Wechsel, Config-Persistenz | Klein |
| `platform/windows/` | Optional: Monitor-Enumeration abstrahieren | Mittel |
