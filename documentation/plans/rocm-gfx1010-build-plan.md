# ROCm gfx1010 Build Plan (Windows)

*Goal: Get AMD RX 5700 XT GPU acceleration working with faster-whisper/CTranslate2*
*Status: GPU transcription working — built CTranslate2 from source (see `ctranslate2-rocm6-build.md`)*

## Gate Checks — ALL PASSED

### 1. PAL exposes gfx1010 for compute
- [x] PASSED — gfx1010 is in PAL's device list

### 2. HIP runtime recognizes the 5700 XT
- [x] PASSED — `hipinfo.exe` returns device count 1, sees "AMD Radeon RX 5700 XT" (gfx1010:xnack-)
- [x] Critical finding: **HIP SDK 7.1 does NOT work** (returns 0 devices). **HIP SDK 6.2 works.**
- [x] Root cause: Adrenalin driver ships ROCm 6 runtime (`amdhip64_6.dll`). SDK must match.

### 3. Verify hipBLAS/rocBLAS can be called on gfx1010
- [x] PASSED — hipblasSgemm returns correct results (2x2 matmul, A × identity = A)
- [x] Full pipeline works: HIP → hipBLAS → rocBLAS → Tensile fallback kernels → GPU

### 4. rocBLAS gfx1010 Tensile kernels
- [x] SDK 6.2 does NOT ship gfx1010 kernels (only gfx906, gfx1030, gfx1100, gfx1101, gfx1102, gfx1151)
- [x] Installed community-built kernels from likelovewant/ROCmLibs (v0.6.2.4, gfx1010-xnack-)
- [x] Source: https://github.com/likelovewant/ROCmLibs-for-gfx1103-AMD780M-APU/releases/tag/v0.6.2.4
- [x] Replaced rocblas.dll + library/ in `C:\Program Files\AMD\ROCm\6.2\bin\rocblas\`
- [x] Original rocblas.dll backed up (400MB with all archs → 200MB gfx1010 only)

## CTranslate2 Integration — DLL Shim Approach (no build needed!)

### 5. DLL shim instead of building from source
- [x] Pre-built CTranslate2 ROCm wheel (v4.7.1, built for ROCm 7) links against `amdhip64_7.dll`
- [x] ROCm 6.2 has `amdhip64_6.dll` — ABI is compatible between ROCm 6 and 7 for basic HIP operations
- [x] Copy `amdhip64_6.dll` → `amdhip64_7.dll` in the ROCm 6.2 bin directory
- [x] hipblas.dll naming already matches in 6.2 (was `libhipblas.dll` in 7.1)
- [x] CTranslate2 imports, detects GPU, reports all compute types
- [x] **SUPERSEDED:** Shim worked for loading/detection but failed during GEMM. Built CTranslate2 from source instead (see `ctranslate2-rocm6-build.md`)

### 6. Whisper-Key app integration
- [x] Added `setup_rocm_path()` in `utils.py` — scans `C:\Program Files\AMD\ROCm\` for directories with `amdhip64_6.dll`
- [x] Called early in `main.py` before any imports that load CTranslate2
- [x] Uses `os.add_dll_directory()` to register the ROCm bin path
- [x] Does NOT trust `HIP_PATH` env var (may point to incompatible 7.1)

### 7. Integration test
- [x] `ctranslate2.get_supported_compute_types('cuda')` works — reports int8, float16, float32, bfloat16 etc.
- [x] faster-whisper model loads on GPU: `WhisperModel('tiny.en', device='cuda', compute_type='float32')`
- [x] **RESOLVED:** Transcription works — built CTranslate2 from source against ROCm 6.2 targeting gfx1010

#### Confirmed
- Model loads on GPU with both float16 and float32
- Error is `CUBLAS_STATUS_INVALID_VALUE` during `model.encode()` — the first heavy GPU computation
- Both float16 and float32 fail identically — not a compute-type issue
- Fails on synthetic audio (random noise) — not a data issue
- CTranslate2 does NOT bundle its own rocBLAS — uses the system one
- `ROCBLAS_TENSILE_LIBPATH` set explicitly — did not help
- `ROCBLAS_LAYER=2` trace logging produced no output (may not be supported in this build)
- The wheel was built from mainline CTranslate2 (ROCm support merged from arlo-phoenix fork in v4.7.0, Windows fix in v4.7.1), targeting ROCm 7.1.1
- The fork hard-codes tensor core detection to `false` for AMD
- CTranslate2 has no env var to control GEMM algorithm selection

#### Root cause (resolved)
The pre-built ROCm 7 wheel failed because of one or more of these layers:
1. HIP runtime shim (`amdhip64_6.dll` → `amdhip64_7.dll`)
2. hipBLAS version mismatch (compiled against ROCm 7 headers, running ROCm 6.2)
3. Community Tensile kernels — possible GEMM shape gaps
4. Pre-compiled GPU code objects — no gfx1010 target in the wheel

Building from source against ROCm 6.2 with `CMAKE_HIP_ARCHITECTURES=gfx1010` eliminated all four layers. See `ctranslate2-rocm6-build.md` for the full build process.

## Key Findings

### gfx1010 ROCm Support Status
- **gfx1010 (RDNA 1) was never officially supported by ROCm in any version**
- Official support starts at RDNA 2 (gfx1030+)
- Community efforts make it functional: custom Tensile kernels, COMGR JIT compilation
- Some ROCm infrastructure for gfx1010 exists (e.g. `TensileLibrary_lazy_gfx1010.dat` ships in some builds) but it's not enabled in official releases

### SDK Version Compatibility
- HIP SDK 7.1 + Adrenalin driver = **0 devices detected**
- HIP SDK 6.2 + Adrenalin driver = **GPU detected and working**
- Adrenalin driver bundles ROCm 6 runtime DLLs; SDK version must match
- Note: HIP SDK 7.1 returning 0 devices could be driver/runtime mismatch OR ROCm 7 not recognizing gfx1010 — we haven't determined which

### DLL Shim — Superseded
- Renaming `amdhip64_6.dll` → `amdhip64_7.dll` let the ROCm 7 wheel **load, detect GPU, and load models**
- **However:** actual GEMM computation failed during inference
- **Resolved** by building CTranslate2 from source against ROCm 6.2 — DLL shim no longer needed

### HIP_PATH Environment Variable
- HIP SDK installer sets `HIP_PATH` to its install location
- If both 6.2 and 7.1 are installed, `HIP_PATH` may point to 7.1 (wrong one)
- Our code ignores `HIP_PATH` and scans for directories with `amdhip64_6.dll` instead

### COMGR Library
- `amd_comgr.dll` (Code Object Manager) is required for GPU initialization
- Missing from minimal HIP SDK install — need to install full SDK including "HIP Runtime Compiler"
- Without it: "no ROCm-capable device" error for ALL GPUs (misleading)

### Debugging Tools
- `AMD_LOG_LEVEL=4` on hipinfo.exe reveals exactly what's failing
- Process Monitor (procmon) shows which DLLs are being searched for
- Windows DLL error messages are misleading — "module not found" means dependency missing, not the module itself

## Setup Requirements Summary — COMPLETE

1. **HIP SDK 6.2.x** (NOT 7.x) — must match Adrenalin driver's ROCm 6 runtime
2. **Community rocBLAS** with gfx1010 Tensile kernels (from likelovewant/ROCmLibs)
   - Replace `rocblas.dll` and `library/` folder in `ROCm\6.2\bin\rocblas\`
3. **CTranslate2 built from source** against ROCm 6.2, targeting gfx1010 (see `ctranslate2-rocm6-build.md`)
4. **App code:** Call `os.add_dll_directory()` pointing to ROCm 6.2 bin before importing CTranslate2
5. ~~**DLL shim** — no longer needed with the from-source build~~

## Code Changes (branch: amd-gpu-support)

- `src/whisper_key/utils.py` — added `setup_rocm_path()` function
- `src/whisper_key/main.py` — calls `setup_rocm_path()` at startup before other imports

## Environment Info

- GPU: AMD RX 5700 XT (RDNA 1, gfx1010:xnack-, 8GB VRAM, 20 CUs, 1815 MHz)
- OS: Windows 10+
- Working SDK: HIP SDK 6.2 (`C:\Program Files\AMD\ROCm\6.2\`)
- Non-working SDK: HIP SDK 7.1 (still installed, `HIP_PATH` points here — ignored by our code)
- Driver: Adrenalin 32.0.12033.1030 (Nov 2024)
- Python: 3.13
- CTranslate2: 4.7.1 (built from source against ROCm 6.2, targeting gfx1010 — see `ctranslate2-rocm6-build.md`)
- Community rocBLAS: likelovewant/ROCmLibs v0.6.2.4

## Files

- This plan: `documentation/plans/rocm-gfx1010-build-plan.md`
- ROCm build explainer: `documentation/research/rocm-build-explainer.html`
- GPU stack explainer: `documentation/research/gpu-stack-explainer.html`
- CTranslate2 ROCm research: `documentation/research/ctranslate2-rocm-support.md`
- Testing risk assessment: `documentation/temp/gfx1010-testing-risk-assessment.md`
- Sherpa-ONNX DirectML research: `documentation/temp/sherpa-onnx-directml-research.md`
- AMD GPU progress notes: `documentation/temp/amd-gpu-support-progress.md`
