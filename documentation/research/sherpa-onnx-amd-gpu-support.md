# Sherpa-ONNX AMD GPU Support Research

*Research Date: 2026-02-06*

## Executive Summary

Sherpa-onnx has **built-in DirectML support** via the cmake flag `SHERPA_ONNX_ENABLE_DIRECTML=ON`. DirectML works with any DirectX 12 GPU including the RX 5700 XT, completely sidestepping the ROCm compatibility mess. This is a significantly easier path to AMD GPU acceleration than the CTranslate2/ROCm approach. However, there are no pre-built DirectML Python wheels -- it requires building from source. And a caveat: DirectML is now in "maintenance mode" at Microsoft, with WinML as the successor (Windows 11 24H2+).

## 1. Does Sherpa-ONNX Support AMD GPUs?

**Yes, via DirectML.** Sherpa-onnx supports three GPU/accelerator execution providers for desktop:

| Provider | Flag | Platform | AMD GPU Support |
|----------|------|----------|-----------------|
| CUDA | `SHERPA_ONNX_ENABLE_GPU=ON` | Linux/Windows | No (NVIDIA only) |
| DirectML | `SHERPA_ONNX_ENABLE_DIRECTML=ON` | Windows only | **Yes -- all DX12 GPUs** |
| CoreML | built-in on macOS | macOS | N/A |

ONNX Runtime execution providers that could theoretically work with AMD GPUs:
- **DirectML** -- DirectX 12 based, works with AMD/NVIDIA/Intel/Qualcomm
- **ROCm** -- AMD's HIP/ROCm stack, Linux only, limited GPU support
- **MIGraphX** -- AMD's graph optimizer, Linux only, datacenter GPUs
- **Vulkan** -- Not implemented in ONNX Runtime (open feature request)

## 2. DirectML as an Option

**This is the most promising path.** Key findings:

