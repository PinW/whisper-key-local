# GPU Transcription Hang — Investigation

*Status: **RESOLVED** (2026-02-07)*

## ROOT CAUSE: `__syncwarp(mask) → __syncthreads()` mapping in `helpers.h`

The HIP compatibility patch `#define __syncwarp(mask) __syncthreads()` caused a **barrier synchronization race condition** in `block_reduce()` (helpers.h line 436). When block size > 32 (multi-warp), threads at the `__syncwarp` call and threads at the subsequent `__syncthreads` contributed to the **same hardware barrier counter**, causing 496 threads to be released before thread 0 wrote the final reduced value. This corrupted softmax's max and sum reductions, producing garbage attention weights.

**Fix:** `#define __syncwarp(mask)` (no-op — waves execute in lockstep on gfx1010/RDNA1)

**Result:** Full Whisper transcription working on AMD RX 5700 XT. Encoder corr=1.000000 vs CPU reference.

---

## Original Problem

CTranslate2 built from source for ROCm 6.2 / gfx1010 loaded models and ran GPU inference without errors, but the **encoder output was completely wrong** (zero correlation with CPU reference). The decoder then looped endlessly trying to make sense of garbage encoder features.

## How the bug was found

### 1. Pipeline bisection → self-attention is broken
Through systematic bisection testing, the bug was isolated to the **self-attention mechanism** within the transformer layer. Every individual GPU operation passed in isolation.

### 2. Full standalone attention chain → ALL PASS (2026-02-07)
Compiled and ran `test_full_attention.hip` — a complete 9-step attention pipeline (QKV GEMM, split_heads, Q@K^T, softmax, attn@V, combine_heads, output projection, residual) at full Whisper shapes (T=1500). **All 3 test modes passed with corr=1.000000.** This proved the bug was in CT2's runtime, not the GPU operations.

### 3. Identified `__syncwarp → __syncthreads()` race condition
Analyzed `block_reduce()` in `helpers.h`. The `#define __syncwarp(mask) __syncthreads()` patch caused a barrier synchronization race: GPU's `s_barrier` is a shared counting barrier that doesn't distinguish between different code locations. When 16 threads called `__syncthreads()` at the `__syncwarp` site and 496 threads called `__syncthreads()` at the subsequent barrier, the hardware counted 512 total arrivals and released all threads — before the first-warp threads had written reduced values to shared memory.

### 4. Fix applied and verified
Changed `#define __syncwarp(mask) __syncthreads()` to `#define __syncwarp(mask)` (no-op). Rebuilt CT2, verified:
- Zero-QKV test: corr=0.169 → **1.000000**
- Self-attention isolation: corr=0.133 → **1.000000**
- Full encoder vs CPU: corr=1.000000, max_diff=0.0010
- End-to-end transcription: **"Hello, this is me, Pinnell. What is up?"** ✓

### Pipeline bisection results (2026-02-06)

| Component | GPU Status | Test Method | Correlation |
|-----------|-----------|-------------|-------------|
| Conv1d + GELU (both layers) | **CORRECT** | Zero-layer model vs numpy | 1.000000 |
| Transpose [B,C,T]→[B,T,C] | **CORRECT** | Same test | 1.000000 |
| Position embedding add | **CORRECT** | Same test | 1.000000 |
| Layer norm | **CORRECT** | Same test | 1.000000 |
| FFN (linear + GELU + linear) | **CORRECT** | Zero-attn model vs numpy | 0.999999 |
| **Self-attention** | **BROKEN** | Zero-FFN model vs numpy | **0.133** |
| **Full 1-layer encoder** | **BROKEN** | 1-layer model vs numpy/CPU | **0.107** |

### Individual operation standalone tests (ALL PASS)

