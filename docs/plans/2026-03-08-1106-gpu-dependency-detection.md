# GPU Dependency Detection

As a *new user* I want **GPU dependency detection** so the app can tell me exactly what's missing for GPU acceleration instead of a generic "not available" message.

## Background

The current `gpu_detection.py` detects GPU hardware (vendor + name) and does a binary `_check_cuda_runtime()` check. When GPU acceleration doesn't work, the user sees `"CUDA/ROCm runtime not available"` with no guidance on what to fix.

The problem is that GPU acceleration requires multiple pieces to be in place, and any one of them can be the blocker:

| Piece | NVIDIA | AMD RDNA 2+ | AMD RDNA 1 |
|-------|--------|-------------|------------|
| GPU hardware | nvidia-smi | WMI | WMI |
| Runtime libs | CUDA Toolkit 12 | ROCm SDK (HIP 7.1/7.2) | ROCm 6.2 |
| CT2 wheel | CUDA build | ROCm build (official) | ROCm build (custom `+rocm62.gfx1010`) |
| Config | `device: cuda` | `device: cuda` | `device: cuda` |

The onboarding flow needs to know which piece is missing to give actionable guidance like "install CUDA Toolkit 12" or "install the ROCm ctranslate2 wheel".

## Detection Strategy

### CT2 wheel variant

The ctranslate2 wheel determines what GPU backend is available. Three detection methods, combined:

**1. pip metadata version string** (`importlib.metadata.version`):
- `4.7.1` — official build (ambiguous — could be cpu, cuda, or rocm)
- `4.7.1+rocm62.gfx1010` — custom RDNA 1 wheel (unambiguous)

**2. DLL link analysis** (scan `ctranslate2.dll` binary for imported DLL names):
- `amdhip64*.dll` or `hipblas.dll` present → ROCm build
- `cublas*.dll` or `cudart*.dll` present → CUDA build
- Neither → CPU-only build

**3. Runtime check** (`ctranslate2.get_supported_compute_types('cuda')`):
- Returns compute types → GPU backend is functional
- Raises or empty → GPU backend not working (missing runtime libs, wrong wheel, etc.)

Method 2 (DLL scan) is the most reliable for determining wheel variant without requiring runtime libs to be installed. Method 1 adds differentiation for custom wheels. Method 3 confirms the full stack works end-to-end.

### NVIDIA runtime dependencies

If CT2 is a CUDA build but runtime check fails, check for CUDA Toolkit:
- `nvidia-smi` output includes CUDA driver version (tells us drivers are OK)
- Look for `cublas64_12.dll` in PATH or common install locations
- Check `CUDA_PATH` environment variable

### AMD runtime dependencies

If CT2 is a ROCm build but runtime check fails, check for ROCm runtime:
- Check `HIP_PATH` environment variable
- Check if `_rocm_sdk_core` package is importable (pip ROCm SDK 7.2)
- Look for `amdhip64_7.dll` in system PATH

### macOS

Skip all GPU dependency detection. macOS has no CUDA/ROCm support for faster-whisper. Return cpu-only status immediately.

## Implementation Plan

### 1. Extend GpuInfo with CT2 detection

- [ ] Add `Ct2Info` dataclass: `version`, `variant` (cpu/cuda/rocm), `is_custom` (bool for local tag in version)
- [ ] `_detect_ct2_variant()` — scan `ctranslate2.dll` (Windows) or `.so` (Linux) for linked GPU library names
- [ ] `_detect_ct2_version()` — read version from `importlib.metadata.version('ctranslate2')`, parse local tag if present
- [ ] `_detect_ct2()` — combine into `Ct2Info`

### 2. Extend GpuInfo dataclass

- [ ] Replace `cuda_available: bool` with `ct2: Ct2Info` on `GpuInfo`
- [ ] Add derived property or helper: `gpu_ready` (GPU detected + matching CT2 variant + runtime works)
- [ ] Update `_check_cuda_runtime()` to remain as a separate end-to-end runtime check
- [ ] Update `detect_gpu()` to call `_detect_ct2()` and include result in `GpuInfo`

### 3. Update startup messages

- [ ] Update `print_gpu_status()` to use `Ct2Info` for specific messages:
  - GPU + wrong CT2 variant → `"CT2 is cpu-only — install the [CUDA/ROCm] wheel for GPU acceleration"`
  - GPU + right CT2 variant + runtime fails → `"[CUDA Toolkit 12 / ROCm SDK] not found — see docs/gpu-setup.md"`
  - GPU + right CT2 + runtime works + device=cpu → `"GPU ready — set device: cuda for faster transcription"` (existing)
  - No GPU + device=cuda → `"No GPU detected"` (existing)
