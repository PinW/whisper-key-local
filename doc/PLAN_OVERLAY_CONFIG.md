# Plan: Konfigurierbares Preview Overlay

---

## Ueberblick

Das Preview-Overlay soll vollstaendig konfigurierbar sein:
- **Welcher Monitor**: Cursor-Position, Focus-Follow, fester Monitor, alle Monitore
- **Position**: bottom_center, top_center, etc.
- **Stil**: Schriftgroesse, Transparenz, Farben
- **Einstellbar per**: Config-File + System Tray Context-Menu + HTTP API

---

## 1. Config-Schema

### Neue Config unter `listening.overlay:`

```yaml
listening:
  preview_enabled: false          # bestehend
  preview_show_tooltip: true      # bestehend
  preview_show_overlay: false     # bestehend

  overlay:
    monitor: follow_focus         # "follow_focus" | "cursor" | "primary" | "all" | 1 | 2 | 3...
    position: bottom_center       # bottom_center | top_center | bottom_left | bottom_right | top_left | top_right | center
    margin: 80                    # Pixel-Abstand vom Rand (0-500)
    font_size: 18                 # 8-72
    opacity: 0.85                 # 0.1-1.0
    bg_color: "#1a1a2e"
    text_color: "#ffffff"
```

### Monitor-Modi

| Wert | Verhalten |
|---|---|
| `follow_focus` | Overlay auf dem Monitor des aktiv fokussierten Fensters (via GetForegroundWindow + MonitorFromWindow) |
| `cursor` | Overlay auf dem Monitor unter der Maus (aktuelles Verhalten, GetCursorPos + MonitorFromPoint) |
| `primary` | Immer auf dem primaeren Monitor |
| `all` | Ein Overlay-Fenster pro Monitor gleichzeitig |
| `1`, `2`, `3`... | Fester Monitor nach Index |

### Positions-Berechnung

```
Position = Monitor-Work-Area (ohne Taskbar) + Margin + Fenster-Groesse

bottom_center: x = mon_x + (mon_w - win_w) / 2,  y = mon_y + mon_h - win_h - margin
top_center:    x = mon_x + (mon_w - win_w) / 2,  y = mon_y + margin
bottom_left:   x = mon_x + margin,                y = mon_y + mon_h - win_h - margin
bottom_right:  x = mon_x + mon_w - win_w - margin, y = mon_y + mon_h - win_h - margin
...
```

---

## 2. System Tray Menu

```
Preview ->
  [x] Enabled
  ---
  Overlay ->
    [x] Show Overlay
    ---
    Monitor ->
      * Follow Focus
      o Cursor Position
      o Primary Monitor
      o All Monitors
      ---
      o Monitor 1 (\\.\DISPLAY1)
      o Monitor 2 (\\.\DISPLAY2)
    Position ->
      * Bottom Center
      o Top Center
      o Bottom Left
      o Bottom Right
```

Monitor-Liste wird dynamisch generiert via `EnumDisplayMonitors`. Stil-Optionen (font, opacity, colors) nur per Config-File — nicht im Tray (wuerde ueberladen).

---

## 3. HTTP API

```
GET /overlay                       → {"monitor": "follow_focus", "position": "bottom_center", "monitors": [...]}
GET /overlay/toggle                → Overlay ein/aus (preview_show_overlay)
GET /overlay/monitor/follow_focus  → Monitor-Modus aendern
GET /overlay/monitor/cursor        → Monitor-Modus aendern
GET /overlay/monitor/primary       → Monitor-Modus aendern
GET /overlay/monitor/all           → Monitor-Modus aendern
GET /overlay/monitor/1             → Fester Monitor
GET /overlay/position/bottom_center → Position aendern
GET /overlay/position/top_center    → Position aendern
```

---

## 4. Implementierungsplan

### Phase A: Monitor-Utility Modul (Basis)

**Neue Datei:** `src/whisper_key/platform/windows/monitors.py`

Win32 Monitor-Utilities via ctypes (kein neues Dependency):
- `enumerate_monitors() -> list[MonitorInfo]` — Alle Monitore mit Index, Name, Rect, Work-Area, Primary-Flag
- `get_monitor_by_index(index) -> MonitorInfo`
- `get_primary_monitor() -> MonitorInfo`
- `get_monitor_at_cursor() -> MonitorInfo`
- `get_monitor_of_focused_window() -> MonitorInfo` — GetForegroundWindow + MonitorFromWindow
- `MonitorInfo` dataclass mit: index, name, x, y, w, h, work_x, work_y, work_w, work_h, is_primary

