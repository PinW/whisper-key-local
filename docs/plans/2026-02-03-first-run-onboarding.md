# First-Run Onboarding

## Goal

Guide new users through initial configuration on first launch, eliminating the need to manually edit YAML.

## Detection

Add `onboarding_complete: false` at the end of `config.defaults.yaml`. When the app starts and this is `false`, run the onboarding flow before normal startup.

## Onboarding Steps

Uses the `terminal_ui.prompt_choice()` system (already built for permissions prompt).

### 1. Welcome + Model Selection

```
┌─────────────────────────────────────────────────────────┐
│ Welcome to Whisper Key! Let's get you set up...         │
│                                                         │
│ [1] tiny (fastest, least accurate, ~75MB)               │
│ [2] base (good balance, ~150MB)                         │
│ [3] small (better accuracy, ~500MB)                     │
│ [4] medium (high accuracy, ~1.5GB)                      │
│ [5] large-v3 (best accuracy, ~3GB)                      │
└─────────────────────────────────────────────────────────┘
```

Config: `whisper.model`

### 2. Processing Device (CPU vs GPU)

Detect NVIDIA GPU availability first, then present options:

**If NVIDIA GPU detected:**
```
┌─────────────────────────────────────────────────────────┐
│ Where should Whisper run?                               │
│                                                         │
│ [1] GPU - NVIDIA GeForce RTX 3080 (Recommended)         │
│     Faster transcription, requires CUDA 12              │
│ [2] CPU                                                 │
│     Works everywhere, slower but reliable               │
└─────────────────────────────────────────────────────────┘
```

**If no GPU detected:**
```
┌─────────────────────────────────────────────────────────┐
│ No NVIDIA GPU detected. Using CPU for processing.       │
│                                                         │
│ Press Enter to continue...                              │
└─────────────────────────────────────────────────────────┘
```

Config: `whisper.device` (cpu/cuda), `whisper.compute_type` (auto-set: int8 for CPU, float16 for GPU)

**GPU Detection:**
```python
def detect_nvidia_gpu():
    try:
        import subprocess
        result = subprocess.run(
            ['nvidia-smi', '--query-gpu=name', '--format=csv,noheader'],
            capture_output=True, text=True, timeout=5
        )
        if result.returncode == 0 and result.stdout.strip():
            return result.stdout.strip().split('\n')[0]  # First GPU name
    except (FileNotFoundError, subprocess.TimeoutExpired):
        pass
    return None
```

**CUDA Availability Check:**

If user selects GPU, verify CUDA is usable:
```python
def check_cuda_available():
    try:
        import torch
        return torch.cuda.is_available()
    except ImportError:
        return False
```

If CUDA not available after GPU selection, show:
```
┌─────────────────────────────────────────────────────────┐
│ CUDA not ready. GPU detected but CUDA 12 not installed. │
│                                                         │
│ To use GPU acceleration:                                │
│   winget install Nvidia.CUDA --version 12.9             │
│                                                         │
│ [1] Continue with CPU for now                           │
│ [2] Exit and install CUDA first                         │
└─────────────────────────────────────────────────────────┘
```

### 3. Audio Device Confirmation

List available input devices, highlight the current default:

```
┌─────────────────────────────────────────────────────────┐
│ Which microphone should Whisper Key use?                │
│                                                         │
│ [1] MacBook Pro Microphone (default)                    │
│ [2] External USB Mic                                    │
│ [3] AirPods Pro                                         │
└─────────────────────────────────────────────────────────┘
```

Config: `audio.input_device` (store device name, not index)

### 4. System Tray

```
┌─────────────────────────────────────────────────────────┐
│ Show system tray icon?                                  │
│                                                         │
│ [1] Yes (Recommended)                                   │
│     Access settings and quit from menu bar              │
│ [2] No                                                  │
│     Run in background, quit with Ctrl+C                 │
└─────────────────────────────────────────────────────────┘
```

Config: `system_tray.enabled`

### 5. Auto-Paste (last, may require restart on macOS)

```
┌─────────────────────────────────────────────────────────┐
│ Auto-paste transcriptions?                              │
│                                                         │
│ [1] Yes (Recommended)                                   │
│     Transcribe directly to cursor position              │
│ [2] No                                                  │
│     Copy to clipboard, paste manually                   │
└─────────────────────────────────────────────────────────┘
```

Config: `clipboard.auto_paste`

On macOS, if user selects Yes:
- Check accessibility permission
- If not granted, show existing permission prompt (from `permissions.py`)
- Prompt restart if permission was just requested

### 6. Completion

```
Setup complete! Starting Whisper Key...

Your settings are saved in: ~/.whisper-key/config.yaml
Press [fn+control] to start recording.
```

Set `onboarding_complete: true` in user config.

## Implementation

### Files to Modify

| File | Change |
|------|--------|
| `config.defaults.yaml` | Add `onboarding_complete: false` |
| `main.py` | Check flag, run onboarding before normal startup |
| `terminal_ui.py` | Add `prompt_choice_single()` for single-select with descriptions |

### New Files

| File | Purpose |
|------|---------|
| `onboarding.py` | Onboarding flow logic |

### terminal_ui.py Enhancements

Current `prompt_choice()` works well. May need:
- Multi-line descriptions (already supported via tuples)
- Possibly a "text input" prompt for custom device names (future)

### Audio Device Discovery

Use sounddevice to list input devices:

```python
import sounddevice as sd

def get_input_devices():
    devices = sd.query_devices()
    return [(i, d['name']) for i, d in enumerate(devices) if d['max_input_channels'] > 0]
```

### Flow

```
main.py
  └── if not config.onboarding_complete:
        └── onboarding.run(config_manager)
              ├── prompt model selection → save
              ├── detect GPU → prompt device selection → save
              │     └── if GPU selected: verify CUDA → fallback to CPU if needed
              ├── prompt audio device → save
              ├── prompt system tray → save
              ├── prompt auto-paste → save
              │     └── (macOS) check/request accessibility permission
              └── set onboarding_complete: true
```

## Edge Cases

- **Re-run onboarding**: User can delete `onboarding_complete` line or set to `false` to re-run
- **Ctrl+C during onboarding**: Exit cleanly, don't save partial config
- **No audio devices**: Show error, suggest checking hardware
- **macOS permission denied**: Handled by existing `permissions.py` flow
- **GPU detected but CUDA missing**: Offer fallback to CPU with install instructions
- **nvidia-smi not in PATH**: Treat as no GPU detected, default to CPU

## Future Enhancements

- Skip individual steps if already configured
- `--setup` CLI flag to force re-run onboarding
- GUI wizard (when GUI is added)
