# Overlay Config Schema Design

## 1. Config-Schema

### Bestehende Config (listening:)

```yaml
listening:
  preview_enabled: false
  preview_show_tooltip: true
  preview_show_overlay: false
```

### Erweiterung

```yaml
listening:
  preview_enabled: false
  preview_show_tooltip: true
  preview_show_overlay: false

  overlay:
    # Monitor-Auswahl
    # "follow_focus" = Overlay erscheint auf dem Monitor mit dem aktiven Fenster
    # "primary"      = Immer auf dem primaeren Monitor
    # "all"          = Ein Overlay-Fenster pro Monitor gleichzeitig
    # 1, 2, 3...     = Fester Monitor (nach Nummer)
    monitor: follow_focus

    # Position auf dem Monitor
    # Optionen: bottom_center, top_center, bottom_left, bottom_right,
    #           top_left, top_right, center
    position: bottom_center

    # Vertikaler Abstand vom Rand in Pixeln
    margin: 80

    # Stil
    font_size: 18
    opacity: 0.85
    bg_color: "#1a1a2e"
    text_color: "#ffffff"
```

### Warum dieses Schema

- **`monitor`** ist ein Union-Typ: String (`"follow_focus"`, `"primary"`, `"all"`) oder Integer (1, 2, 3...). Damit deckt man alle vier Anwendungsfaelle ab ohne separate Boolean-Flags.
- **`position`** als Enum statt X/Y-Koordinaten -- einfacher fuer User, und das Overlay berechnet die Pixel-Position selbst basierend auf Monitor-Geometrie.
- **`margin`** gibt vertikalen Abstand vom Rand -- bei `bottom_center` ist das der Abstand vom unteren Rand, bei `top_center` vom oberen.
- **Stil-Optionen** sind optional/nice-to-have. Sinnvolle Defaults reichen fuer v1.

### Validierung

| Feld | Typ | Default | Gueltige Werte |
|------|-----|---------|-----------------|
| `monitor` | `str \| int` | `"follow_focus"` | `"follow_focus"`, `"primary"`, `"all"`, `1`..`N` |
| `position` | `str` | `"bottom_center"` | `"bottom_center"`, `"top_center"`, `"bottom_left"`, `"bottom_right"`, `"top_left"`, `"top_right"`, `"center"` |
| `margin` | `int` | `80` | `0`..`500` |
| `font_size` | `int` | `18` | `8`..`72` |
| `opacity` | `float` | `0.85` | `0.1`..`1.0` |
| `bg_color` | `str` | `"#1a1a2e"` | Hex-Color |
| `text_color` | `str` | `"#ffffff"` | Hex-Color |


---

## 2. Tray-Menu Design

### Bestehende Struktur

```
Listening Mode ->
  * Hotkey
  o Continuous
  o Wake Word
[ ] Preview
---
Model ->
Audio Device ->
...
Exit
```

### Erweiterte Struktur

Das "Preview"-Checkbox wird zu einem Submenu mit verschachtelten Optionen:

```
Listening Mode ->
  * Hotkey
  o Continuous
  o Wake Word
Preview ->
  [x] Enabled
  ---
  Overlay ->
    [x] Show Overlay
    ---
    Monitor ->
      * Follow Focus
      o Primary Monitor
      o All Monitors
      ---
      o Monitor 1 (DELL U2723QE)
      o Monitor 2 (LG 27UK850)
    Position ->
      * Bottom Center
      o Top Center
      o Bottom Left
      o Bottom Right
---
```

### Design-Entscheidungen

1. **"Preview" wird Submenu** statt Checkbox -- enthaelt jetzt "Enabled" Toggle + Overlay-Settings.
2. **Monitor-Namen** werden dynamisch per `screeninfo` oder Win32 API gelesen und angezeigt (z.B. "Monitor 1 (DELL U2723QE)").
3. **Separator** trennt den generischen Modus (Follow Focus / Primary / All) von den nummerierten Monitoren.
4. **Position** hat nur die gaengigsten 4 Optionen im Menu (bottom_center, top_center, bottom_left, bottom_right). Weitere per Config-File.
5. **Stil-Optionen** (font_size, opacity, colors) sind nur per Config-File aenderbar, nicht per Tray -- das wuerde das Menu ueberladen.

