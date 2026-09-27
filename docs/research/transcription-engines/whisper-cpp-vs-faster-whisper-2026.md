# Whisper.cpp vs Faster-Whisper: 2026 Research Report

*Research Date: February 5, 2026*

## Executive Summary

This report evaluates whether whisper.cpp has improved enough to warrant switching from faster-whisper for a cross-platform desktop app targeting Windows and macOS.

**Key Findings:**
- whisper.cpp has matured significantly with production-ready Metal and Vulkan support
- On Apple Silicon, whisper.cpp with CoreML is **5-6x faster** than faster-whisper
- On Windows with Vulkan, whisper.cpp delivers **10-12x speedup** over CPU
- faster-whisper still wins on NVIDIA CUDA (5-7x faster than whisper.cpp)
- The word spacing/accuracy issues we experienced remain context-dependent, not fully resolved

**Recommendation:** Consider migrating to whisper.cpp for true cross-platform GPU acceleration, especially given macOS Metal/CoreML benefits.

---

## 1. Background: Our Previous Experience

In 2025, we tested whisper.cpp and found:
- Poor accuracy for smaller models on CPU (missing word spaces)
- Slower than faster-whisper overall
- Limited GPU support

This report investigates whether these issues have been resolved.

---

## 2. Whisper.cpp Current State (2026)

### Recent Releases

| Version | Date | Key Changes |
|---------|------|-------------|
| v1.8.3 | Jan 2025 | 12x performance boost for iGPUs (Vulkan), Silero VAD v6.2 |
| v1.8.0 | Late 2024 | Flash attention by default, Metal performance improvements |
| v1.7.5 | Mid 2024 | ARM/iOS optimizations, XCFramework workflow |

### GPU Backend Status

| Backend | Status | Performance |
|---------|--------|-------------|
| **Metal (macOS)** | Mature, production-ready | Excellent on Apple Silicon |
| **CoreML (macOS)** | Mature | 2-3x faster than Metal alone via Neural Engine |
| **Vulkan (Win/Linux)** | Production-ready | 10-12x faster than CPU, works AMD/NVIDIA/Intel |
| **CUDA** | Experimental | Often slower than whisper.cpp's CPU implementation |

### Accuracy Improvements

Quantization research (March 2025) shows promising results:

| Quantization | WER | Size Reduction |
|--------------|-----|----------------|
| Baseline | 1.99% | - |
| INT8 | 1.99% | 45% |
| INT4 | **1.59%** | 62% |

However, whisper.cpp still has known issues:
- 30-50% higher WER than OpenAI implementation with default settings (can be mitigated)
- Higher hallucination rates in some scenarios (1046 repeated lines vs 155 for faster-whisper in one test)
- Word timestamps can drift 300-800ms

---

## 3. Faster-Whisper Current State (2026)

### Recent Releases

| Version | Date | Key Features |
|---------|------|--------------|
| v1.2.1 | Oct 2024 | Silero-VAD v6, timestamp fixes |
| v1.2.0 | - | distil-large-v3.5, private HuggingFace support |
| v1.1.0 | - | **Batched inference (4x faster)**, large-v3-turbo |

### CTranslate2 Updates (v4.6.3, Jan 2026)

- **CUDA 12.8 support**
- **cuDNN now optional** for Conv1d operations (easier deployment)
- AMD ROCm/HIP support improved (v4.7.0)

### GPU Support

| Backend | Status |
|---------|--------|
| **CUDA** | Mature, pip-installable NVIDIA libs |
| **ROCm/HIP** | Now supported (v4.7.0), but painful setup experience |
| **Metal** | **Not supported** |
| **Vulkan** | **Not supported** |

---

## 4. Performance Benchmarks

### CPU Performance (i7-12700H, 4 threads)

| Implementation | Model | Audio | Time |
|----------------|-------|-------|------|
| faster-whisper | small.en | 27m49s | **7m30s** |
| whisper.cpp | small.en | 27m49s | 9m45s |

**Winner: faster-whisper** (1.5-2x faster on CPU)

### Apple Silicon (M2 Air, 198.7s audio, beam=1)

| Model | faster-whisper INT8 | whisper.cpp ANE |
|-------|---------------------|-----------------|
| tiny | 4.03s | **1.74s** |
| base | 7.07s | **2.80s** |
| small | 19.89s | **8.09s** |
| medium | 57.32s | **22.81s** |
| large-v2 | 105.56s | **57.28s** |

**Winner: whisper.cpp with CoreML** (2.5-3x faster)

### Apple Silicon M4 (MacBook Pro 24GB)

| Implementation | Model | Time |
|----------------|-------|------|
| MLX Whisper | large-v3-turbo | 1.02s |
| whisper.cpp + CoreML | large-v3-turbo q5_0 | **1.23s** |
| faster-whisper | large-v3-turbo | 6.96s |

**Winner: whisper.cpp** (5-6x faster than faster-whisper)

### NVIDIA GPU (RTX 4080, 12min audio)

| Implementation | Model | Time |
|----------------|-------|------|
| **faster-whisper** | large-v2 | **30s** |
| whisper.cpp | medium | 3.4min |

**Winner: faster-whisper** (6-7x faster on CUDA)

### Windows iGPU with Vulkan (whisper.cpp v1.8.3)

- **12x speedup** vs CPU on AMD Ryzen 7 6800H (Radeon 680M)
- **12x speedup** vs CPU on Intel Core Ultra 7 155H
- Cross-vendor compatibility (AMD, NVIDIA, Intel)

### Memory Usage

