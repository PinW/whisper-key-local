# AMD GPU Acceleration for AI/ML Inference on Windows

Research compiled: 2026-03-16

---

## 1. ROCm on Windows

### Current State (as of early 2026)

ROCm has historically been Linux-first. AMD began offering Windows support in 2025 through the **HIP SDK for Windows** and a dedicated **PyTorch on Windows Preview** driver.

**Key milestones:**
- **Computex 2025:** AMD pledged ROCm support for Windows consumer GPUs
- **ROCm 6.4.4 (Oct 2025):** Public preview enabling PyTorch on Windows for RX 7000/9000 series
- **ROCm 7.2.0 (late 2025):** Expanded RDNA4 support, PyTorch 2.9 compatibility
- Windows support requires a special **PyTorch Preview Edition driver** from AMD

**Important caveat:** PyTorch on Windows includes ROCm 7.2 components, but the **entire ROCm stack is NOT yet supported on Windows**. Only PyTorch and ONNX Runtime EP are available.

### Supported GPUs on Windows (ROCm)

| Generation | GPUs | Windows ROCm Support |
|------------|------|---------------------|
| **RDNA 1** (gfx1010) | RX 5700 XT, RX 5600 XT | **Not supported, no plans** |
| **RDNA 2** (gfx1030-1032) | RX 6800-6950 XT, Pro W6800 | Supported (most SKUs, excludes RX 6600-6750 XT range) |
| **RDNA 3** (gfx1100-1102) | RX 7600-7900 XTX, Pro W7900 | Supported (excludes RX 7650 GRE, 7900 GRE) |
| **RDNA 4** (gfx1200-1201) | RX 9060-9070 XT | Supported (public preview) |

### Performance Issues

- RDNA4 convolution algorithms not fully supported yet; initial performance was around 1.8 TFLOPS (roughly GTX 1060 level)
- Winograd convolution kernel has been merged to develop branch; improvements expected in nightly builds
- ROCm on Windows is still **public preview** quality

### RDNA1 Workarounds (Linux only)

