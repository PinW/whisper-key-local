# Restore CPU Support in Custom CTranslate2 Build

As a *user* I want **CPU/INT8 inference to work in the custom ROCm build** so the same wheel works for both GPU and CPU users.

## Background

The custom CTranslate2 build (ROCm 6.2, gfx1010) was built GPU-only to simplify initial testing:

```
-DWITH_MKL=OFF -DWITH_DNNL=OFF -DOPENMP_RUNTIME=NONE
```

This means CPU inference fails with `"No SGEMM backend on CPU"`. The stock PyPI wheel uses **oneDNN (DNNL)** for CPU GEMM — including INT8 quantized inference — and bundles Intel OpenMP (`libiomp5md.dll`) for multi-threaded CPU execution.

**Goal:** Add DNNL to the existing ROCm build so cpu/int8 works, matching the stock wheel's CPU behavior.

**Non-goal:** Optimal multi-threaded CPU performance (OpenMP is a stretch goal).

## Key Findings

| Fact | Detail |
|------|--------|
| Stock wheel CPU backend | **DNNL (oneDNN 3.1.1)**, statically linked |
| Stock wheel OpenMP | Intel `libiomp5md.dll` (OPENMP_RUNTIME=INTEL) |
| DNNL primitives CT2 uses | BLAS-like API: `dnnl_sgemm`, `dnnl_gemm_u8s8s32`, `dnnl_gemm_s8s8s32`; Primitive API: `dnnl::convolution_forward`, `dnnl::reorder` |
| Stock oneDNN build flags | `ONEDNN_ENABLE_PRIMITIVE="CONVOLUTION;REORDER"` — sufficient for CT2 |
| ROCm 6.2 ships libomp.dll? | **No** — `OPENMP_RUNTIME=COMP` won't work without extra install |

## Implementation Plan

### Phase 1: Build oneDNN from source (Windows, MSVC) — DONE

- [x] Download oneDNN 3.1.1 source: `https://github.com/oneapi-src/oneDNN/archive/refs/tags/v3.1.1.tar.gz`
- [x] Extract to `C:\Users\pinwa\projects\5700xt-rocm\oneDNN-3.1.1\`
- [x] Create `build_onednn.bat` in the 5700xt-rocm directory
- [x] Build as static library with SEQ runtime (no OpenMP dependency)
- [x] Verify install produces `include/dnnl.h` and `lib/dnnl.lib`

Note: required `CMAKE_POLICY_VERSION_MINIMUM=3.5` (same CMake 4.2 compat issue as CT2). 391 targets built with MSVC.

### Phase 2: Modify CTranslate2 build configuration — DONE

- [x] Update `configure.bat`: change `-DWITH_DNNL=OFF` to `-DWITH_DNNL=ON`
- [x] Update `configure.bat`: add oneDNN install path to `CMAKE_PREFIX_PATH`
- [x] Keep `OPENMP_RUNTIME=NONE` (no OpenMP for Phase 1)
- [x] Run `configure.bat` — verify cmake finds DNNL headers and library

### Phase 3: Rebuild, wheel, install — DONE

- [x] Run `build.bat` (full rebuild — 149 targets)
- [x] Run `install_and_wheel.bat` to create new wheel
- [x] Install wheel: `pip install --force-reinstall <wheel>`
- [x] Copy `ctranslate2.dll` to site-packages

### Phase 4: Test — DONE

- [x] Verify GPU still works: `device='cuda', compute_type='float32'` — "Hello, this is me, panel. What is up?" (0.1s)
- [x] Verify CPU INT8 works: `device='cpu', compute_type='int8'` — "Hello, this is me, panel. What is up?" (0.1s)
- [x] Confirmed working in whisper-key app
- [ ] ~~Compare CPU INT8 output with stock PyPI wheel output~~ (skipped — output matches expected)
- [ ] ~~Test model switch (gpu → cpu → gpu)~~ (not tested yet)

### Phase 5 (stretch): Add OpenMP for multi-threaded CPU

- [ ] Investigate: download standalone Intel OpenMP runtime (conda/NuGet/standalone)
- [ ] Rebuild oneDNN with OMP runtime instead of SEQ
- [ ] Rebuild CT2 with `OPENMP_RUNTIME=INTEL` and path to `libiomp5md.lib`
- [ ] Bundle `libiomp5md.dll` in wheel
- [ ] Benchmark CPU INT8 speed: single-threaded (SEQ) vs multi-threaded (OMP)

## Implementation Details

### `build_onednn.bat`

```bat
@echo off
call "C:\Program Files (x86)\Microsoft Visual Studio\18\BuildTools\VC\Auxiliary\Build\vcvars64.bat" >nul 2>&1

cd /d %~dp0oneDNN-3.1.1

