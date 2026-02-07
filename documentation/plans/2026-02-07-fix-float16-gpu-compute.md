# Fix float16 GPU Compute Type — COMPLETE

As a *user* I want **float16 transcription on AMD GPU** so I get ~2x speedup and half the VRAM usage.

## Background

Float16 compute type failed with `HIPBLAS_STATUS_UNKNOWN`. Root cause: the legacy `hipblasGemmEx` (v1) uses `hipblasDatatype_t` for compute type. The v2 API (`hipblasGemmEx_v2`) uses `hipblasComputeType_t` — a different enum with different values. The v2 functions exist in SDK 6.2 but only activate behind `#ifdef HIPBLAS_V2`.

Our original patch mapped to v1 types, but the v1 API silently accepted wrong values and failed at runtime.

## What was done

1. Switched all GemmEx calls to v2 API (`hipblasGemmEx_v2`, `hipblasGemmStridedBatchedEx_v2`)
2. Changed compute type mappings to `hipblasComputeType_t` (`HIPBLAS_COMPUTE_16F`, etc.)
3. Changed data type mappings to `hipDataType` (`HIP_R_16F`, etc.)
4. Rebuilt wheel and published as [GitHub release](https://github.com/PinW/ctranslate2-rocm-rdna1/releases/tag/v4.7.1-rocm62-gfx1010)

## Result

- [x] GPU float16 transcription working
- [x] GPU float32 no regression
- [x] Wheel rebuilt and published