| Operation | Test Method | Result |
|-----------|-------------|--------|
| hipblasSgemm | ctypes, 10 exact Whisper shapes | ALL PASS |
| hipblasSgemmStridedBatched | ctypes, exact attention shapes (Q@K^T and attn@V) | ALL PASS, 6/6 |
| transpose_0213 kernel (uint4 path) | Compiled HIP kernel, exact Whisper shapes | ALL PASS, 0 mismatches |
| transpose_0213 kernel (float path) | Same HIP kernel | ALL PASS, 0 mismatches |
| uint4 vs float transpose | Compared both paths | EXACT MATCH |
| hipcub::BlockReduce | Standalone HIP kernel | 8/8 PASS |
| Custom block_reduce (softmax) | Standalone HIP kernel | sum+max PASS |
| CPU↔GPU transfer | StorageView roundtrip | Perfect match |

### Weight format is NOT the issue

| Test | Result |
|------|--------|
| Float16 weights (original) | corr=-0.095 (broken) |
| Float32 weights (converted) | Same output as float16 (still broken) |
| Identity attention weights (Q=K=V=input) | corr=0.234 (ALSO broken) |
| Zeroed transformer weights | corr=1.000 (correct — attention not exercised) |

**Conclusion: Bug is structural, not weight-dependent.**

## The paradox

Every operation works correctly when tested standalone with hipcc/ctypes — including their compositions on a single stream — but the self-attention COMPOSITION fails within CTranslate2. This definitively points to the CT2 build or runtime environment, not the GPU operations themselves.

### Operation chain tests (2026-02-06, test_chain_stream.hip)

All 5 tests pass at full Whisper shapes (time=1500), zero mismatches, perfect correlation:

| Test | What it tests | Result |
|------|--------------|--------|
| A: thrust::gather + inner_dim_offset_map + uint4 + par_nosync | Standalone split kernel | **PASS** (0 mismatches) |
| A2: Same with thrust::hip::par (synchronizing) | Sync vs nosync policy | **PASS** (identical to A) |
| B: transpose→split chain, same stream, no sync | Stream ordering (kernel→thrust) | **PASS** (0 mismatches) |
| C: GEMM→transpose→split chain, same stream, no sync | Stream ordering (hipBLAS→kernel→thrust) | **PASS** (max_diff ~2.8e-6) |
| D: Same chain with hipDeviceSynchronize between ops | Explicit sync vs stream ordering | **PASS** (identical to C) |

**Conclusion: All individual ops AND their compositions pass standalone. Bug is definitively in CT2 build/runtime, not GPU ops.**

### Compilation flags comparison (2026-02-06)

From CT2's build.ninja: `-O3 -DNDEBUG -DCT2_USE_HIP -DCT2_WITH_CUDA -std=gnu++17 --offload-arch=gfx1010:xnack-`

Recompiled standalone chain test with `-O3 -DNDEBUG -std=gnu++17` — still ALL PASS. Difference is NOT in compiler flags alone.

### HIP_LAUNCH_BLOCKING=1 test (2026-02-06)

Ran `test_isolate_sa_ffn.py` with `HIP_LAUNCH_BLOCKING=1` (forces every kernel launch to be synchronous — no overlap, no out-of-order execution).

**Result: STILL BROKEN (corr=0.133)**

This ELIMINATES:
- Stream ordering as a suspect (all kernels forced synchronous)
- cub_caching allocator races (no concurrent kernels means no races)
- The compiled kernels themselves produce wrong output, regardless of execution order

### Zero QKV weight test (2026-02-06, test_zero_qkv_weight.py)

Created model with QKV weight=0 (bias only), FFN weights=0. This makes Q=K=V=constant at every position, so attention should be trivial (uniform softmax weights, output = mean of V = constant).

| Metric | Expected | GPU Actual |
|--------|----------|------------|
| Correlation | ~1.0 | **0.169** |
| Max difference | ~0 | **11.37** |
| Output magnitudes | ~residual | **~10x too large** |
| Variance across time | ~2.0 (from residual) | **0.0007** |

