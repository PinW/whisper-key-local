# Decouple GPU Detection from CTranslate2

As a *developer* I want **GPU and runtime detection independent of CTranslate2** so the app can detect the user's hardware before CT2 is installed and guide them to the correct wheel.

## Background

`gpu_detection.py` currently bundles hardware detection, runtime detection, CT2 analysis, and status reporting into a single interleaved flow. `detect_gpu()` calls `_detect_ct2()` internally, which imports `ctranslate2` — meaning the entire detection pipeline fails or returns incomplete data if CT2 isn't installed.

The standard CT2 wheel (PyPI) is the CUDA build and also works for CPU — there is no separate CPU-only variant. AMD GPUs require a custom ROCm CT2 build. CT2 uses `device='cuda'` for both NVIDIA and AMD.

**Goal:** Separate detection into 4 independent stages so stages 1-3 work without CT2, enabling a future onboarding flow that installs the correct wheel based on detected hardware.

## Current Architecture

```
detect_gpu()
  |-> _detect_ct2()                    # requires CT2
  |     |-> _detect_ct2_variant()      # import ctranslate2, read DLL
  |     |-> _detect_ct2_version()      # importlib.metadata
  |     |-> _check_cuda_runtime()      # ctranslate2.get_supported_compute_types()
  |-> _detect_nvidia_gpu()             # nvidia-smi (independent)
  |-> _detect_amd_gpu()                # powershell (independent)
  |
  \-> GpuInfo(vendor, name, ct2=Ct2Info(...))   # nested, all-or-nothing

print_gpu_status(gpu_info, configured_device)
  |-> reads gpu_info.ct2 fields
  |-> calls _find_cuda_runtime() / _find_rocm_runtime() as fallback only
```

**Problems:**
- `GpuInfo` nests `Ct2Info` — can't have GPU info without CT2 info
- `_find_cuda_runtime()` / `_find_rocm_runtime()` are buried as fallbacks in `print_gpu_status()`, not used as primary detection
- `_check_cuda_runtime()` conflates "is CUDA available on this system" with "does CT2 work with CUDA"
- No way to run detection before CT2 is installed

## Target Architecture

```
Stage 1: detect_gpu()          -> GpuInfo(vendor, name)
Stage 2: detect_runtime()      -> RuntimeInfo(cuda, rocm)
Stage 3: detect_ct2()          -> Ct2Info(installed, version, variant, is_custom)
Stage 4: test_ct2_gpu()        -> bool

                 no dependencies
Stages 1+2:     ──────────────────>  "You have an AMD GPU + ROCm runtime"
                 CT2 may not exist
Stage 3:        ──────────────────>  "CT2 is installed (ROCm build v4.5.0+rocm)"
                 CT2 must be loaded                    or "CT2 not installed"
Stage 4:        ──────────────────>  "CT2 GPU transcription works: yes/no"
```

## Data Model

### Before

```python
@dataclass
class Ct2Info:
    version: str
    variant: str            # "cuda", "rocm", "not_installed"
    is_custom: bool
    runtime_available: bool  # conflates runtime detection + CT2 test

@dataclass
class GpuInfo:
    vendor: str | None
    name: str | None
    ct2: Ct2Info             # nested — forces CT2 detection with GPU detection
```

### After

```python
@dataclass
class GpuInfo:
    vendor: str | None       # "nvidia", "amd", None
    name: str | None

@dataclass
class RuntimeInfo:
    cuda: bool               # CUDA DLLs found on system
    rocm: bool               # ROCm DLLs found on system

@dataclass
class Ct2Info:
    installed: bool
    version: str | None
    variant: str | None      # "cuda", "rocm"
    is_custom: bool
```

## Implementation Plan