| Aspect | faster-whisper | whisper.cpp |
|--------|----------------|-------------|
| Runtime overhead | Higher (Python) | **Lower (C++ binary)** |
| Startup time | ~1.8s | **<300ms** |
| VRAM usage | Moderate | **Lowest** |

---

## 5. Accuracy Comparison

Both use the same Whisper model weights, so accuracy is essentially identical with matching settings.

### Minor Differences

| Aspect | faster-whisper | whisper.cpp |
|--------|----------------|-------------|
| Disfluent speech ("um", restarts) | Better (0.6-0.8% WER reduction) | Standard |
| Word timestamps | **More precise** | Can drift 300-800ms |
| Hallucination rate | Lower | Higher in some tests |

### Word Spacing Issue

The word spacing issue we observed with smaller models on CPU appears to be:
- Related to tokenization/decoding settings, not fundamental to whisper.cpp
- Mitigatable with proper VAD configuration and prompt settings
- Still more prevalent than with faster-whisper

---

## 6. Cross-Platform Analysis

### For This Project (macOS + Windows Desktop App)

| Feature | whisper.cpp | faster-whisper |
|---------|-------------|----------------|
| macOS Metal | **Native** | Not supported |
| macOS CoreML | **3x boost with ANE** | Not supported |
| Windows Vulkan | **10-12x over CPU** | Not supported |
| Windows CUDA | Experimental | **Mature, 5-7x faster** |
| Python integration | Bindings available | **Native** |
| Binary size | **Small** | Larger (Python runtime) |
| Deployment | **Simpler** | More dependencies |

### GPU Acceleration Summary

| Platform | Best Option |
|----------|-------------|
| macOS (any) | **whisper.cpp + CoreML** |
| Windows + NVIDIA | **faster-whisper + CUDA** |
| Windows + AMD | whisper.cpp + Vulkan (easy) or faster-whisper + ROCm (painful setup, better perf) |
| Windows + Intel | **whisper.cpp + Vulkan** |
| Cross-platform with single codebase | **whisper.cpp** |

---

## 7. New Alternatives to Consider

### Large-v3-Turbo Model
- 6x faster than large-v3 with only 1-2% accuracy loss
- 809M parameters (vs 1.55B for large-v3)
- Supported by both implementations

### Distil-Whisper
- 6x faster, 49% smaller
- Within 1% WER of full Whisper
- Good for resource-constrained deployment

### MLX Whisper (macOS only)
- Native Apple framework
- Lightning-Whisper-MLX claims 10x faster than whisper.cpp
- Not cross-platform

### ONNX Runtime
- DirectML for Windows (AMD/NVIDIA/Intel)
- CoreML provider for macOS
- Requires model conversion

---

## 8. Recommendation

### Should We Switch to whisper.cpp?

**Arguments For:**
1. True cross-platform GPU acceleration (Metal + Vulkan)
2. On macOS, 5-6x faster than faster-whisper
3. Smaller binary, faster startup
4. Vulkan is plug-and-play for AMD/Intel (vs ROCm's painful setup in faster-whisper)

**Arguments Against:**
1. On Windows with NVIDIA, faster-whisper is 5-7x faster
2. Word spacing issues may still occur with smaller models
3. Higher hallucination rates in some scenarios
4. Would require significant code changes
5. faster-whisper now has ROCm/HIP support for AMD (though setup is painful)

### Suggested Approach

**Option A: Hybrid Architecture (Recommended)**
- Use whisper.cpp on macOS (CoreML backend)
- Keep faster-whisper on Windows (CUDA for NVIDIA, CPU fallback for others)
- More complex but optimal performance on each platform

**Option B: Full whisper.cpp Migration**
- Single codebase for both platforms
- Best macOS performance
- Acceptable Windows performance with Vulkan
- Trade-off: lose CUDA optimization for NVIDIA users

**Option C: Status Quo**
- Keep faster-whisper everywhere
- macOS users get CPU-only (still reasonable with Accelerate)
- Simpler codebase

### My Recommendation

Given that:
- macOS support is new and performance matters there
- Not all Windows users have NVIDIA GPUs
- Whisper.cpp has matured significantly

**Consider Option A (Hybrid)** if development resources allow, or **Option B** for simplicity with good-enough performance everywhere. The CoreML speedup on Apple Silicon is substantial enough to justify the effort.

---

## Sources

- [whisper.cpp GitHub](https://github.com/ggml-org/whisper.cpp)
- [faster-whisper GitHub](https://github.com/SYSTRAN/faster-whisper)
- [CTranslate2 GitHub](https://github.com/OpenNMT/CTranslate2)
- [Phoronix: Whisper.cpp 1.8.3 12x Performance](https://www.phoronix.com/news/Whisper-cpp-1.8.3-12x-Perf)
- [mac-whisper-speedtest benchmarks](https://github.com/anvanvan/mac-whisper-speedtest)
- [faster-whisper vs whisper.cpp discussion](https://github.com/SYSTRAN/faster-whisper/discussions/368)
- [Modal: Choosing Whisper Variants](https://modal.com/blog/choosing-whisper-variants)
- [Northflank: Best STT Models 2026](https://northflank.com/blog/best-open-source-speech-to-text-stt-model-in-2026-benchmarks)
- [arXiv: Quantization for Whisper](https://arxiv.org/abs/2503.09905)
- [AMD ROCm 7 announcement](https://www.tomshardware.com/pc-components/gpus/amd-unveils-rocm-7)
- [Voicci: Apple Silicon Whisper Performance](https://www.voicci.com/blog/apple-silicon-whisper-performance.html)