cmake -GNinja -DCMAKE_BUILD_TYPE=Release ^
  -DONEDNN_LIBRARY_TYPE=STATIC ^
  -DONEDNN_BUILD_EXAMPLES=OFF ^
  -DONEDNN_BUILD_TESTS=OFF ^
  -DONEDNN_ENABLE_WORKLOAD=INFERENCE ^
  -DONEDNN_ENABLE_PRIMITIVE="CONVOLUTION;REORDER" ^
  -DONEDNN_BUILD_GRAPH=OFF ^
  -DDNNL_CPU_RUNTIME=SEQ ^
  -DCMAKE_INSTALL_PREFIX=%~dp0onednn-install ^
  -S . -B build

cmake --build build --config Release -j
cmake --install build
```

Key flags:
- `DNNL_CPU_RUNTIME=SEQ` — no OpenMP, avoids cross-compiler linking issues between MSVC (oneDNN) and ROCm clang (CT2)
- `ONEDNN_LIBRARY_TYPE=STATIC` — linked into ctranslate2.dll, no extra DLL to ship
- `ONEDNN_ENABLE_PRIMITIVE="CONVOLUTION;REORDER"` — matches stock build, sufficient for CT2

### Updated `configure.bat` (changes in bold)

```bat
@echo off
call "C:\Program Files (x86)\Microsoft Visual Studio\18\BuildTools\VC\Auxiliary\Build\vcvars64.bat" >nul 2>&1

set ROCM=C:\PROGRA~1\AMD\ROCm\6.2
set ROCM_PATH=%ROCM%
set HIP_PATH=%ROCM%
set HIP_PLATFORM=amd
set HIP_DEVICE_LIB_PATH=%ROCM%\amdgcn\bitcode
set CC=%ROCM%\bin\clang.exe
set CXX=%ROCM%\bin\clang++.exe
set PATH=%ROCM%\bin;%PATH%

cd /d %~dp0CTranslate2
rmdir /s /q build 2>nul

cmake -GNinja -DCMAKE_BUILD_TYPE=Release -DCMAKE_POLICY_VERSION_MINIMUM=3.5 ^
  -S . -B build ^
  -DBUILD_CLI=OFF ^
  -DWITH_MKL=OFF ^
  -DWITH_DNNL=ON ^
  -DOPENMP_RUNTIME=NONE ^
  -DWITH_HIP=ON ^
  -DCMAKE_HIP_ARCHITECTURES=gfx1010 ^
  -DCMAKE_HIP_COMPILER=C:/PROGRA~1/AMD/ROCm/6.2/bin/clang++.exe ^
  -DCMAKE_HIP_COMPILER_ROCM_ROOT=C:/PROGRA~1/AMD/ROCm/6.2 ^
  -DCMAKE_PREFIX_PATH="C:/PROGRA~1/AMD/ROCm/6.2;%~dp0onednn-install" ^
  "-DCMAKE_HIP_FLAGS=-D_MSVC_STL_DOOM_FUNCTION(mesg)=__builtin_trap()" ^
  "-DCMAKE_CXX_FLAGS=-D_MSVC_STL_DOOM_FUNCTION(mesg)=__builtin_trap()"
```

Changes from current:
1. `-DWITH_DNNL=OFF` → `-DWITH_DNNL=ON`
2. `CMAKE_PREFIX_PATH` now includes `onednn-install` path alongside ROCm

### Scope

| File | Action |
|------|--------|
| `C:\...\5700xt-rocm\build_onednn.bat` | **New** — oneDNN build script |
| `C:\...\5700xt-rocm\configure.bat` | **Modified** — add DNNL, update PREFIX_PATH |
| `C:\...\5700xt-rocm\build.bat` | Unchanged |
| `C:\...\5700xt-rocm\install_and_wheel.bat` | Unchanged |
| No whisper-key source changes | DLL search path already handles ROCm; oneDNN is statically linked |

## Risks

| Risk | Mitigation |
|------|------------|
| MSVC-compiled oneDNN static lib incompatible with ROCm clang linker | Both target MSVC ABI (COFF format). If fails: build oneDNN as shared DLL instead, or build with ROCm clang |
| `DNNL_CPU_RUNTIME=SEQ` makes CPU notably slower than stock wheel | Functional but single-threaded. Phase 5 adds OpenMP. Users needing fast CPU can use stock PyPI wheel |
| oneDNN 3.1.1 build fails with MSVC 2026 (v14.50) | Same `_MSVC_STL_DOOM_FUNCTION` issue as CT2 — add same workaround to oneDNN cmake flags if needed |
| `ONEDNN_ENABLE_PRIMITIVE="CONVOLUTION;REORDER"` not sufficient | CT2 uses BLAS-like GEMM API (works regardless of primitives) + CONVOLUTION + REORDER. Should be fine. If not: use `ONEDNN_ENABLE_PRIMITIVE=ALL` |

## Success Criteria

- [x] `ctranslate2.get_supported_compute_types('cpu')` includes `int8` — returns `{int8, int8_float32, float32}`
- [x] CPU/INT8 transcription produces correct text
- [x] GPU transcription still works (no regression)
- [x] No new DLLs needed at runtime (oneDNN is statically linked)

## Status

**Phases 1–4 complete (2026-02-07).** Phase 5 (OpenMP) deferred.
