# RX 5700 XT (RDNA 1 / gfx1010) ROCm Options for Whisper

*Research Date: 2026-02-05*

## Executive Summary

The AMD RX 5700 XT uses RDNA 1 architecture (gfx1010) which is **not officially supported** by AMD's ROCm. While community workarounds exist, they require significant effort and have known instability issues. For practical Whisper acceleration, **whisper.cpp with Vulkan or HIPBLAS** offers the most realistic path, though CPU-based faster-whisper remains a reliable fallback.

---

## NEW: ROCm 6.1+ Native Support Investigation (2026-02)

### The Claim: "gfx1010 Should Just Work After ROCm 6.1"

A [Reddit post](https://www.reddit.com/r/ROCm/comments/1bd8vde/psa_rdna1_gfx1010gfx101_gpus_should_start_working/) and [GitHub issue comment](https://github.com/ROCm/Tensile/issues/1757) claimed that RDNA1 GPUs would work natively in ROCm 6.1+ without `HSA_OVERRIDE_GFX_VERSION`.

### What Actually Happened

#### Tensile Issue #1757 and PR #1897

**The Problem:** Tensile (AMD's GEMM library generator for rocBLAS) wouldn't produce backend libraries for GPU architectures lacking optimized logic files when using `--separate-architectures`. Even though gfx1010 was "enabled by default in rocBLAS builds since ROCm 4.3.0", no library was actually produced because Navi10 lacked optimized logic files.

**The Fix:** [PR #1897](https://github.com/ROCm/Tensile/pull/1897) (merged March 6, 2024) enabled architectures without optimized logic files to produce libraries using **fallback kernels**. This was cherry-picked into ROCm 6.1 release branch.

**Timeline:**
- Issue #1757 opened: August 17, 2023
- Issue closed: January 24, 2024
- PR #1897 merged: March 6, 2024
- Cherry-picked to ROCm 6.1: ~April 2024

#### Current State in rocBLAS 6.4+

Arch Linux's [rocblas 6.4.4](https://archlinux.org/packages/extra/x86_64/rocblas/files/) package now includes fallback TensileLibrary files for gfx1010:
- `TensileLibrary_fallback_gfx1010.dat`
- Multiple `*_fallback_gfx1010.hsaco` files

This means **rocBLAS itself does have gfx1010 support** via fallback kernels in ROCm 6.1+.

### Why It Still Doesn't "Just Work"

Despite the Tensile fix, several issues remain:

| Issue | Impact |
|-------|--------|
| **Not officially supported** | gfx1010 is NOT in AMD's [ROCm 7.2.0 compatibility matrix](https://rocm.docs.amd.com/en/latest/compatibility/compatibility-matrix.html) |
| **PyTorch segfaults** | Pre-built PyTorch ROCm wheels still crash on gfx1010 |
| **Fallback = slower** | Fallback kernels have [performance regressions](https://github.com/ROCm/ROCm/discussions/4030) vs optimized kernels |
| **Math library gaps** | Only rocBLAS/rocSOLVER fully support gfx1010; other libraries (MIOpen, etc.) may not |
| **No flash attention** | Triton has no RDNA1 support |

### Practical Testing Results (Community Reports)

| Configuration | Result |
|--------------|--------|
| ROCm 6.2 + PyTorch (source build) | Works with `PYTORCH_ROCM_ARCH=gfx1010` |
| ROCm 6.4.1 + Ollama | Partial success with `HSA_OVERRIDE_GFX_VERSION=10.1.0` |
| ROCm 6.4.3 + Ollama | SIGSEGV crashes reported |
| Pre-built PyTorch wheels | Still broken |

### Verdict: The Claim is Partially True

**What's true:**
- Tensile/rocBLAS now produces fallback libraries for gfx1010 in ROCm 6.1+
- The underlying infrastructure for gfx1010 support exists

**What's still false:**
- gfx1010 is NOT officially supported (not in compatibility matrix)
- Pre-built binaries (PyTorch wheels, Ollama) don't include gfx1010
- You still need source builds or `HSA_OVERRIDE` workarounds
- Performance is degraded compared to officially supported GPUs

### Recommendation

For RX 5700 XT users in 2025-2026:

1. **Don't expect plug-and-play** - ROCm 6.1+ does NOT mean native out-of-box support
2. **whisper.cpp + Vulkan/HIPBLAS** remains the most practical path
3. **Source builds work** but require effort: [PyTorch-ROCm-gfx1010](https://github.com/Efenstor/PyTorch-ROCm-gfx1010)
4. **Docker images** may have gfx1010 pre-built: [wyoming-faster-whisper-rocm](https://github.com/Donkey545/wyoming-faster-whisper-rocm)

---

## 1. Official ROCm Support Status

### RDNA 1 / gfx1010 is NOT Officially Supported

| ROCm Version | gfx1010 Support | Notes |
|--------------|-----------------|-------|
| ROCm 5.x | No | Never officially supported |
| ROCm 6.0 | No | LLVM target present but libraries missing |
| ROCm 6.1+ | **Partial** | Tensile/rocBLAS fallback libraries included |
| ROCm 6.4.x | **Partial** | Fallback libraries in distro packages |
| ROCm 7.x | No | **Still NOT in official compatibility matrix** |

**Nuanced Status:** While Tensile PR #1897 (March 2024) added fallback library generation for gfx1010, AMD has NOT added RDNA1 to their official compatibility matrix. The gfx1010 target exists in builds but is considered "unofficial" and lacks optimized kernels.

**Sources:**
- [ROCm Issue #887 - 5700 XT Support](https://github.com/ROCm/ROCm/issues/887)
- [ROCm Compatibility Matrix](https://rocm.docs.amd.com/en/latest/compatibility/compatibility-matrix.html)
- [ROCm Device Support Wishlist](https://github.com/ROCm/ROCm/discussions/4276)

## 2. HSA_OVERRIDE_GFX_VERSION Workaround

### Does HSA_OVERRIDE_GFX_VERSION=10.3.0 Work?

**Short answer: Mostly no, with significant caveats.**

| Scenario | Result |
|----------|--------|
| PyTorch < 2.0 | Sometimes worked |
| PyTorch >= 2.0 | **Segfaults** - completely broken |
| Ollama (ROCm 6.4.1) | May work with 10.1.0 |
| Ollama (ROCm 6.4.3) | Broken - SIGSEGV crashes |
| CTranslate2 | Untested/unreliable |

The `HSA_OVERRIDE_GFX_VERSION=10.3.0` trick (which spoofs RDNA 2 gfx1030) **no longer works** for PyTorch-based workflows after torch 2.0.0. It causes segmentation faults.

For the 5700 XT, the correct override should be `10.1.0` (gfx1010), not `10.3.0`:
```bash
export HSA_OVERRIDE_GFX_VERSION=10.1.0
```

However, even this is unreliable and version-dependent.

**Sources:**
- [PyTorch Issue #106728 - Segfaults on RDNA1](https://github.com/pytorch/pytorch/issues/106728)
- [Ollama Issue #12111 - SIGSEGV with 10.3.0](https://github.com/ollama/ollama/issues/12111)
- [Ollama Issue #8806 - RX 5700 XT GPU Detection](https://github.com/ollama/ollama/issues/8806)

## 3. Faster-Whisper / CTranslate2 on 5700 XT

### Success Stories

Limited but real success has been reported:
- Users got Whisper working on 5700 XT with "medium" model using ~97% of 8GB VRAM
- Required `--fp16 False` flag to avoid garbled transcription output
- Performance gains were modest compared to the setup difficulty

### Requirements

1. **Build CTranslate2 from source** with gfx1010 target
2. **Use community forks** like arlo-phoenix/CTranslate2-rocm
3. **Docker containers** are the easiest path (see below)

### Docker Solutions

| Docker Image | gfx1010 Support | Notes |
|-------------|-----------------|-------|
| [wyoming-faster-whisper-rocm](https://github.com/Donkey545/wyoming-faster-whisper-rocm) | gfx900-gfx1151 | Home Assistant integration |
| [pigeekcom/wyoming-faster-whisper-rocm](https://hub.docker.com/r/pigeekcom/wyoming-faster-whisper-rocm) | Yes | 68GB+ image size |
| [insanely-fast-whisper-rocm](https://github.com/beecave-homelab/insanely-fast-whisper-rocm) | ROCm 6.1-7.1 | May require custom build |

**Warning:** These images are massive (60-70GB) and may require building with `PYTORCH_ROCM_ARCH=gfx1010` to work properly.

**Sources:**
- [OpenAI Whisper Discussion #55 - ROCm Support](https://github.com/openai/whisper/discussions/55)
- [wyoming-faster-whisper-rocm GitHub](https://github.com/Donkey545/wyoming-faster-whisper-rocm)

## 4. PyTorch ROCm on 5700 XT

### Current Status: Broken Unless You Build from Source

The only working solution is building PyTorch from source with explicit gfx1010 support:

**Key Resource:** [PyTorch-ROCm-gfx1010](https://github.com/Efenstor/PyTorch-ROCm-gfx1010) - Instructions for building PyTorch 2.8 on Debian 12 with gfx1010 support.

### Major Limitations

| Issue | Impact |
|-------|--------|
| No flash attention | Transformer models slower |
| No AOTriton support | PyTorch 2.3+ broken |
| glibc 2.41+ breaks prebuilt wheels | Must compile from source |
| Triton has no RDNA1 support | Memory-efficient attention unavailable |

### Community Build Project

[ROCm-RDNA1](https://github.com/TheTrustedComputer/ROCm-RDNA1) provides build scripts for:
- PyTorch targeting gfx1010
- ONNX Runtime
- Related libraries

**Important:** This is a community-driven effort, not AMD-supported.

**Sources:**
- [PyTorch-ROCm-gfx1010](https://github.com/Efenstor/PyTorch-ROCm-gfx1010)
- [ROCm-RDNA1](https://github.com/TheTrustedComputer/ROCm-RDNA1)

## 5. Alternative Paths

### Option A: whisper.cpp with HIPBLAS (Recommended)

whisper.cpp supports AMD GPUs via HIPBLAS (ROCm HIP):

```bash
# Install ROCm HIP SDK
sudo apt install rocm-hip-sdk

# Build whisper.cpp with HIPBLAS
git clone https://github.com/ggml-org/whisper.cpp
cd whisper.cpp
WHISPER_HIPBLAS=1 make -j

# Run with GPU
./main -m models/ggml-medium.bin -f audio.wav
```

**Performance:** Users report ~7x speedup over CPU with HIPBLAS on AMD GPUs.

**Caveat:** Math libraries for gfx1010 are limited (only rocBLAS and rocSOLVER fully support it).

**Sources:**
- [HIPBLAS Success Story](https://github.com/ggml-org/whisper.cpp/discussions/1491)
- [whisper.cpp AMD GPU Support](https://github.com/ggml-org/whisper.cpp/issues/2828)

### Option B: whisper.cpp with Vulkan (Cross-Platform)

Vulkan provides vendor-agnostic GPU acceleration:

```bash
# Build with Vulkan support
cmake -B build -DWHISPER_VULKAN=1
cmake --build build

# Verify Vulkan detection
./build/bin/main -m models/ggml-base.bin -f audio.wav
```

**Performance:**
- ~12x speedup on AMD integrated graphics (Radeon 680M)
- Works on Linux better than Windows
- Cross-vendor compatibility (AMD/NVIDIA/Intel)

**Known Issues:**
- Some AMD GPUs show garbled output on Windows
- May have low GPU utilization on certain configs

**Sources:**
- [Vulkan Backend Discussion](https://github.com/ggml-org/whisper.cpp/discussions/2375)
- [Whisper.cpp 1.8.3 Performance Boost](https://www.phoronix.com/news/Whisper-cpp-1.8.3-12x-Perf)

### Option C: CPU-Only with faster-whisper (Reliable Fallback)

If GPU acceleration proves unreliable, CPU-based faster-whisper works well:

| CPU | Model | Realtime Factor |
|-----|-------|-----------------|
| Ryzen 4500U | small.en | ~0.10x (10x slower than realtime) |
| Ryzen 3600 | medium | ~0.05x (20x slower than realtime) |
| i7 9750H | medium | Very slow (~16 hours for 1 hour audio) |
| Modern 8-core | small | ~0.2-0.5x (acceptable for short clips) |

**Tips for CPU performance:**
- Use `int8` quantization: `compute_type="int8"`
- Use smaller models: `tiny.en` or `base.en` for real-time use
- Enable VAD filtering to skip silence

**Sources:**
- [faster-whisper GitHub](https://github.com/SYSTRAN/faster-whisper)
- [Whisper CPU Performance Discussion](https://github.com/openai/whisper/discussions/369)

### Option D: OpenCL (Limited Support)

OpenCL is available through ROCm's runtime but has limited whisper.cpp support and worse performance than HIPBLAS or Vulkan.

## 6. Practical Recommendations

### For Quick Results (Minimal Effort)

1. **Try whisper.cpp with Vulkan** first - cross-platform, no ROCm drama
2. **Fall back to CPU** with faster-whisper + int8 quantization if Vulkan fails

### For Best GPU Performance (High Effort)

1. Install ROCm (may need older version like 6.4.1)
2. Build whisper.cpp with HIPBLAS
3. Test thoroughly - results may be unstable

### For Home Assistant / Docker Users

1. Use [wyoming-faster-whisper-rocm](https://github.com/Donkey545/wyoming-faster-whisper-rocm)
2. Set `PYTORCH_ROCM_ARCH=gfx1010` during build
3. Expect 60-70GB image size

### What NOT to Do

- Don't expect `HSA_OVERRIDE_GFX_VERSION=10.3.0` to work with PyTorch 2.0+
- Don't rely on official ROCm support coming for RDNA 1
- Don't assume pre-built Docker images work without modification

## 7. Summary Table

| Approach | Effort | Reliability | Performance | Recommendation |
|----------|--------|-------------|-------------|----------------|
| whisper.cpp + Vulkan | Low | Medium | ~5-12x vs CPU | **Try First** |
| whisper.cpp + HIPBLAS | Medium | Medium | ~7x vs CPU | Good option |
| faster-whisper CPU (int8) | Very Low | High | 0.1-0.3x realtime | Reliable fallback |
| CTranslate2 ROCm (Docker) | High | Low | Unknown | Advanced users |
| PyTorch ROCm (source build) | Very High | Low | Variable | Not recommended |

## 8. References

### Official Documentation
- [ROCm Compatibility Matrix](https://rocm.docs.amd.com/en/latest/compatibility/compatibility-matrix.html)
- [ROCm GPU Hardware Specs](https://rocm.docs.amd.com/en/latest/reference/gpu-arch-specs.html)
- [AMD ROCm Blog: Whisper](https://rocm.blogs.amd.com/artificial-intelligence/whisper/README.html)

### GitHub Issues/Discussions
- [ROCm Issue #887 - 5700 XT Support](https://github.com/ROCm/ROCm/issues/887)
- [PyTorch Issue #106728 - RDNA1 Segfaults](https://github.com/pytorch/pytorch/issues/106728)
- [Ollama Issue #2503 - 5700 XT Support](https://github.com/ollama/ollama/issues/2503)
- [whisper.cpp HIPBLAS Discussion](https://github.com/ggml-org/whisper.cpp/discussions/1491)
- [Tensile Issue #1757 - Backend Libraries for gfx1010](https://github.com/ROCm/Tensile/issues/1757)
- [Tensile PR #1897 - Fallback Library Fix](https://github.com/ROCm/Tensile/pull/1897)
- [ROCm Discussion #4030 - Regression in ROCm 5.3+ for gfx1010](https://github.com/ROCm/ROCm/discussions/4030)

### Community Projects
- [ROCm-RDNA1](https://github.com/TheTrustedComputer/ROCm-RDNA1) - RDNA1 build scripts
- [PyTorch-ROCm-gfx1010](https://github.com/Efenstor/PyTorch-ROCm-gfx1010) - PyTorch build guide
- [wyoming-faster-whisper-rocm](https://github.com/Donkey545/wyoming-faster-whisper-rocm) - Docker solution
- [arlo-phoenix/CTranslate2-rocm](https://github.com/arlo-phoenix/CTranslate2-rocm) - CTranslate2 fork
- [Arch Linux rocblas Package](https://archlinux.org/packages/extra/x86_64/rocblas/files/) - Shows fallback_gfx1010 files included
