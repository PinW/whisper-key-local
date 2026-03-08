# GPU Dependency Detection

As a *new user* I want **GPU dependency detection** so the app can tell me exactly what's missing for GPU acceleration instead of a generic "not available" message.

## Background

The current `gpu_detection.py` detects GPU hardware (vendor + name) and does a binary `_check_cuda_runtime()` check. When GPU acceleration doesn't work, the user sees `"CUDA/ROCm runtime not available"` with no guidance on what to fix.

GPU acceleration requires multiple pieces to be in place, and any one of them can be the blocker:

| Piece | NVIDIA | AMD RDNA 2+ | AMD RDNA 1 |
|-------|--------|-------------|------------|
| GPU hardware | nvidia-smi | WMI | WMI |
| Runtime libs | CUDA Toolkit 12 | ROCm SDK (HIP 7.1/7.2) | ROCm 6.2 |
| CT2 wheel | Standard (includes CUDA) | ROCm build (official) | ROCm build (custom `+rocm62.gfx1010`) |
| Config | `device: cuda` | `device: cuda` | `device: cuda` |

**Key insight:** The standard pip CT2 wheel IS the CUDA build — there is no separate CPU-only variant. The same binary supports both CPU and CUDA modes. The only distinct variant is the ROCm build, which replaces CUDA linkage with HIP/ROCm linkage.

## Detection Strategy

### CT2 wheel variant

Only two variants exist in practice:

| DLL links against | Variant | Supports |
|---|---|---|
| `cublas` / `cudart` / `cudnn` | `cuda` | CPU + NVIDIA GPU (standard pip install) |
| `amdhip64` / `hipblas` | `rocm` | CPU + AMD GPU |

Detection uses two methods:

**1. DLL link analysis** (scan `ctranslate2.dll` binary for imported DLL names):
- `amdhip64*.dll` or `hipblas.dll` present → `rocm`
- `cublas*.dll` or `cudart*.dll` present → `cuda` (standard build)

**2. pip metadata version string** (`importlib.metadata.version`):
- `4.7.1` — official build
- `4.7.1+rocm62.gfx1010` — custom RDNA 1 wheel (local tag identifies custom builds)

**3. Runtime check** (`ctranslate2.get_supported_compute_types('cuda')`):
- Confirms the full stack works end-to-end (~10-50ms, initializes GPU context)

### NVIDIA runtime dependency detection

When CT2 is the standard `cuda` build + NVIDIA GPU detected, but runtime check fails — the CUDA Toolkit is likely missing. Detection (fast file-existence checks):

1. Check `CUDA_PATH` env var → look for `bin\cublas64_12.dll`
2. Check pip-installed nvidia packages: `site-packages\nvidia\cublas\bin\`
3. Scan `PATH` for `cublas64_12.dll`

Note: `nvidia-smi` shows driver CUDA capability, NOT installed toolkit. Don't use it for toolkit detection.

### AMD runtime dependency detection

When CT2 is the `rocm` build + AMD GPU detected, but runtime check fails — ROCm runtime is likely missing. Two install methods exist:

**HIP SDK (system install):**
1. Check `HIP_PATH` env var → look for `bin\amdhip64_7.dll`
2. Fallback: check `HIP_DIR`, `HIPInstallDir` env vars

**ROCm SDK (pip install):**
1. Check `importlib.util.find_spec("_rocm_sdk_core")` (fast, no import)
2. If found, check `_rocm_sdk_core/bin/amdhip64_7.dll`

### CT2 variant / GPU vendor mismatch

When the CT2 wheel doesn't match the detected GPU:
- NVIDIA GPU + ROCm CT2 → "ctranslate2 is built for ROCm — install the standard wheel"
- AMD GPU + standard CUDA CT2 → "ctranslate2 is built for CUDA — install the ROCm wheel"

### macOS

Skip all dependency detection. macOS has no CUDA/ROCm support for faster-whisper.

### Error handling

If ctranslate2 is not installed or metadata is missing, handle gracefully:
- `ImportError` from `import ctranslate2` → `Ct2Info` with variant="not_installed"
- `PackageNotFoundError` from `importlib.metadata.version()` → version="unknown"

## Implementation Plan

### 1. Add CT2 detection

- [ ] Add `Ct2Info` dataclass: `version`, `variant` (cuda/rocm/not_installed), `is_custom`, `runtime_available`
- [ ] `_detect_ct2_variant()` — scan `ctranslate2.dll` for linked GPU library names
- [ ] `_detect_ct2_version()` — read version from `importlib.metadata`, parse local tag
- [ ] `_detect_ct2()` — combine into `Ct2Info`, handle ImportError/PackageNotFoundError
- [ ] `_check_cuda_runtime()` — keep as end-to-end runtime check (already exists)

### 2. Add runtime dependency detection

- [ ] `_find_cuda_runtime()` — check `CUDA_PATH`, pip nvidia packages, PATH for `cublas64_12.dll`
- [ ] `_find_rocm_runtime()` — check `HIP_PATH`/`HIP_DIR`, `_rocm_sdk_core` pip package, PATH for `amdhip64_7.dll`
- [ ] Only run the relevant check based on CT2 variant (cuda → NVIDIA deps, rocm → AMD deps)
- [ ] Store result on `Ct2Info` or return separately for message logic

### 3. Refactor GpuInfo

- [ ] Replace `cuda_available: bool` with `ct2: Ct2Info` on `GpuInfo`
- [ ] Update `detect_gpu()` to call `_detect_ct2()` and include result
- [ ] Update all callers (`system_tray.py` `_get_tray_title()`)

### 4. Update startup messages

- [ ] Update `print_gpu_status()` with specific messages for each scenario:
  - CT2 not installed → "ctranslate2 not found"
  - GPU + variant/vendor mismatch → "ctranslate2 is built for [X] — install the [Y] wheel"
  - GPU + right variant + missing runtime → "[CUDA Toolkit 12 / ROCm SDK] not found — see docs/gpu-setup.md"
  - GPU + everything works + device=cpu → "GPU ready — set device: cuda"
  - No GPU + device=cuda → "No GPU detected"
- [ ] Keep messages to one line each, link to `docs/gpu-setup.md`

## Implementation Details

### Ct2Info dataclass

```python
@dataclass
class Ct2Info:
    version: str            # "4.7.1", "4.7.1+rocm62.gfx1010", "unknown"
    variant: str            # "cuda", "rocm", "not_installed"
    is_custom: bool         # True if version has local tag (e.g. +rocm62.gfx1010)
    runtime_available: bool # True if get_supported_compute_types('cuda') works