- [ ] Keep messages concise — one line per issue, link to `docs/gpu-setup.md` for full instructions

### 4. Update system tray and main.py

- [ ] `main.py` — no changes needed (already passes `GpuInfo` through)
- [ ] `system_tray.py` — update `_get_tray_title()` if `GpuInfo` shape changes (replace `cuda_available` access)

## Implementation Details

### Ct2Info dataclass

```python
@dataclass
class Ct2Info:
    version: str            # "4.7.1", "4.7.1+rocm62.gfx1010"
    variant: str            # "cpu", "cuda", "rocm"
    is_custom: bool         # True if version has local tag (e.g. +rocm62.gfx1010)
    runtime_available: bool # True if get_supported_compute_types('cuda') works
```

### DLL scan for variant detection

```python
def _detect_ct2_variant() -> str:
    import ctranslate2
    dll_path = pathlib.Path(ctranslate2.__file__).parent / 'ctranslate2.dll'
    if not dll_path.exists():
        return 'cpu'
    data = dll_path.read_bytes()
    linked = set(re.findall(rb'([a-zA-Z0-9_\-]+\.dll)', data))
    if any(b'amdhip' in d or b'hipblas' in d for d in linked):
        return 'rocm'
    if any(b'cublas' in d or b'cudart' in d or b'cudnn' in d for d in linked):
        return 'cuda'
    return 'cpu'
```

On non-Windows platforms, look for `.so` files with `ldd`-style analysis or skip (macOS = always cpu).

### Version parsing

```python
def _detect_ct2_version() -> tuple[str, bool]:
    version = importlib.metadata.version('ctranslate2')
    is_custom = '+' in version
    return version, is_custom
```

### Updated GpuInfo

```python
@dataclass
class GpuInfo:
    vendor: str | None      # "nvidia", "amd", or None
    name: str | None        # "AMD Radeon RX 9070 XT"
    ct2: Ct2Info            # CT2 wheel info
```

`cuda_available` is replaced by `ct2.runtime_available`. Callers check `gpu_info.ct2.runtime_available` instead of `gpu_info.cuda_available`.

### Startup message logic

```python
def print_gpu_status(gpu_info: GpuInfo, configured_device: str):
    ct2 = gpu_info.ct2

    if gpu_info.name:
        print(f"   ✓ Detected {gpu_info.name}")

    if configured_device == 'cuda':
        if not gpu_info.name:
            print("   ⚠ device: cuda but no GPU detected — transcription may fail")
        elif ct2.variant == 'cpu':
            wheel = 'CUDA' if gpu_info.vendor == 'nvidia' else 'ROCm'
            print(f"   ⚠ ctranslate2 is a CPU build — install the {wheel} wheel (see docs/gpu-setup.md)")
        elif not ct2.runtime_available:
            runtime = 'CUDA Toolkit 12' if gpu_info.vendor == 'nvidia' else 'ROCm SDK'
            print(f"   ⚠ {runtime} not found — see docs/gpu-setup.md")
    elif gpu_info.name and ct2.runtime_available:
        print("   ℹ GPU ready — set device: cuda in settings for faster transcription")
```

## Scope

| File | Changes |
|------|---------|
| `gpu_detection.py` | Add `Ct2Info`, `_detect_ct2_variant()`, `_detect_ct2_version()`, `_detect_ct2()`. Refactor `GpuInfo` to include `ct2: Ct2Info`. Update `print_gpu_status()` |
| `system_tray.py` | Update `_get_tray_title()` — replace `cuda_available` with `ct2.runtime_available` |

## Success Criteria

- [ ] CT2 CPU wheel detected as `variant: cpu` on a fresh pip install
- [ ] CT2 ROCm wheel detected as `variant: rocm` on primary PC (RX 9070 XT)
- [ ] CT2 custom RDNA 1 wheel detected as `variant: rocm, is_custom: True` on secondary PC (RX 5700 XT)
- [ ] CT2 CUDA wheel detected as `variant: cuda` (needs NVIDIA test machine or CI)
- [ ] Wrong wheel message shown when GPU detected but CT2 is cpu-only
- [ ] Missing runtime message shown when right wheel but runtime libs not installed
- [ ] No regression on macOS (silent, no errors)
- [ ] No added startup delay > 100ms from CT2 detection (DLL scan is fast)