### Implementierungs-Hinweise fuer system_tray.py

```python
# Innerhalb _create_menu():

overlay_config = self.config_manager.get_setting('listening', 'overlay') or {}
current_monitor = overlay_config.get('monitor', 'follow_focus')
current_position = overlay_config.get('position', 'bottom_center')
show_overlay = self.config_manager.get_setting('listening', 'preview_show_overlay')

# Monitor-Submenu
monitor_choices = [
    ("Follow Focus", "follow_focus"),
    ("Primary Monitor", "primary"),
    ("All Monitors", "all"),
]
# + dynamisch: nummerierte Monitore per screeninfo/win32

# Position-Submenu
position_choices = [
    ("Bottom Center", "bottom_center"),
    ("Top Center", "top_center"),
    ("Bottom Left", "bottom_left"),
    ("Bottom Right", "bottom_right"),
]
```


---

## 3. HTTP-Endpoints

### Bestehende Endpoints

```
GET /mode/preview/on     -> Preview ein
GET /mode/preview/off    -> Preview aus
GET /preview             -> Letzter Preview-Text
```

### Neue Endpoints

```
GET /overlay                          -> Aktuelle Overlay-Config (JSON)
GET /overlay/toggle                   -> Overlay ein/aus toggeln
GET /overlay/monitor/follow_focus     -> Monitor auf follow_focus setzen
GET /overlay/monitor/primary          -> Monitor auf primary setzen
GET /overlay/monitor/all              -> Monitor auf all setzen
GET /overlay/monitor/<N>              -> Monitor auf Nummer N setzen (1, 2, 3...)
GET /overlay/position/bottom_center   -> Position setzen
GET /overlay/position/top_center      -> Position setzen
GET /overlay/position/<position>      -> Position setzen (beliebig)
```

### Response-Format

**GET /overlay**
```json
{
  "ok": true,
  "overlay_enabled": true,
  "monitor": "follow_focus",
  "position": "bottom_center",
  "margin": 80,
  "font_size": 18,
  "opacity": 0.85,
  "monitors_available": [
    {"index": 1, "name": "DELL U2723QE", "primary": true, "width": 3840, "height": 2160},
    {"index": 2, "name": "LG 27UK850", "primary": false, "width": 3840, "height": 2160}
  ]
}
```

**GET /overlay/monitor/follow_focus** (und alle anderen Setter)
```json
{
  "ok": true,
  "message": "Monitor set to follow_focus",
  "monitor": "follow_focus"
}
```

### Routing in http_trigger.py

```python
# In do_GET:
elif path == "/overlay":
    self._handle_overlay_config(sm)
elif path == "/overlay/toggle":
    self._handle_overlay_toggle(sm)
elif path.startswith("/overlay/monitor/"):
    value = path.split("/overlay/monitor/")[1]
    self._handle_overlay_monitor(sm, value)
elif path.startswith("/overlay/position/"):
    value = path.split("/overlay/position/")[1]
    self._handle_overlay_position(sm, value)
```


---

## 4. Interaktions-Matrix

### Monitor-Modus vs. preview_show_overlay

| `preview_show_overlay` | `overlay.monitor` | Verhalten |
|------------------------|-------------------|-----------|
| `false` | (egal) | Kein Overlay. Monitor-Setting wird gespeichert aber ignoriert. |
| `true` | `follow_focus` | Ein Overlay-Fenster, springt zum Monitor mit aktivem Fenster. Bei Fokuswechsel: altes Overlay schliessen, neues auf Ziel-Monitor oeffnen. |
| `true` | `primary` | Ein Overlay-Fenster, fest auf dem primaeren Monitor. |
| `true` | `all` | N Overlay-Fenster gleichzeitig, eins pro erkanntem Monitor. Alle zeigen denselben Text. |
| `true` | `1`, `2`, `3`... | Ein Overlay-Fenster, fest auf dem Monitor mit der angegebenen Nummer. Fallback auf `primary` wenn Nummer nicht existiert. |