```

### DLL scan for variant detection

```python
def _detect_ct2_variant() -> str:
    try:
        import ctranslate2
    except ImportError:
        return 'not_installed'
    dll_path = pathlib.Path(ctranslate2.__file__).parent / 'ctranslate2.dll'
    if not dll_path.exists():
        return 'cuda'  # default assumption if DLL not found at expected path
    data = dll_path.read_bytes()
    linked = set(re.findall(rb'([a-zA-Z0-9_\-]+\.dll)', data))
    if any(b'amdhip' in d or b'hipblas' in d for d in linked):
        return 'rocm'
    return 'cuda'
```

### Runtime dependency checks

```python
def _find_cuda_runtime() -> bool:
    cuda_path = os.environ.get('CUDA_PATH')
    if cuda_path:
        dll = os.path.join(cuda_path, 'bin', 'cublas64_12.dll')
        if os.path.isfile(dll):
            return True

    for sp in site.getsitepackages():
        cublas_bin = os.path.join(sp, 'nvidia', 'cublas', 'bin')
        if os.path.isdir(cublas_bin) and any(Path(cublas_bin).glob('cublas64_12*')):
            return True

    for d in os.environ.get('PATH', '').split(os.pathsep):
        if os.path.isfile(os.path.join(d, 'cublas64_12.dll')):
            return True

    return False


def _find_rocm_runtime() -> bool:
    for var in ('HIP_PATH', 'HIP_DIR'):
        hip_path = os.environ.get(var)
        if hip_path and os.path.isfile(os.path.join(hip_path, 'bin', 'amdhip64_7.dll')):
            return True

    spec = importlib.util.find_spec('_rocm_sdk_core')
    if spec and spec.submodule_search_locations:
        core_bin = os.path.join(spec.submodule_search_locations[0], 'bin')
        if os.path.isfile(os.path.join(core_bin, 'amdhip64_7.dll')):
            return True

    for d in os.environ.get('PATH', '').split(os.pathsep):
        if os.path.isfile(os.path.join(d, 'amdhip64_7.dll')):
            return True

    return False
```

### Startup message logic

```python
def print_gpu_status(gpu_info: GpuInfo, configured_device: str):
    ct2 = gpu_info.ct2

    if gpu_info.name:
        print(f"   ✓ Detected {gpu_info.name}")

    if configured_device == 'cuda':
        if not gpu_info.name:
            print("   ⚠ device: cuda but no GPU detected — transcription may fail")
        elif ct2.variant == 'not_installed':
            print("   ⚠ ctranslate2 not found")
        elif ct2.variant == 'rocm' and gpu_info.vendor == 'nvidia':
            print("   ⚠ ctranslate2 is built for ROCm — install the standard wheel (see docs/gpu-setup.md)")
        elif ct2.variant == 'cuda' and gpu_info.vendor == 'amd':
            print("   ⚠ ctranslate2 is built for CUDA — install the ROCm wheel (see docs/gpu-setup.md)")
        elif not ct2.runtime_available:
            runtime = 'CUDA Toolkit 12' if gpu_info.vendor == 'nvidia' else 'ROCm SDK'
            print(f"   ⚠ {runtime} not found — see docs/gpu-setup.md")
    elif gpu_info.name and ct2.runtime_available:
        print("   ℹ GPU ready — set device: cuda in settings for faster transcription")
```

## Scope

| File | Changes |
|------|---------|
| `gpu_detection.py` | Add `Ct2Info`, CT2 variant/version detection, runtime dependency checks, refactor `GpuInfo`, update `print_gpu_status()` |
| `system_tray.py` | Update `_get_tray_title()` — replace `cuda_available` with `ct2.runtime_available` |

## Success Criteria

- [ ] Standard CT2 wheel detected as `variant: cuda` on any machine
- [ ] ROCm CT2 wheel detected as `variant: rocm` on primary PC (RX 9070 XT)
- [ ] Custom RDNA 1 CT2 wheel detected as `variant: rocm, is_custom: True` on secondary PC (RX 5700 XT)
- [ ] Variant/vendor mismatch shows specific "wrong wheel" message
- [ ] Missing CUDA Toolkit shows "CUDA Toolkit 12 not found" (not generic "not available")
- [ ] Missing ROCm SDK shows "ROCm SDK not found" (not generic "not available")
- [ ] ctranslate2 not installed handled gracefully (no crash)
- [ ] No regression on macOS (silent, no errors)
- [ ] No added startup delay > 100ms from dependency detection
