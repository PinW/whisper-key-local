# GPU Auto-Detection

As a *new user* I want **auto GPU detection** so CUDA/ROCm mode is enabled automatically when a compatible GPU is available.

## Background

Users must manually set `device: cuda` and `compute_type: float16` in their config to use GPU acceleration. Most users with NVIDIA GPUs have CUDA already installed but don't know to change the config. AMD users need a custom CTranslate2 wheel installed first.

The goal is to detect GPU availability at startup and either auto-configure or surface clear guidance — no silent failures, no confusing error messages when CUDA isn't installed.

## Detection Strategy

**NVIDIA:** Run `nvidia-smi --query-gpu=name --format=csv,noheader` — if it returns a GPU name, NVIDIA hardware is present. Then try loading a model with `device='cuda'` to verify CUDA runtime works.

**AMD (ROCm):** Check if the installed ctranslate2 package has ROCm support. ROCm uses the same `device='cuda'` path, so the runtime check is the same — but GPU name detection differs (use `rocm-smi` or `hipInfo`).

**Key principle:** Detection is informational at startup. It logs what it finds and warns about mismatches. It does NOT auto-change the user's config — that belongs in onboarding (separate feature).

## Implementation Plan

1. Create `gpu_detection.py` module
- [ ] `detect_nvidia_gpu() -> str | None` — runs `nvidia-smi`, returns GPU name or None
- [ ] `detect_amd_gpu() -> str | None` — runs `rocm-smi` or `hipInfo`, returns GPU name or None
- [ ] `check_cuda_runtime() -> bool` — tries `ctranslate2` with `device='cuda'` in a minimal way (import check, not model load)
- [ ] `detect_gpu() -> GpuInfo` — combines the above, returns a dataclass with `vendor`, `name`, `cuda_available`

2. Integrate into startup
- [ ] Call `detect_gpu()` in `main.py` during initialization (before whisper engine setup)
- [ ] Log the result: `"Detected NVIDIA GeForce RTX 3080"` or `"No GPU detected"`
- [ ] If `device: cuda` is configured but no GPU/CUDA found → warn with actionable message
- [ ] If GPU detected but `device: cpu` → info message: `"GPU available — set device: cuda for faster transcription"`

3. Surface in system tray
- [ ] Show detected GPU in tray tooltip or menu (e.g., `"Whisper Key — RTX 3080 (GPU)"`)
- [ ] If no GPU, show `"Whisper Key — CPU"`

## Implementation Details

### gpu_detection.py

```python
import subprocess
import logging
from dataclasses import dataclass

logger = logging.getLogger(__name__)

@dataclass
class GpuInfo:
    vendor: str | None      # "nvidia", "amd", or None
    name: str | None        # "GeForce RTX 3080", "Radeon RX 5700 XT", etc.
    cuda_available: bool    # True if ctranslate2 can use device='cuda'

def detect_nvidia_gpu() -> str | None:
    try:
        result = subprocess.run(
            ['nvidia-smi', '--query-gpu=name', '--format=csv,noheader'],
            capture_output=True, text=True, timeout=5
        )
        if result.returncode == 0 and result.stdout.strip():
            return result.stdout.strip().split('\n')[0]
    except (FileNotFoundError, subprocess.TimeoutExpired):
        pass
    return None

def detect_amd_gpu() -> str | None:
    # Windows: rocm-smi or hipInfo from HIP SDK
    # macOS: not applicable (no ROCm support)
    ...

def check_cuda_runtime() -> bool:
    try:
        import ctranslate2
        return 'cuda' in ctranslate2.get_supported_compute_types('cuda')
    except Exception:
        return False

def detect_gpu() -> GpuInfo:
    nvidia = detect_nvidia_gpu()
    if nvidia:
        cuda_ok = check_cuda_runtime()
        return GpuInfo(vendor="nvidia", name=nvidia, cuda_available=cuda_ok)

    amd = detect_amd_gpu()
    if amd:
        cuda_ok = check_cuda_runtime()  # ROCm uses same 'cuda' device
        return GpuInfo(vendor="amd", name=amd, cuda_available=cuda_ok)

    return GpuInfo(vendor=None, name=None, cuda_available=False)
```

### Startup messages (in main.py)

```python
gpu = detect_gpu()

if gpu.name:
    print(f"🖥️  Detected {gpu.name}")
    if device_config == 'cuda' and not gpu.cuda_available:
        print(f"⚠️  device: cuda but CUDA runtime not available — see documentation/gpu-setup.md")
    elif device_config == 'cpu' and gpu.cuda_available:
        logger.info(f"GPU available — set device: cuda for faster transcription")
else:
    if device_config == 'cuda':
        print(f"⚠️  device: cuda but no GPU detected — falling back to CPU")
```

### Scope

| File | Change |
|------|--------|
| `gpu_detection.py` | New — GPU detection logic |
| `main.py` | Call `detect_gpu()` at startup, log results, warn on mismatches |
| `system_tray.py` | Show GPU info in tooltip |

## Open Questions

- Should detection auto-fallback `device: cuda` → `cpu` when no GPU found, or just warn? (Recommend: warn + let it fail with clear error, so user knows to fix config)
- Should `detect_amd_gpu()` be Windows-only via platform abstraction, or just try `rocm-smi` and catch FileNotFoundError?
- CTranslate2's `get_supported_compute_types('cuda')` — need to verify this works without loading a model (if it tries to init CUDA context, it could be slow or crash)

## Success Criteria

- [ ] App logs detected GPU name on startup
- [ ] `device: cuda` with no GPU shows clear warning
- [ ] `device: cpu` with GPU available shows info-level hint
- [ ] No startup delay > 1 second from detection
- [ ] System tray shows GPU/CPU status