Community project [ROCm-RDNA1](https://github.com/TheTrustedComputer/ROCm-RDNA1) provides build scripts for Linux. Requires compiling from source with `gfx1010` target. Flash attention and Triton do not work on RDNA1. Not viable on Windows.

---

## 2. DirectML

### Overview

DirectML is Microsoft's hardware-accelerated DirectX 12 library for machine learning on Windows. It works as an execution provider for ONNX Runtime.

**Key characteristics:**
- Works with **any DirectX 12 capable GPU** (AMD, NVIDIA, Intel, Qualcomm)
- Windows 10 (1903+) and Windows 11
- Install: `pip install onnxruntime-directml`
- Available for Python 3.11, 3.12, 3.13 on Windows amd64

### Status

**DirectML is now in "sustained engineering" mode** -- it continues to be supported, but new feature development has moved to **WinML** for Windows-based ONNX Runtime deployments. WinML dynamically selects the best execution provider based on hardware.

### Usage

```python
import onnxruntime as ort
session = ort.InferenceSession("model.onnx", providers=["DmlExecutionProvider"])
```

### Performance

- DirectML is **significantly slower than ROCm** for AI workloads -- reports indicate ROCm is up to **4x faster**
- DirectML has been reported as **2x slower than CPU** in some TensorFlow benchmarks (though this has improved)
- DirectML is a general-purpose API, not optimized specifically for AI like CUDA/ROCm
- Advantage: broadest hardware compatibility of any GPU acceleration option on Windows

### RDNA Generation Compatibility

All RDNA generations (1-4) support DirectX 12, so **DirectML works on all of them**, including the RX 5700 XT.

---

## 3. Vulkan Compute

### Overview

Vulkan is an open, cross-vendor graphics and compute API. It provides GPU acceleration for ML inference through projects like **llama.cpp** and **whisper.cpp**.

### llama.cpp with Vulkan

- Build with `-DGGML_VULKAN=1`
- Works on **all AMD GPUs** with Vulkan support (GCN, Vega, RDNA 1-4)
- Pre-built Windows binaries available
- Tested successfully on: RX 580, RX 5700 XT, RX 7800 XT, RX 7900 XT
- Some limitations: no Vulkan flash attention, some reports of only accessing ~50% of GPU memory

### whisper.cpp with Vulkan

- Build with `-DGGML_VULKAN=1` and Vulkan SDK installed
- **Pre-built Windows binaries** available from community (jerryshell/whisper.cpp-windows-vulkan-bin)
- whisper.cpp 1.8.3 claimed "12x performance boost with integrated graphics"
- **On RX 9070 XT:** ~7.5-8x realtime transcription with large models
- **On AMD iGPUs (Radeon 680M):** 3-4x better realtime factor vs CPU-only

### Vulkan vs ROCm Performance

One analysis showed Vulkan with **50%+ performance advantages over ROCm** in some LLM workloads. Vulkan is considered the most practical GPU acceleration option for consumer AMD GPUs, especially older ones.

### RDNA Generation Compatibility

All RDNA generations support Vulkan. This is the **most broadly compatible** GPU acceleration option.

---

## 4. ONNX Runtime + DirectML

### The Most Promising Path for Broad AMD GPU Support

This is the most accessible option for running ML models on AMD GPUs on Windows because:
- No special drivers needed (standard AMD drivers include DirectX 12)
- Works on all RDNA generations (1-4)
- Simple pip install
- Growing model ecosystem

### Setup

```bash
pip install onnxruntime-directml
```

```python
import onnxruntime as ort
session = ort.InferenceSession(
    "model.onnx",
    providers=["DmlExecutionProvider"]
)
```

### Model Optimization

Microsoft's **Olive** toolchain can optimize ONNX models for DirectML execution, including:
- Operator fusions
- Kernel optimizations for CPU and GPU
- Quantization (FP32 to INT8)
- Combining beam search + encoder/decoder into single ONNX model (for Whisper)

### Whisper on ONNX Runtime + DirectML

Microsoft provides an official sample for running Whisper with DirectML:
- [DirectML Whisper sample](https://github.com/microsoft/DirectML/blob/master/PyTorch/audio/whisper/README.md)
- ONNX Runtime + Olive can export Whisper as an "all-in-one" optimized ONNX model
- WebNN + DirectML enables browser-based Whisper (Whisper Base runs in-browser)

### Performance Expectations

DirectML for Whisper on AMD GPUs is typically faster than CPU-only but slower than CUDA on equivalent NVIDIA hardware. Specific benchmarks for AMD GPUs with DirectML + Whisper are sparse.

---

## 5. OpenVINO

### AMD GPU Support: Not Available

OpenVINO is **Intel-only** for GPU acceleration:
- **AMD GPUs:** Not supported (confirmed by Intel as of Feb 2025)
- **AMD CPUs:** Works for CPU-based inference (unofficially), can achieve significant speedups (30ms down to 3ms reported)
- **Intel GPUs (integrated & discrete):** Officially supported

OpenVINO is **not a viable path** for AMD GPU acceleration.

---

## 6. Speech-to-Text on AMD GPUs

### Option A: Whisper via ONNX Runtime + DirectML

**Best for: Broad AMD GPU support (RDNA 1-4)**

```bash
pip install onnxruntime-directml
```

Use Whisper ONNX models with DmlExecutionProvider. Microsoft provides optimized exports via Olive.

### Option B: whisper.cpp with Vulkan

**Best for: Performance on all AMD GPUs**

- Pre-built binaries available for Windows
- 7.5-8x realtime on RX 9070 XT with large model
- Works on RDNA 1-4
- Drawback: C/C++ library, harder to integrate with Python apps

### Option C: onnx-asr (Parakeet + Whisper via DirectML)

**Best for: Modern, high-accuracy STT with DirectML**

[onnx-asr](https://github.com/istupakov/onnx-asr) is a lightweight Python package supporting multiple ASR models with DirectML:

```bash
pip install onnx-asr[hub]
pip install onnxruntime-directml
```

```python
import onnx_asr

model = onnx_asr.load_model("nemo-parakeet-tdt-0.6b-v3", providers=["DmlExecutionProvider"])
result = model.recognize("test.wav")
```

**Supported models:**
- NVIDIA Parakeet TDT 0.6B v2 (English) / v3 (25 languages)
- NVIDIA Parakeet CTC 0.6B, RNNT 0.6B
- NVIDIA Canary v2 (Multilingual)
- OpenAI Whisper (tiny, base, small, large-v3-turbo)
- GigaAM v2/v3 (Russian)

**Parakeet vs Whisper performance:**
- Parakeet v2 RTFx: 36x on Ryzen 9 CPU, 57x on T4 GPU, 3380x with GPU batching
- Parakeet beats Whisper on English accuracy and speed
- Whisper has better multilingual/multitask flexibility
- Both available as ONNX models compatible with DirectML

### Option D: faster-whisper with ROCm (Linux only)

CTranslate2 does NOT support DirectML. faster-whisper requires CUDA or ROCm.

- `pip install ctranslate2-rocm` (Linux only)
- Community Docker builds available (wyoming-faster-whisper-rocm)
- **Not viable on Windows** for AMD GPUs

### Option E: ROCm PyTorch + Whisper (RDNA 3/4 on Windows)

For RX 7000/9000 series only:
- Install AMD PyTorch Preview driver
- Use PyTorch with ROCm for Windows
- Run OpenAI Whisper or HuggingFace transformers-based Whisper
- Still in preview; convolution performance issues on RDNA4

### Option F: Const-me/Whisper (Direct3D, Windows-only)

Uses Direct3D 11.0 instead of Vulkan. Developer noted "not sure performance is ideal on discrete AMD GPUs." Project appears abandoned (last commits 2023). Not recommended.

---

## 7. RDNA Generation Compatibility Matrix

| Approach | RDNA 1 (RX 5700 XT) | RDNA 2 (RX 6000) | RDNA 3 (RX 7000) | RDNA 4 (RX 9070 XT) |
|----------|---------------------|-------------------|-------------------|---------------------|
| **ROCm (Windows)** | No | Yes (most SKUs) | Yes (most SKUs) | Yes (preview) |
| **ROCm (Linux)** | Community only | Yes | Yes | Yes |
| **DirectML** | Yes | Yes | Yes | Yes |
| **Vulkan (whisper.cpp/llama.cpp)** | Yes | Yes | Yes | Yes |
| **ONNX Runtime + DirectML** | Yes | Yes | Yes | Yes |
| **onnx-asr + DirectML** | Yes | Yes | Yes | Yes |

### Recommendations by GPU

**RX 5700 XT (RDNA 1):**
- DirectML or Vulkan are the only options on Windows
- No ROCm support (Windows or Linux officially)
- Best bet: onnx-asr + DirectML for STT, or whisper.cpp + Vulkan

**RX 9070 XT (RDNA 4):**
- All options available
- ROCm on Windows (preview) offers best potential performance but still maturing
- DirectML for ease of use and stability
- Vulkan via whisper.cpp for proven ~7.5-8x realtime performance
- Best bet: ROCm when stable, DirectML/Vulkan as fallback

---

## 8. Performance Comparisons

### Relative Performance Ranking (AMD GPU inference, Windows)

| Backend | Relative Performance | Ease of Setup | Hardware Coverage |
|---------|---------------------|---------------|-------------------|
| **ROCm** | Best (up to 4x faster than DirectML) | Moderate (preview driver) | RDNA 2-4 only |
| **Vulkan** | Very Good (50%+ over ROCm in some LLM tests) | Moderate (build from source or find binaries) | All RDNA |
| **CPU** | Baseline | Easiest | Universal |
| **DirectML** | Lowest for AI-specific tasks | Easiest (pip install) | All RDNA |

### whisper.cpp Vulkan Benchmarks

| Hardware | Model | Performance |
|----------|-------|-------------|
| RX 9070 XT | Large | ~7.5-8x realtime |
| Radeon 680M (iGPU) | - | 3-4x realtime factor vs CPU |
| Generic iGPUs | - | "12x performance boost" (v1.8.3 claim) |

### onnx-asr Parakeet Benchmarks

| Model | CPU (Ryzen 9) | GPU (T4/CUDA) | TensorRT |
|-------|--------------|---------------|----------|
| Parakeet v2/v3 | 36x RTFx | 57x RTFx | ~3380x RTFx |
| GigaAM v3 CTC | 59x RTFx | - | 1370x RTFx |

(No DirectML-specific AMD GPU benchmarks published yet)

### DirectML vs ROCm

- ROCm reported as **4x faster** than DirectML in some AI tests
- DirectML was historically **2x slower than CPU** for TensorFlow (improved since)
- DirectML is general-purpose (not AI-optimized like CUDA/ROCm)

---

## Key Takeaways

1. **For the RX 5700 XT (RDNA 1):** DirectML via ONNX Runtime is the most practical GPU acceleration path on Windows. Vulkan via whisper.cpp is another solid option. No ROCm support exists or is planned.

2. **For the RX 9070 XT (RDNA 4):** ROCm on Windows is now available in preview but still maturing (performance issues with convolutions). DirectML and Vulkan are more stable today.

3. **onnx-asr** is a very promising option for STT: lightweight, supports Parakeet and Whisper models, works with DirectML on any AMD GPU. Parakeet models outperform Whisper on English.

4. **faster-whisper/CTranslate2** does NOT support DirectML and requires CUDA or ROCm. Not viable for AMD GPUs on Windows.

5. **DirectML is the simplest path** but also the slowest for GPU inference. It works on everything but may not deliver dramatic speedups over CPU for all workloads.

6. **Vulkan via whisper.cpp** delivers strong real-world performance (7.5-8x realtime on RX 9070 XT) and works across all RDNA generations, but requires using C/C++ binaries rather than Python.

7. **OpenVINO** does not support AMD GPUs -- Intel only.

8. The AMD GPU ML ecosystem on Windows is improving rapidly (ROCm for Windows launched 2025), but remains significantly behind NVIDIA CUDA in maturity.

---

## Sources

- [AMD ROCm for Windows - Compatibility Matrix](https://rocm.docs.amd.com/projects/radeon-ryzen/en/latest/docs/compatibility/compatibilityrad/windows/windows_compatibility.html)
- [AMD Blog: The Road to ROCm on Radeon for Windows and Linux](https://www.amd.com/en/blogs/2025/the-road-to-rocm-on-radeon-for-windows-and-linux.html)
- [AMD ROCm 6.4.4 PyTorch for Windows (VideoCardz)](https://videocardz.com/newz/amd-enables-windows-pytorch-support-for-radeon-rx-7000-9000-with-rocm-6-4-4-update)
- [AMD ROCm 6.4.4 PyTorch for Windows (WCCFtech)](https://wccftech.com/amd-rocm-6-4-4-pytorch-support-windows-radeon-9000-radeon-7000-gpus-ryzen-ai-apus/)
- [ONNX Runtime DirectML Execution Provider](https://onnxruntime.ai/docs/execution-providers/DirectML-ExecutionProvider.html)
- [Microsoft DirectML Whisper Sample](https://github.com/microsoft/DirectML/blob/master/PyTorch/audio/whisper/README.md)
- [onnx-asr GitHub](https://github.com/istupakov/onnx-asr)
- [onnx-asr PyPI](https://pypi.org/project/onnx-asr/)
- [whisper.cpp GitHub](https://github.com/ggml-org/whisper.cpp)
- [whisper.cpp Vulkan on AMD GPUs (MaroonMed)](https://www.maroonmed.com/subtitle-edit-and-whisper-cpp-stt-on-amd-and-other-non-nvidia-gpus-with-vulkan/)
- [whisper.cpp Windows Vulkan binaries](https://github.com/jerryshell/whisper.cpp-windows-vulkan-bin)
- [AMD GPU Acceleration Technologies Compared (GitHub Gist)](https://gist.github.com/danielrosehill/8793e2028ef4bd08c6ca955a38b40e5b)
- [ROCm-RDNA1 Community Project](https://github.com/TheTrustedComputer/ROCm-RDNA1)
- [faster-whisper GitHub](https://github.com/SYSTRAN/faster-whisper)
- [wyoming-faster-whisper-rocm](https://github.com/Donkey545/wyoming-faster-whisper-rocm)
- [AMD ROCm Blog: CTranslate2 on AMD GPUs](https://rocm.blogs.amd.com/artificial-intelligence/ctranslate2/README.html)
- [AMD ROCm Blog: Whisper on AMD GPUs](https://rocm.blogs.amd.com/artificial-intelligence/whisper/README.html)
- [OpenVINO System Requirements](https://docs.openvino.ai/systemrequirements)
- [llama.cpp Vulkan Performance Discussion](https://github.com/ggml-org/llama.cpp/discussions/10879)
- [AMD GPUOpen: ONNX + DirectML Guide](https://gpuopen.com/learn/onnx-directlml-execution-provider-guide-part1/)
- [ROCm vs CUDA Comparison (ThunderCompute)](https://www.thundercompute.com/blog/rocm-vs-cuda-gpu-computing)
- [Parakeet vs Whisper Comparison](https://medium.com/data-science-in-your-pocket/nvidia-parakeet-v2-vs-openai-whisper-which-is-the-best-asr-ai-model-5912cb778dcf)
- [2025 Edge STT Benchmark](https://www.ionio.ai/blog/2025-edge-speech-to-text-model-benchmark-whisper-vs-competitors)
- [AMD Whisper on Ryzen AI NPUs](https://www.amd.com/en/developer/resources/technical-articles/2025/unlocking-on-device-asr-with-whisper-on-ryzen-ai-npus.html)
- [Const-me/Whisper (D3D implementation)](https://github.com/Const-me/Whisper)
