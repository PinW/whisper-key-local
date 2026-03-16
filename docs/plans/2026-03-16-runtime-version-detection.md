# Version-Aware Runtime Detection

Replace hardcoded DLL filename checks with ctypes API calls that return actual version numbers.

## File: `platform/windows/gpu.py`

### `_find_cuda_runtime() -> str | None`

**Before:** Check for `cublas64_12.dll` in 3 locations. Return `'12'` or `None`.

**After:**
1. Glob for `cudart64_*.dll` across: `CUDA_PATH/bin`, `site-packages/nvidia/cuda_runtime/bin`, PATH dirs
2. Load first match via `ctypes.CDLL(full_path)`
3. Call `cudaRuntimeGetVersion(pointer)` — returns `major*1000 + minor*10`
4. Decode and return `"12.6"` (or whatever version)
5. On any failure, return `None`

### `_find_rocm_runtime() -> str | None`

**Before:** Check for `amdhip64_7.dll` in 3 locations. Return HIP version from pip metadata or `'7'`.

**After:**
1. Glob for `amdhip64_*.dll` across: `C:\Windows\System32`, `HIP_PATH/bin`, `site-packages/_rocm_sdk_core/bin`, PATH dirs
2. Load first match via `ctypes.CDLL(full_path)`
3. Call `hipRuntimeGetVersion(pointer)` — returns `major*10000000 + minor*100000 + patch`
4. Decode and return `"7.2"` (major.minor only)
5. On any failure, return `None`

### Show explicit message when runtime not found

Currently, if GPU is detected but no runtime DLLs exist, the runtime line is silently skipped. Add explicit failure messages:
- `✗ NVIDIA CUDA runtime not found`
- `✗ AMD HIP runtime not found`

### Fix `_test_ct2_gpu()` device string for ROCm

Current code hardcodes `ctranslate2.get_supported_compute_types('cuda')` — this fails for ROCm CT2 wheels. Pass the correct device string based on `ct2_variant` (`'cuda'` or `'cuda'` for ROCm — check what CT2 ROCm actually expects).

### Compatibility check in `detect_and_print()`

After getting runtime version + CT2 variant, replace current `_test_ct2_gpu()` check:

```
CT2 CUDA wheel → needs CUDA major version 12
CT2 ROCm wheel → needs HIP major version 7
```

Messages:
- Compatible + works: `✓ GPU acceleration available`
- Incompatible version: `✗ CTranslate2 requires CUDA 12, found CUDA 13`
- No runtime found: `✗ CUDA runtime not found` / `✗ HIP runtime not found`

Keep `_test_ct2_gpu()` as a final verification even when versions match — the actual GPU test is the ground truth.

### DLL search order (preserve current priority)

CUDA: `CUDA_PATH/bin` → `site-packages/nvidia/cuda_runtime/bin` → PATH dirs
ROCm: `HIP_PATH/bin` → `site-packages/_rocm_sdk_core/bin` → `C:\Windows\System32` → PATH dirs

### Runtime version display

With ctypes we get more precise versions:
- `✓ NVIDIA CUDA 12.6 runtime available` (was just `12`)
- `✓ AMD HIP 7.2 runtime available` (now from ctypes, not pip metadata)

## Scope

Only `platform/windows/gpu.py` changes. No changes to `hardware_detection.py`, `main.py`, or macOS.