**EVEN TRIVIAL ATTENTION IS BROKEN.** Bug is in a basic operation: split_heads, softmax, combine_heads, or output projection.

## Self-attention data flow in CTranslate2

```
Input [1, 1500, 384]
  → Linear (GEMM): input × QKV_weight^T → [1, 1500, 1152]
  → split_heads: reshape [1, 1500, 18, 64] → transpose_0213 → [1, 18, 1500, 64]
  → Split(axis=1): thrust::gather → Q[1,6,1500,64], K[1,6,1500,64], V[1,6,1500,64]
  → Q @ K^T: hipblasSgemmStridedBatched (6 batches) → [1, 6, 1500, 1500]
  → SoftMax → [1, 6, 1500, 1500]
  → attn @ V: hipblasSgemmStridedBatched → [1, 6, 1500, 64]
  → combine_heads: transpose_0213 → [1, 1500, 6, 64] → reshape [1, 1500, 384]
  → Linear (GEMM): output projection
  → Residual add
```

Key source: `CTranslate2/src/layers/attention.cc` lines 423-633

## What's been eliminated

| Suspect | Status | How tested |
|---------|--------|------------|
| rocBLAS SGEMM kernels | **Eliminated** | 10/10 exact Whisper shapes pass via ctypes |
| rocBLAS SgemmStridedBatched | **Eliminated** | 6/6 exact attention shapes pass via ctypes |
| transpose_0213 kernel (uint4) | **Eliminated** | Standalone HIP kernel, 1.7M+ elements, 0 mismatches |
| transpose_0213 kernel (float) | **Eliminated** | Same, both paths produce identical output |
| hipcub::BlockReduce | **Eliminated** | Standalone HIP kernel, 8/8 pass |
| Custom block_reduce | **Eliminated** | Standalone HIP kernel, sum+max pass |
| Warp size mismatch | **Eliminated** | Hardware reports 32, code uses 32 |
| CPU↔GPU transfer | **Eliminated** | Perfect roundtrip, deterministic |
| Float16→float32 weight conversion | **Eliminated** | Float32 model produces same wrong output |
| Weight values / magnitudes | **Eliminated** | Identity weights also produce wrong output |
| Conv1d im2col kernel | **Eliminated** | Zero-layer model matches numpy exactly |
| HSA_OVERRIDE_GFX_VERSION | **Not viable** | Windows unsupported, Linux broken for gfx1010 |
| index_t overflow (uint32) | **Eliminated** | All values fit in 32-bit for Whisper tiny |
| thrust::gather + inner_dim_offset_map + uint4 | **Eliminated** | Standalone HIP test, 0 mismatches at full shapes |
| par_nosync execution policy | **Eliminated** | par_nosync and par produce identical results |
| Stream ordering (kernel→thrust) | **Eliminated** | transpose→split chain, same stream, no sync, 0 mismatches |
| Stream ordering (hipBLAS→kernel→thrust) | **Eliminated** | GEMM→transpose→split chain, same stream, no sync, PASS |
| Stream ordering (ALL configurations) | **Eliminated** | HIP_LAUNCH_BLOCKING=1 still broken (corr=0.133) |
| cub_caching allocator races | **Eliminated** | HIP_LAUNCH_BLOCKING=1 serializes everything, still broken |
| Compiler optimization level (-O3) | **Eliminated** | Standalone test with -O3 -DNDEBUG still passes |
| Compiler flags alone | **Eliminated** | Matching CT2's flags in standalone test, still passes |

## Remaining suspects (priority order)

1. **CT2's compiled kernel code differs from standalone** — The SAME source code may compile to DIFFERENT machine code in CT2's build context. CT2 builds through CMake with `-DCT2_USE_HIP -DCT2_WITH_CUDA`, MSVC STL includes, and Thrust from CT2's include chain. Template instantiation context, include chain, and surrounding code structure may all affect codegen. Even though compiler FLAGS match, the compilation CONTEXT differs.

