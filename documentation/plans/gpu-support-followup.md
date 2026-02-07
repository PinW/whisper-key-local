# GPU Support — Follow-up Tasks

Status: OPEN

## 1. ~~Restore CPU support in custom CTranslate2 build~~ DONE (2026-02-07)

Built oneDNN 3.1.1 from source (static, SEQ runtime) and rebuilt CTranslate2 with `WITH_DNNL=ON`. CPU now supports int8, int8_float32, and float32. Both CPU INT8 and GPU float32 transcription verified working.

Build changes: `configure.bat` updated (`WITH_DNNL=ON`, oneDNN added to `CMAKE_PREFIX_PATH`). New `build_onednn.bat` for oneDNN build. oneDNN installed to `C:\Users\pinwa\projects\5700xt-rocm\onednn-install\`.

OpenMP not yet added (CPU inference is single-threaded). See plan: `2026-02-07-restore-cpu-support-implementation.md` Phase 5.

## 2. Fix float16 not working on setup

Float16 compute type fails during GPU setup/inference. Needs investigation — may be a rocBLAS Tensile kernel gap for gfx1010 half-precision GEMM, or a type mapping issue in the CTranslate2 HIP patches.

Error: `2026-02-07 10:20:16,249 - src.whisper_key.whisper_engine - ERROR - Transcription failed: cuBLAS failed with status UNKNOWN`

## 3. GPU setup documentation

Create a doc linked from both the whisper-key README and config comments explaining GPU setup for each vendor:

- **NVIDIA (CUDA)**: which CUDA toolkit version is needed, how to verify with `nvidia-smi`, supported GPU generations
- **AMD RDNA 2+ (ROCm 7)**: use the official CTranslate2 ROCm wheel from GitHub releases, HIP SDK version requirements
- **AMD RDNA 1 (ROCm 6.2)**: link to [ctranslate2-rocm-rdna1](https://github.com/PinW/ctranslate2-rocm-rdna1), explain HIP SDK 6.2 + community rocBLAS prerequisites
- **CPU fallback**: what to expect performance-wise, no extra setup needed

This doc should be the single source of truth for "how do I get GPU acceleration working."

## 4. Auto-detection for GPU onboarding

Make whisper-key detect the user's GPU and guide them to the right setup:

- Detect NVIDIA GPUs (check for CUDA availability via ctranslate2 or torch)
- Detect AMD GPUs (check for HIP/ROCm availability, identify architecture — gfx1010 vs gfx1030+)
- If no GPU detected, fall back to CPU gracefully
- Surface clear messages in the UI/logs: "Detected AMD RX 5700 XT (RDNA 1) — using GPU acceleration" or "No supported GPU found — using CPU mode"
- Link to the setup doc (task 2) when GPU is detected but drivers/SDK are missing

## 5. Fix crash on model switch in CUDA mode

Switching models while in GPU mode causes an access violation (`0xC0000005`) in `ctranslate2.dll` during `StorageView` destructor. The crash happens when the old model is being torn down — specifically in `Model::~Model()` clearing a list of `shared_ptr<StorageView>` pairs. The GPU memory backing those tensors has likely already been freed or the HIP context is invalid by the time the destructor runs.

Stack trace (key frames):
```
StorageView::~StorageView() + 0x2F
list<pair<string, shared_ptr<StorageView>>>::clear() + 0x64
Model::~Model() + 0x5B
make_shared<WhisperModel>() + 0x217  (new model being created while old destroys)
Worker::run() + 0xAB
```

Likely cause: the old model's GPU tensors are freed after the HIP context or device state has changed (e.g. new model allocation triggers cleanup). Need to ensure the old model is fully destroyed before creating the new one, or that GPU resource cleanup happens in the correct order.