### Preview-States

| `preview_enabled` | `preview_show_overlay` | `preview_show_tooltip` | Ergebnis |
|--------------------|------------------------|------------------------|----------|
| `false` | (egal) | (egal) | Kein Preview, kein Overlay, kein Tooltip |
| `true` | `false` | `true` | Nur Tooltip im Tray |
| `true` | `true` | `false` | Nur Overlay |
| `true` | `true` | `true` | Beides: Overlay + Tooltip |

### Edge Cases

1. **Monitor wird abgesteckt waehrend Overlay aktiv**: Overlay auf diesem Monitor schliessen. Bei `follow_focus` oder `all`: automatisch re-layout. Bei fester Nummer: Fallback auf primary.
2. **Monitor wird angesteckt**: Bei `all`: neues Overlay-Fenster erstellen. Bei fester Nummer: pruefen ob der neue Monitor die gewuenschte Nummer hat.
3. **follow_focus und kein Fenster fokussiert** (Desktop fokussiert): Overlay auf dem primaeren Monitor anzeigen.
4. **Ungueltige Monitor-Nummer in Config**: Warnung loggen, Fallback auf `primary`.
5. **preview_enabled=false wird gesetzt waehrend Overlay sichtbar**: Alle Overlay-Fenster sofort schliessen.


---

## 5. config.defaults.yaml Aenderung (Diff)

```yaml
# Bestehend (unveraendert):
listening:
  mode: hotkey
  preview_enabled: false
  preview_show_tooltip: true
  preview_show_overlay: false
  preview_interval_sec: 1.5
  preview_max_audio_seconds: 30.0
  pre_buffer_duration_sec: 0.3
  post_speech_silence_ms: 800
  max_speech_duration_sec: 60.0
  min_speech_duration_sec: 0.5

  # NEU:
  overlay:
    monitor: follow_focus
    position: bottom_center
    margin: 80
    font_size: 18
    opacity: 0.85
    bg_color: "#1a1a2e"
    text_color: "#ffffff"
```


---

## 6. StateManager Aenderungen (Skizze)

Neue Felder und Methoden fuer `state_manager.py`:

```python
# __init__:
overlay_config = listening_config.get('overlay', {})
self.overlay_monitor = overlay_config.get('monitor', 'follow_focus')
self.overlay_position = overlay_config.get('position', 'bottom_center')

# Neue Methoden:
def set_overlay_monitor(self, value: str | int):
    self.overlay_monitor = value
    self.config_manager.update_user_setting('listening', 'overlay', 'monitor', value)
    if self.preview_overlay:
        self.preview_overlay.reconfigure(monitor=value)

def set_overlay_position(self, value: str):
    self.overlay_position = value
    self.config_manager.update_user_setting('listening', 'overlay', 'position', value)
    if self.preview_overlay:
        self.preview_overlay.reconfigure(position=value)

def get_overlay_config(self) -> dict:
    overlay = self.config_manager.get_setting('listening', 'overlay') or {}
    return {
        "overlay_enabled": self.preview_show_overlay,
        "monitor": overlay.get('monitor', 'follow_focus'),
        "position": overlay.get('position', 'bottom_center'),
        "margin": overlay.get('margin', 80),
        "font_size": overlay.get('font_size', 18),
        "opacity": overlay.get('opacity', 0.85),
    }

# Erweiterung von get_mode_info:
def get_mode_info(self) -> dict:
    return {
        "mode": self.listening_mode.value,
        "preview": self.preview_enabled,
        "overlay": self.preview_show_overlay,
        "overlay_monitor": self.overlay_monitor,
    }
```


---

## 7. Zusammenfassung der Aenderungen

| Datei | Aenderung |
|-------|-----------|
| `config.defaults.yaml` | `listening.overlay` Block hinzufuegen |
| `state_manager.py` | `overlay_monitor`, `overlay_position` Felder + Setter/Getter |
| `system_tray.py` | Preview Checkbox -> Submenu mit Overlay/Monitor/Position |
| `http_trigger.py` | `/overlay/*` Endpoints |
| `config_manager.py` | Validierung fuer `listening.overlay.*` Felder |