2. **CT2 passes wrong parameters to kernels** — StorageView shape/stride miscalculation could cause correct kernels to receive wrong dimensions, offsets, or pointers. The zero-QKV test showing ~10x magnitudes and near-zero variance suggests data is being read from wrong locations or with wrong strides.

3. **Model weight loading issue** — Weights might not reach GPU correctly despite the model file being correct. Could be a deserialization or upload path issue specific to multi-head attention weights.

## Recommended next steps

1. **Write FULL standalone attention chain test** — The first half (GEMM→transpose→split) passes. Need to test the second half: Q@K^T (strided batched GEMM with scale=1/sqrt(64)), softmax (CT2's cunn_SoftMaxForward kernel with ILP=2, block_reduce), attn@V (strided batched GEMM), combine_heads (transpose_0213 + reshape). Use exact CT2 stride calculations from matmul.cc. If this passes, bug is definitively in CT2 parameter passing.

2. **If full chain passes: add tensor dumps to CT2 attention.cc** — Insert `hipMemcpy` + file writes at key points in `dot_product_attention()` (after Q@K^T at ~line 200, after softmax at ~line 217, after attn@V at ~line 222). This is ~20 lines of code, fast incremental rebuild. Compare GPU intermediate tensors to numpy reference.

3. **Alternative: Python-level intermediate extraction** — Use `StorageView.__cuda_array_interface__` + hipMemcpy to extract encoder output at each layer boundary. Won't see inside attention, but can confirm layer-level divergence.

4. **Try community rocBLAS v6.4.2** — newer release available at likelovewant/ROCmLibs-for-gfx1103-AMD780M-APU (v0.6.2.4 → v6.4.2, released 2025)

## CTranslate2 patches applied (3 files)

1. **`src/cuda/primitives.cu` lines 3-26** — HIP type mappings (only affects fp16/int8 GemmEx, not float32 Sgemm)
2. **`src/cuda/helpers.h` line 12** — `#define __syncwarp(mask) __syncthreads()`
3. **`ctranslate2/__init__.py`** — ROCm DLL path setup (runtime only)

## Key source files for the bug

- `CTranslate2/src/layers/attention.cc` — self-attention: split_heads (line 586), combine_heads (line 611), dot_product_attention (line 178)
- `CTranslate2/src/cuda/primitives.cu` — transpose_0213 kernel (line 424), transpose_4d dispatch (line 447), gemm_batch_strided float32 (line 599)
- `CTranslate2/src/ops/concat_split_slide_gpu.cu` — Split::compute with thrust::gather and uint4 (line 116)
- `CTranslate2/src/ops/matmul.cc` — batched GEMM stride computation (line 62)
- `CTranslate2/src/ops/softmax_gpu.cu` — cunn_SoftMaxForward kernel, launched as 1-block-per-row with ILP=2
- `CTranslate2/src/cuda/helpers.h` — `index_t = unsigned int` (line 39), block_reduce (line 412), ilp_reduce (line 461), get_block_size (line 401)

### CT2 attention stride calculations (from matmul.cc)

For Q@K^T (`MatMul(trans_a=false, trans_b=true, scale=1/sqrt(d_k))`):
- Q shape [batch*heads, time, d_k] → m=time, k=d_k, n=time
- lda=d_k, ldb=d_k, ldc=time, stridea=time*d_k, strideb=time*d_k, stridec=time*time
- cuBLAS row→col swap: calls `hipblasSgemmStridedBatched(OP_T, OP_N, n=time, m=time, k=d_k, ...b, ldb, strideb, a, lda, stridea, ...c, ldc, stridec, batch=batch*heads)`

For attn@V (`MatMul()`, no transpose, alpha=1):
- attn shape [batch*heads, time, time], V shape [batch*heads, time, d_v] → m=time, k=time, n=d_v
- lda=time, ldb=d_v, ldc=d_v, stridea=time*time, strideb=time*d_v, stridec=time*d_v

## Test files created

| File | Purpose |
|------|---------|
| `dist/test_bisect_encoder.py` | Pipeline bisection: 0-layer, 1-layer truncated models |
| `dist/test_numpy_1layer.py` | Full 1-layer encoder in numpy (matches CPU: corr=0.999998) |
| `dist/test_zero_layer.py` | Zero transformer weights → tests conv pipeline only |
| `dist/test_isolate_sa_ffn.py` | Zero SA vs zero FFN → isolated self-attention as broken |
| `dist/test_strided_batched_gemm.py` | hipblasSgemmStridedBatched via ctypes (6/6 PASS) |
| `dist/test_transpose_0213.hip` | Standalone HIP kernel replicating transpose_0213 (ALL PASS) |
| `dist/test_identity_attention.py` | Identity attention weights → confirms structural bug |
| `dist/test_f32_weights.py` | Float32 weights → confirms not a precision issue |
| `dist/test_cpu_1layer.py` | CPU reference for 1-layer model (stock ctranslate2) |
| `dist/test_sgemm_direct.py` | Direct hipblasSgemm via ctypes (all PASS) |
| `dist/test_exact_shapes.py` | 10 exact Whisper GEMM shapes (all PASS) |
| `dist/test_blockredu.hip` | Standalone HIP kernel testing BlockReduce (all PASS) |
| `dist/test_transfer.py` | CPU↔GPU StorageView transfer + determinism (all PASS) |
| `dist/test_chain_stream.hip` | 5-test chain: GEMM→transpose→split + variants (ALL PASS) |
| `dist/test_zero_qkv_weight.py` | Trivial attention test: QKV weight=0 (GPU BROKEN, corr=0.169) |
| `dist/test_full_attention.hip` | Full 9-step attention chain: QKV GEMM+bias, split_heads, split, Q@K^T, softmax, attn@V, combine_heads, output proj, residual. 3 test modes (no-sync, sync, step-by-step). Supports `bias` mode for zero-QKV. **NOT YET RUN.** |

## Useful techniques discovered

- `StorageView.__cuda_array_interface__` provides GPU pointer for hipMemcpy extraction
- `sv_to_numpy()` via hipMemcpy from `__cuda_array_interface__['data'][0]`
- Model binary format: version 4+ has null-terminated strings, type_id byte, num_bytes uint32
- Custom build has NO CPU SGEMM backend (WITH_MKL=OFF, WITH_DNNL=OFF, WITH_OPENBLAS=OFF)

## Community rocBLAS

- Current: likelovewant/ROCmLibs v0.6.2.4
- **Newer available: v6.4.2 (2025)** at https://github.com/likelovewant/ROCmLibs-for-gfx1103-AMD780M-APU/releases
- Mixed xnack-/non-xnack install (80 gfx1010 files) — works correctly for individual SGEMM but untested for edge cases

## Environment

- GPU: AMD RX 5700 XT (gfx1010, RDNA 1, warpSize=32)
- CTranslate2: 4.7.1 (built from source, ROCm 6.2, gfx1010)
- HIP SDK: 6.2, Clang 19.0.0
- Community rocBLAS: likelovewant/ROCmLibs v0.6.2.4
- Python: 3.13, faster-whisper, device=cuda, compute_type=float32
- MSVC Build Tools 2026 (v14.50) — requires `__builtin_verbose_trap` workaround
- Build project: `C:\Users\pinwa\projects\5700xt-rocm\`
- CTranslate2 source: `C:\Users\pinwa\projects\5700xt-rocm\CTranslate2\`
- Build repo: https://github.com/PinW/ctranslate2-rocm-rdna1
- CPU reference venv: `C:\Users\pinwa\projects\5700xt-rocm\temp_cpu_venv\`
