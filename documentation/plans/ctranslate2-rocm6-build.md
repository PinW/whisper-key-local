# CTranslate2 ROCm 6.2 Build — COMPLETE

*Built CTranslate2 v4.7.1 from source with ROCm 6.2 on Windows, targeting gfx1010 (RX 5700 XT).*
*GPU transcription verified working — 2026-02-06.*

## Why build from source?

The pre-built CTranslate2 v4.7.1 ROCm wheel (from GitHub releases):
- Built against ROCm 7.1.1 — our system runs ROCm 6.2 (driver-locked)
- Targets `gfx1030;gfx1100;...` — no gfx1010
- GPU loads and detects, but GEMM fails during inference (`CUBLAS_STATUS_INVALID_VALUE`)
- See `rocm-gfx1010-build-plan.md` for full diagnosis

## Prerequisites installed

| Tool | Version | Purpose |
|------|---------|---------|
| ROCm HIP SDK | 6.2 | GPU compiler, runtime, math libs |
| Community rocBLAS | gfx1010 Tensile kernels | GEMM operations for our GPU arch |
| MSVC Build Tools 2026 | v14.50 + v14.44 | Linker, runtime libs, Windows SDK |
| CMake | 4.2.1 (pip) | Build system |
| Ninja | 1.13.0 (pip) | Fast parallel builds |
| Python | 3.13.5 | Target runtime |
| pybind11 | 3.0.1 (pip) | Python C++ bindings |

## Build steps — exactly what we did

### 1. Clone CTranslate2 v4.7.1

```
git clone --branch v4.7.1 --depth 1 --recurse-submodules https://github.com/OpenNMT/CTranslate2.git
```

Submodules: cpu_features, cutlass, cxxopts, googletest, ruy, spdlog, thrust.

### 2. Install MSVC Build Tools

ROCm's clang on Windows delegates linking to MSVC's `lld-link`, which needs MSVC runtime libraries (`msvcrt.lib`, `oldnames.lib`) and Windows SDK headers.

Downloaded "Build Tools for Visual Studio 2026" and selected **"Desktop development with C++"** workload. Only needed:
- MSVC Build Tools for x64/x86 (Latest) — compiler and linker libs
- Windows 11 SDK — system headers and libs

Also installed **MSVC v143 (VS 2022)** toolchain alongside v145 — needed because v14.50 headers use `__builtin_verbose_trap` which Clang 19.0.0 doesn't support (see workaround below).

### 3. CMake configure

Key flags and why each is needed:

```
cmake -GNinja -DCMAKE_BUILD_TYPE=Release -DCMAKE_POLICY_VERSION_MINIMUM=3.5 -S . -B build \
  -DBUILD_CLI=OFF \
  -DWITH_MKL=OFF \
  -DWITH_DNNL=OFF \
  -DOPENMP_RUNTIME=NONE \
  -DWITH_HIP=ON \
  -DCMAKE_HIP_ARCHITECTURES=gfx1010 \
  -DCMAKE_HIP_COMPILER=<rocm>/bin/clang++.exe \
  -DCMAKE_HIP_COMPILER_ROCM_ROOT=<rocm> \
  -DCMAKE_PREFIX_PATH=<rocm> \
  "-DCMAKE_HIP_FLAGS=-D_MSVC_STL_DOOM_FUNCTION(mesg)=__builtin_trap()" \
  "-DCMAKE_CXX_FLAGS=-D_MSVC_STL_DOOM_FUNCTION(mesg)=__builtin_trap()"
```

| Flag | Why |
|------|-----|
| `WITH_MKL=OFF`, `WITH_DNNL=OFF` | No Intel oneAPI installed; GPU-only inference doesn't need it |
| `OPENMP_RUNTIME=NONE` | Default `INTEL` expects libiomp5 (Intel OpenMP); skip it |
| `CMAKE_POLICY_VERSION_MINIMUM=3.5` | `third_party/cpu_features` has old cmake_minimum_required; CMake 4.2 rejects it |
| `CMAKE_HIP_COMPILER_ROCM_ROOT` | CMake 4.2's HIP module can't auto-detect ROCm root on Windows |
| `_MSVC_STL_DOOM_FUNCTION` override | MSVC 2026 (v14.50) headers use `__builtin_verbose_trap` which Clang 19.0.0 doesn't have; this pre-defines the macro to use `__builtin_trap()` instead (header has `#ifndef` guard) |
| 8.3 short paths (`PROGRA~1`) | Paths with spaces break CMake `-D` argument parsing through the cmd.exe/batch chain |

Environment setup (via `vcvars64.bat` before cmake):
- `vcvars64.bat` loads MSVC linker + Windows SDK paths
- `ROCM_PATH`, `HIP_PATH`, `HIP_PLATFORM=amd`, `HIP_DEVICE_LIB_PATH` set for HIP
- `CC`/`CXX` set to ROCm clang; `PATH` includes ROCm bin

### 4. Source patches (3 files)

#### `src/cuda/primitives.cu` — hipBLAS type mismatch

CTranslate2 v4.7.1 was written for ROCm 7 where `hipDataType` and `hipblasDatatype_t` are interchangeable. In ROCm 6.2 they're separate types. The `hipblasGemmEx` function expects `hipblasDatatype_t` for ALL type arguments, including compute type.