- Sherpa-onnx has a `SHERPA_ONNX_ENABLE_DIRECTML` cmake flag
- DirectML works with **any DirectX 12 capable GPU** including the RX 5700 XT
- The RX 5700 XT fully supports DirectX 12 (RDNA1 architecture)
- DirectML is a system component of Windows 10 (version 1903+) -- no driver installation needed
- Confirmed working: Whisper tiny.int8 model runs successfully with DirectML
- Known issue: Whisper medium model had GPU memory errors on an 8GB GPU (issue #1240)

### Build Configuration

```
cmake -B build \
  -DCMAKE_BUILD_TYPE=Release \
  -DSHERPA_ONNX_ENABLE_DIRECTML=ON \
  -DBUILD_SHARED_LIBS=ON \
  .
```

**Requirement:** DirectML builds MUST use shared libraries (`BUILD_SHARED_LIBS=ON`). Static linking is not supported without modifying CMakeLists.txt.

### DirectML Maintenance Mode Warning

Microsoft has moved DirectML to **maintenance mode**:
- No new functionality or feature updates planned
- Security and compliance fixes only
- Successor: **Windows ML (WinML)** on Windows 11 24H2+
- WinML dynamically selects the best execution provider for your hardware
- DirectML will still ship with future Windows versions and remains functional
- For Windows 10 users, DirectML remains the primary option

## 3. ROCm Execution Provider

ONNX Runtime has a ROCm EP, but it's problematic for consumer AMD GPUs:

- **Officially supported:** MI100/MI200/MI300 datacenter GPUs (gfx90a, gfx942)
- **gfx1010 (RX 5700 XT): NOT officially supported**
- Linux only -- no Windows ROCm support
- Building from source with custom `CMAKE_HIP_ARCHITECTURES=gfx1010` is theoretically possible
- Community project exists: [ROCm-RDNA1](https://github.com/TheTrustedComputer/ROCm-RDNA1) for unofficial RDNA1 support
- Practical reality: unstable, segfaults reported on gfx1010 with ROCm

**Verdict:** ROCm is not a viable path for RX 5700 XT, especially on Windows.

## 4. Vulkan Compute

- **ONNX Runtime does NOT have a Vulkan execution provider**
- There is an open [feature request (#21917)](https://github.com/microsoft/onnxruntime/issues/21917) on the ONNX Runtime repo
- A separate project [WONNX](https://github.com/webonnx/wonnx) provides WebGPU/Vulkan-based ONNX inference but is a completely different runtime
- Not relevant for sherpa-onnx

## 5. Current State of Sherpa-ONNX GPU Support

From GitHub issues and documentation:

- **CUDA support** is mature with pre-built wheels and documentation
- **DirectML support** exists in the build system but is underdocumented
  - Not mentioned in official Python install docs
  - Not listed as a provider option in Python example scripts (only "cpu", "cuda", "coreml")
  - The `setup.py` has no DirectML variant -- only CUDA GPU wheels are built
  - Users who need DirectML must build the C++ library from source
- **AMD published an article** about sherpa-onnx on Windows with AMD Ryzen AI platform, confirming AMD's interest in the project
- GitHub issues confirm DirectML builds work but have edge cases (large model memory issues)

### Provider String

When using DirectML with sherpa-onnx's Python API, the provider would be passed as `"directml"` to the recognizer constructor (mapping to `DmlExecutionProvider` in ONNX Runtime).

## 6. Pre-Built Packages

| Package | DirectML | ROCm | CUDA |
|---------|----------|------|------|
| `pip install sherpa-onnx` | No | No | No (CPU only) |
| `pip install sherpa-onnx==1.12.13+cuda12.cudnn9` | No | No | **Yes** |
| Pre-built C++ binaries (GitHub releases) | No | No | Yes (Linux x64) |
| `pip install onnxruntime-directml` | **Yes** (ONNX Runtime only) | N/A | N/A |

**To get DirectML with sherpa-onnx, you must build from source:**

1. Clone sherpa-onnx
2. Build with `-DSHERPA_ONNX_ENABLE_DIRECTML=ON -DBUILD_SHARED_LIBS=ON`
3. The resulting shared library includes the DirectML execution provider
4. For Python: set `SHERPA_ONNX_CMAKE_ARGS` and run `python setup.py install`

**Alternative approach (untested):** Install the standard `sherpa-onnx` pip package alongside `onnxruntime-directml` and see if the DirectML provider can be swapped in. This would only work if sherpa-onnx delegates to the system onnxruntime rather than bundling its own.

## 7. Performance Expectations

No direct benchmarks found for sherpa-onnx + DirectML. Indirect data:

- **General DirectML vs CPU:** Reports of ~2x speedup with DirectML on commodity GPUs
- **RX 5700 with DirectML:** ~9ms inference latency reported for a landmark tracking model
- **Sherpa-onnx streaming models are lightweight:** Zipformer streaming models achieve 0.054 RTF on iPhone 15 Pro CPU -- already very fast
- **Key insight:** For small streaming models (Zipformer, Paraformer), GPU acceleration may provide marginal benefit since these models are already optimized for CPU real-time performance
- **Where GPU helps most:** Larger models (Whisper medium/large), batch processing, or when CPU is under load

### Streaming vs. Batch Processing

For your use case (real-time streaming speech recognition):
- Streaming models (Zipformer) are specifically designed for CPU efficiency
- The overhead of CPU-GPU data transfer in DirectML may negate gains for small models
- DirectML does not support parallel execution or multi-threaded inference sessions
- GPU acceleration is more beneficial for offline/batch transcription of longer audio

## Comparison: DirectML Path vs. CTranslate2/ROCm Path

| Factor | sherpa-onnx + DirectML | faster-whisper + CTranslate2/ROCm |
|--------|----------------------|----------------------------------|
| AMD GPU support | Any DX12 GPU (RX 5700 XT works) | gfx1010 not officially supported |
| Platform | Windows only | Linux only (ROCm) |
| Build complexity | Build sherpa-onnx from source | Build CTranslate2 with custom ROCm |
| Pre-built packages | None for DirectML | None for ROCm+gfx1010 |
| Stability | DirectML is stable, maintenance mode | ROCm on RDNA1 has segfault reports |
| Model ecosystem | Zipformer, Paraformer, Whisper (ONNX) | Whisper (CTranslate2 format) |
| Streaming support | Native streaming models | No native streaming (chunked) |
| Expected speedup | Modest (~2x) for small models | Unknown/unstable on gfx1010 |

## Recommendation

**DirectML via sherpa-onnx is a much easier and more reliable path than ROCm for AMD GPU acceleration on Windows.** However, for your specific use case of real-time streaming speech recognition with small models, the performance gain may be modest. The streaming models sherpa-onnx uses are already CPU-efficient.

The practical next steps if pursuing this:

1. Build sherpa-onnx from source with `SHERPA_ONNX_ENABLE_DIRECTML=ON`
2. Test with a streaming Zipformer model using `provider="directml"`
3. Benchmark against CPU to see if the GPU transfer overhead is worth it
4. For larger models (Whisper), DirectML should show clearer wins

## Sources

- [sherpa-onnx GitHub](https://github.com/k2-fsa/sherpa-onnx)
- [sherpa-onnx DirectML issue #1240](https://github.com/k2-fsa/sherpa-onnx/issues/1240)
- [sherpa-onnx GPU linking discussion #1202](https://github.com/k2-fsa/sherpa-onnx/discussions/1202)
- [sherpa-onnx Windows GPU issue #1954](https://github.com/k2-fsa/sherpa-onnx/issues/1954)
- [ONNX Runtime DirectML EP docs](https://onnxruntime.ai/docs/execution-providers/DirectML-ExecutionProvider.html)
- [ONNX Runtime ROCm EP docs](https://onnxruntime.ai/docs/execution-providers/ROCm-ExecutionProvider.html)
- [AMD GPUOpen ONNX DirectML guide](https://gpuopen.com/learn/onnx-directlml-execution-provider-guide-part1/)
- [AMD sherpa-onnx Windows article](https://www.amd.com/en/developer/resources/technical-articles/2026/a-practical-approach-to-using-sherpa-onnx-production-ready-on-wi.html)
- [Microsoft DirectML repo (maintenance mode)](https://github.com/microsoft/DirectML)
- [ONNX Runtime Vulkan feature request #21917](https://github.com/microsoft/onnxruntime/issues/21917)
- [ROCm RDNA1 unofficial support](https://github.com/TheTrustedComputer/ROCm-RDNA1)
- [ROCm ONNX Runtime for Radeon](https://rocm.docs.amd.com/projects/radeon-ryzen/en/latest/docs/install/installrad/native_linux/install-onnx.html)
- [sherpa-onnx Python install docs](https://k2-fsa.github.io/sherpa/onnx/python/install.html)
- [sherpa-onnx PyPI](https://pypi.org/project/sherpa-onnx/)
- [Open-LLM-VTuber sherpa GPU issue](https://github.com/Open-LLM-VTuber/Open-LLM-VTuber/issues/219)
- [ONNX Runtime execution providers list](https://onnxruntime.ai/docs/execution-providers/)
