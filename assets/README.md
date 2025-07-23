# Tray Icons

This directory contains the system tray icons for different application states.

## Icon Files

- `tray_idle.png` - Blue circle - App ready, waiting for hotkey
- `tray_recording.png` - Red microphone - Currently recording audio  
- `tray_processing.png` - Orange circle - Processing/transcribing audio

## Generating Icons

To generate the icon files, run from the project root:

```bash
python tools/create_tray_icons.py
```

This requires the Pillow library to be installed:

```bash
pip install Pillow
```

## Icon Specifications

- Size: 16x16 pixels (standard for system tray)
- Format: PNG with transparency
- Colors:
  - Idle: Cornflower blue (100, 149, 237)
  - Recording: Crimson red (220, 20, 60)
  - Processing: Orange (255, 165, 0)