Data type defines — cast `HIP_R_*` to `hipblasDatatype_t`:
```cpp
// Before (ROCm 7):
#define CUDA_R_16F HIP_R_16F
// After (ROCm 6.2):
#define CUDA_R_16F (hipblasDatatype_t)HIP_R_16F
```
Applied to: `CUDA_R_16F`, `CUDA_R_16BF`, `CUDA_R_32F`, `CUDA_R_8I`, `CUDA_R_32I`

Compute type defines — map to `hipblasDatatype_t` instead of `hipblasComputeType_t`:
```cpp
// Before (ROCm 7):
#define cublasComputeType_t hipblasComputeType_t
#define CUBLAS_COMPUTE_32F HIPBLAS_COMPUTE_32F
// After (ROCm 6.2):
#define cublasComputeType_t hipblasDatatype_t
#define CUBLAS_COMPUTE_32F (hipblasDatatype_t)HIPBLAS_R_32F
```
Applied to: `CUBLAS_COMPUTE_16F`, `CUBLAS_COMPUTE_32F`, `CUBLAS_COMPUTE_32I`

#### `src/cuda/helpers.h` — `__syncwarp` not in HIP

`__syncwarp(mask)` is a CUDA warp synchronization intrinsic. AMD wavefronts execute in lockstep (SIMD), so warp sync is a no-op. **Must be defined as no-op, NOT `__syncthreads()`** — using `__syncthreads()` causes a barrier race condition in `block_reduce()` that corrupts softmax. See `gpu-transcription-hang.md` for the full investigation.

```cpp
// Added inside #ifdef CT2_USE_HIP block:
#define __syncwarp(mask)  // no-op — waves are lockstep on RDNA1
```

#### `ctranslate2/__init__.py` (site-packages) — ROCm DLL path

The installed package's `__init__.py` looks for ROCm DLLs in a PyPI-bundled `_rocm_sdk_core` package. For our system install, added the ROCm bin directory to the DLL search path:

```python
os.add_dll_directory(r"C:\Program Files\AMD\ROCm\6.2\bin")
```

### 5. Build

```
cmake --build build --config Release -j
```

149 targets: C/C++ sources compiled by ROCm clang, HIP GPU kernels compiled for gfx1010. Warnings only (unused vars, deprecated getenv, loop unroll failures — all harmless).

### 6. Create Python wheel

```
cmake --install build --prefix build/install
set CTRANSLATE2_ROOT=<build>/install
cd python
pip wheel . --no-deps -w dist
```

Produces `ctranslate2-4.7.1-cp313-cp313-win_amd64.whl`.

### 7. Install

```
pip install --force-reinstall <wheel>
copy ctranslate2.dll → site-packages/ctranslate2/
```

The DLL must be in the package directory (or on PATH) for the Python extension to find it.

### 8. Test

Test script: `documentation/temp/test_rocm_transcribe.py`

```
GPU #0: AMD Radeon RX 5700 XT (CC=10.1)
Model loaded OK
Transcription OK: 'ew a the a a to with the the...'
```

Random noise input → gibberish output = correct behavior. GPU inference works.

## Problems encountered and solutions

| # | Problem | Solution |
|---|---------|----------|
| 1 | CMake can't find C compiler | ROCm clang needs MSVC linker libs; installed MSVC Build Tools |
| 2 | `cmake_minimum_required` too old for CMake 4.2 | `-DCMAKE_POLICY_VERSION_MINIMUM=3.5` |
| 3 | Intel OpenMP `libiomp5` not found | `-DOPENMP_RUNTIME=NONE` |
| 4 | "Failed to find ROCm root directory" | `-DCMAKE_HIP_COMPILER_ROCM_ROOT=<path>` |
| 5 | Spaces in `C:\Program Files\...` break CMake `-D` args | Use 8.3 short paths: `C:\PROGRA~1\AMD\ROCm\6.2` |
| 6 | Backslashes parsed as escape sequences in CMake config | Use forward slashes in all CMake `-D` values |
| 7 | MSVC 2026 headers: `__builtin_verbose_trap` unsupported | Pre-define `_MSVC_STL_DOOM_FUNCTION(mesg)=__builtin_trap()` |
| 8 | `hipDataType` vs `hipblasDatatype_t` type mismatch | Cast `HIP_R_*` values to `hipblasDatatype_t` in source |
| 9 | `hipblasComputeType_t` vs `hipblasDatatype_t` for compute arg | Map compute type defines to `hipblasDatatype_t` values |
| 10 | `__syncwarp` undeclared in HIP | Define as `__syncthreads()` (AMD waves are lockstep) |
| 11 | DLL load fails — ROCm DLLs not found at runtime | Add ROCm bin to `os.add_dll_directory()` in `__init__.py` |

## Build scripts

Three batch files in the build directory (`configure.bat`, `build.bat`, `install_and_wheel.bat`) automate the process. Each calls `vcvars64.bat` first to set up the MSVC environment.

## What we skipped (can add later)

- ~~**oneDNN/MKL** (`WITH_DNNL=OFF`)~~ **DONE (2026-02-07)**: Built oneDNN 3.1.1 from source (static, SEQ runtime), rebuilt CT2 with `WITH_DNNL=ON`. CPU int8/float32 working. See `build_onednn.bat`.
- **OpenMP** (`OPENMP_RUNTIME=NONE`): Parallel CPU operations. CPU inference works but is single-threaded. ROCm 6.2 doesn't ship libomp.dll so would need Intel OpenMP or standalone libomp.
- **MSVC v143 toolchain**: Installed but ultimately not used — the `_MSVC_STL_DOOM_FUNCTION` workaround let us use v14.50 headers directly.