1. Restructure data model
- [ ] Replace nested `GpuInfo.ct2` with standalone `GpuInfo`, `RuntimeInfo`, `Ct2Info` dataclasses
- [ ] `GpuInfo` holds only hardware fields (`vendor`, `name`)
- [ ] New `RuntimeInfo` holds system-level runtime availability (`cuda: bool`, `rocm: bool`)
- [ ] `Ct2Info` drops `runtime_available` (that's now split between `RuntimeInfo` and `test_ct2_gpu()`)
- [ ] `Ct2Info` uses `installed: bool` + nullable fields instead of sentinel value `"not_installed"`

2. Restructure public API into staged functions
- [ ] `detect_gpu() -> GpuInfo` — hardware only (keep `_detect_nvidia_gpu`, `_detect_amd_gpu` as-is)
- [ ] `detect_runtime() -> RuntimeInfo` — promote `_find_cuda_runtime()` and `_find_rocm_runtime()` to stage 2 (called unconditionally, not as fallbacks)
- [ ] `detect_ct2() -> Ct2Info` — extract from old `_detect_ct2()`, remove `_check_cuda_runtime()` call
- [ ] `test_ct2_gpu() -> bool` — rename from `_check_cuda_runtime()`, make public, works for both CUDA and ROCm

3. Update `print_gpu_status()`
- [ ] Update signature: `print_gpu_status(gpu, runtime, ct2, ct2_gpu_works, configured_device)`
- [ ] Rework decision tree to use separated data (no more `gpu_info.ct2.variant`)
- [ ] Remove inline `_find_cuda_runtime()` / `_find_rocm_runtime()` fallback calls (already in `RuntimeInfo`)

4. Update `main.py` call site
- [ ] Replace 2-line call (lines 230-231) with staged calls
- [ ] Pass all results to `print_gpu_status()`

## Implementation Details

### `gpu_detection.py` — function mapping

| Current | After | Stage | Changes |
|---------|-------|-------|---------|
| `_detect_nvidia_gpu()` | `_detect_nvidia_gpu()` | 1 | None |
| `_detect_amd_gpu()` | `_detect_amd_gpu()` | 1 | None |
| `detect_gpu()` | `detect_gpu()` | 1 | Remove `_detect_ct2()` call, return `GpuInfo` without `ct2` |
| `_find_cuda_runtime()` | `_find_cuda_runtime()` | 2 | None (already independent) |
| `_find_rocm_runtime()` | `_find_rocm_runtime()` | 2 | None (already independent) |
| *(new)* | `detect_runtime()` | 2 | Calls both `_find_*` functions, returns `RuntimeInfo` |
| `_detect_ct2_variant()` | `_detect_ct2_variant()` | 3 | None |
| `_detect_ct2_version()` | `_detect_ct2_version()` | 3 | None |
| `_detect_ct2()` | `detect_ct2()` | 3 | Make public, remove `_check_cuda_runtime()` call |
| `_check_cuda_runtime()` | `test_ct2_gpu()` | 4 | Rename, make public |
| `_read_pe_imports()` | `_read_pe_imports()` | 3 | None |

### `main.py` — call site (lines 230-231)

**Before:**
```python
gpu_info = detect_gpu()
print_gpu_status(gpu_info, whisper_config['device'])
```

**After:**
```python
gpu_info = detect_gpu()
runtime_info = detect_runtime()
ct2_info = detect_ct2()
ct2_gpu_works = test_ct2_gpu() if ct2_info.installed else False
print_gpu_status(gpu_info, runtime_info, ct2_info, ct2_gpu_works, whisper_config['device'])
```

### Scope

| File | Changes |
|------|---------|
| `src/whisper_key/gpu_detection.py` | Restructure dataclasses, split functions into stages, update `print_gpu_status` |
| `src/whisper_key/main.py` | Update import + call site (lines 32, 230-231) |

## Success Criteria

- [ ] `detect_gpu()` and `detect_runtime()` work when CT2 is not installed
- [ ] `detect_ct2()` returns `Ct2Info(installed=False, ...)` when CT2 is not installed (no crash)
- [ ] `test_ct2_gpu()` returns `False` when CT2 is not installed
- [ ] All 4 stages produce correct results when CT2 IS installed
- [ ] Startup messages remain the same for existing users (no visible change)
- [ ] Manual test: app starts correctly on Windows
