# Tray Icon Design

Platform-specific system tray / menu bar icons for whisper-key-local.

## Current State

Three PNG icons in `src/whisper_key/assets/`:
- `tray_idle.png` - Microphone icon (default state)
- `tray_recording.png` - Recording indicator
- `tray_processing.png` - Processing indicator

**Problem:** These are colored icons designed for Windows. On macOS:
- They don't adapt to dark/light mode
- May appear washed out or invisible depending on menu bar color
- Not designed to Apple's sizing specifications

---

## Platform Requirements

### Windows System Tray

| Aspect | Requirement |
|--------|-------------|
| Format | PNG (ICO also works) |
| Size | 16x16, 24x24, or 32x32 px |
| Color | Full color supported |
| Background | Transparent or solid |
| Dark mode | Not applicable (tray is always dark) |

Windows tray icons can be colorful and don't need multiple variants.

### macOS Menu Bar

| Aspect | Requirement |
|--------|-------------|
| Format | PNG with alpha channel (or PDF) |
| Canvas size | 22x22 pt (@1x), 44x44 pt (@2x) |
| Content size | 16x16 pt centered, 32x32 pt (@2x) |
| Color | **Black only** (alpha channel defines shape) |
| Background | Fully transparent |
| Dark mode | Template images auto-adapt |

macOS icons must be **template images** - monochrome with alpha channel only.

---

## Asset Structure

Following the existing platform abstraction pattern from `documentation/design/macos-support.md`:

### Directory Layout

```
src/whisper_key/platform/
├── __init__.py              # Add: from .{platform} import icons
├── macos/
│   ├── icons.py             # get_tray_icons() -> dict of PIL Images
│   └── assets/
│       ├── tray_idle.png
│       ├── tray_recording.png
│       └── tray_processing.png
└── windows/
    ├── icons.py             # get_tray_icons() -> dict of PIL Images
    └── assets/
        ├── tray_idle.png
        ├── tray_recording.png
        └── tray_processing.png

src/whisper_key/assets/
├── sounds/                  # Shared audio assets (unchanged)
└── ...                      # Other shared assets (non-platform-specific)
```

### Interface Contract

```python
# platform/*/icons.py
def get_tray_icons() -> dict[str, Image.Image]:
    """Load and return tray icons for this platform."""
    return {
        "idle": Image.open(...),
        "recording": Image.open(...),
        "processing": Image.open(...)
    }
```

Usage in `system_tray.py`:
```python
from .platform import icons
self.icons = icons.get_tray_icons()
```

---

## Icon Specifications

### macOS Template Icons

Design constraints:
- **Monochrome only** - Use black (#000000) pixels
- **Alpha channel for shading** - Opacity levels create visual depth
- **Centered content** - 16x16 pt content in 22x22 pt canvas
- **No colors** - System ignores color, only reads alpha

State differentiation (since we can't use color):
| State | Visual Treatment |
|-------|-----------------|
| Idle | Standard microphone outline |
| Recording | Filled/solid microphone, or add recording dot |
| Processing | Microphone with activity indicator (dots, spinner effect) |

### Windows Icons

Keep existing colored icons or create new ones:
| State | Visual Treatment |
|-------|-----------------|
| Idle | Microphone (neutral color) |
| Recording | Microphone with red accent/dot |
| Processing | Microphone with processing indicator |

---

## Code Changes

### system_tray.py

Replace direct asset loading with platform abstraction:

```python
from .platform import icons

def _load_icons_to_cache(self):
    self.icons = icons.get_tray_icons()
```

### platform/__init__.py

Add icons to the platform routing:

```python
if IS_MACOS:
    from .macos import icons
else:
    from .windows import icons
```

### pystray Template Mode

pystray automatically calls `setTemplate_(True)` on macOS. No additional code needed if we provide proper monochrome PNGs with alpha channels.

### Retina Support

Use 44x44 px PNG (the @2x size) as the single macOS asset. Downscaling looks fine; upscaling looks blurry. This avoids complexity of loading multiple files.

---

## Implementation Plan

### Phase 1: Platform Abstraction

1. Create `platform/windows/assets/` directory, copy existing icons
2. Create `platform/macos/assets/` directory, copy same icons (placeholder)
3. Create `platform/windows/icons.py` with `get_tray_icons()`
4. Create `platform/macos/icons.py` with `get_tray_icons()`
5. Update `platform/__init__.py` to route icons module
6. Update `system_tray.py` to use `icons.get_tray_icons()`
7. Remove old icons from `assets/` root

### Phase 2: macOS Icon Design

1. Design macOS template icons:
   - 44x44 px canvas
   - 32x32 px centered content
   - Black pixels, alpha-only shading
   - Transparent background
2. Replace placeholder icons in `platform/macos/assets/`

### Phase 3: Testing

- [ ] macOS light mode
- [ ] macOS dark mode
- [ ] macOS with light wallpaper
- [ ] macOS with dark wallpaper
- [ ] macOS "Reduce Transparency" accessibility setting
- [ ] Windows (regression test)

---

## Icon Concept

Initial design direction:

**Core visual:** Keyboard key in 3D perspective, viewed from user's angle (slightly below)

**Elements:**
- Microphone icon on the key face
- Key "presses" down on activation (visual feedback for state change)
- Red recording dot when recording (possibly animated/flashing)

**State mapping:**

| State | Visual |
|-------|--------|
| Idle | Key in raised/default position |
| Recording | Key pressed down + red recording dot |
| Processing | Key pressed + processing indicator (dots? spinner?) |

**Considerations for macOS:**
- Template images are monochrome - red dot won't work directly
- However, macOS shows a system mic icon in menu bar when recording audio, so recording state is already indicated by the OS
- Decision: Use monochrome template images for macOS (simpler, native feel)
- 3D effect achievable with alpha channel shading/gradients

---

## Design Resources

- Research: `documentation/research/macos-menubar-icons.md`
- Research: `documentation/research/icon-design-tools.md`
- Bjango guide: https://bjango.com/articles/designingmenubarextras/
- Apple HIG: https://developer.apple.com/design/human-interface-guidelines/the-menu-bar

---

*Created: 2026-02-04*