**KRITISCH:** `ctypes.windll.shcore.SetProcessDpiAwareness(2)` muss VOR `tk.Tk()` aufgerufen werden — sonst falsche Koordinaten bei Mixed-DPI.

### Phase B: Overlay Refactoring

**Datei:** `src/whisper_key/preview_overlay.py`

Refactoring der bestehenden Klasse:
- Konstruktor bekommt overlay_config dict (monitor, position, margin, font_size, opacity, colors)
- `_resolve_monitor()` — je nach Modus: follow_focus, cursor, primary, fixed(N)
- `_calculate_position(monitor_info)` — Position berechnen basierend auf position + margin
- Stil-Parameter aus Config statt hardcoded
- Fuer "all": Multi-Window mit `Toplevel()` pro Monitor (nur wenn `monitor: "all"`)
- DPI-Awareness setzen bei Init

### Phase C: Config + Persistenz

**Dateien:** `config.defaults.yaml`, `config_manager.py`

- Neue `overlay:` Sub-Sektion unter `listening:`
- `get_overlay_config() -> dict`
- `update_overlay_setting(key, value)` — persistiert in user_settings.yaml
- Validierung: monitor (str|int), position (enum), margin (0-500), font_size (8-72), opacity (0.1-1.0)

### Phase D: Tray Integration

**Datei:** `system_tray.py`

- "Preview" wird Submenu statt Checkbox
- "Overlay" Sub-Submenu mit:
  - Show Overlay Checkbox
  - Monitor Radiobuttons (dynamisch + fixe Optionen)
  - Position Radiobuttons
- Callbacks an `state_manager` / `config_manager`

### Phase E: HTTP + StateManager

**Dateien:** `http_trigger.py`, `state_manager.py`

- /overlay/* Endpoints in http_trigger.py
- state_manager: `set_overlay_monitor()`, `set_overlay_position()`, `get_overlay_config()`
- Overlay zur Laufzeit rekonfigurieren (kein Neustart)

---

## 5. Betroffene Dateien

| Datei | Aenderung |
|---|---|
| `platform/windows/monitors.py` | NEU — Monitor-Enumeration |
| `preview_overlay.py` | Refactoring — Config-driven, Multi-Monitor, DPI |
| `config.defaults.yaml` | overlay: Sub-Sektion |
| `config_manager.py` | get/update overlay config, Validierung |
| `system_tray.py` | Preview Submenu mit Monitor/Position |
| `http_trigger.py` | /overlay/* Endpoints |
| `state_manager.py` | Overlay-Config Setter/Getter |
| `main.py` | Overlay-Config an PreviewOverlay durchreichen |

---

## 6. Interaktions-Matrix

| preview_enabled | preview_show_overlay | monitor | Verhalten |
|---|---|---|---|
| false | * | * | Kein Preview, kein Overlay |
| true | false | * | Preview aktiv (HTTP/Tooltip), kein Overlay |
| true | true | follow_focus | Overlay auf Monitor des fokussierten Fensters |
| true | true | cursor | Overlay auf Monitor unter Mauszeiger |
| true | true | primary | Overlay auf primaerer Monitor |
| true | true | all | Ein Overlay pro Monitor |
| true | true | 2 | Overlay auf Monitor 2 (Fallback: primary) |

---

## 7. Risiken + Mitigations

| Risiko | Mitigation |
|---|---|
| DPI-Scaling falsche Koordinaten | SetProcessDpiAwareness(2) bei App-Start |
| Monitor-Index aendert sich bei Hotplug | Fallback auf primary bei ungueltigem Index |
| "all" Mode: N tkinter Fenster | Toplevel() statt Tk(), lazy create/destroy |
| Focus-Follow Polling-Last | Kein Polling noetig — bei jedem update_text() Monitor neu bestimmen (1.5s Intervall) |
| macOS Kompatibilitaet | monitors.py nur unter platform/windows/, macOS Fallback auf primary |
| Tray-Menu zu tief verschachtelt | Max 3 Ebenen (Preview → Overlay → Monitor/Position) |

---

## 8. Aufwandsschaetzung

| Phase | Aufwand |
|---|---|
| A: Monitor-Utility | 2-3h |
| B: Overlay Refactoring | 3-4h |
| C: Config + Persistenz | 1-2h |
| D: Tray Integration | 2-3h |
| E: HTTP + StateManager | 1-2h |
| **Gesamt** | **9-14h** |
