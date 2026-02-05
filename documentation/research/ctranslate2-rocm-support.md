# CTranslate2 AMD GPU / ROCm Support Research

*Research Date: 2026-02-05*

## Executive Summary

As of February 2026, **official ROCm support has been merged into CTranslate2**. PR #1989 was merged on February 2, 2026, introducing AMD GPU support via ROCm HIP in version 4.7.1. However, this is new functionality with some limitations, and the ecosystem for faster-whisper on AMD GPUs still requires community solutions.

## Current Status

### Official CTranslate2 (v4.7.1+)

| Aspect | Status |
|--------|--------|
| ROCm Support | **Merged** (PR #1989, Feb 2, 2026) |
| First Release | v4.7.1 (Feb 4, 2026) |
| Maturity | New/Experimental |
| PyPI Wheels | CUDA only; ROCm wheels on GitHub Releases |

The official implementation:
- Targets ROCm 7 supported RDNA GPUs
- CDNA may work but with suboptimal wave size (32-bit vs 64-bit)
- RDNA2 support uncertain due to limited testing
- Described as "just enough changes to build for AMD, specific optimizations like flash attention for the future"

### Faster-Whisper AMD Support

**Official stance**: "This repo doesn't support non CUDA GPUs" (from faster-whisper issue #1370)

Faster-whisper depends on CTranslate2 for GPU acceleration. While CTranslate2 now has ROCm support, faster-whisper itself has not integrated this capability.

## Installation Methods

### Method 1: Official CTranslate2 v4.7.1+ (Recommended for New Projects)

ROCm wheels are available on [GitHub Releases](https://github.com/OpenNMT/CTranslate2/releases) (not PyPI):

```bash
# Download appropriate wheel from GitHub releases
pip install ctranslate2-4.7.1-cp311-cp311-linux_x86_64_rocm.whl
```

Requirements:
- Linux: ROCm installation + `rocm-hip-libraries` package
- Windows: `rocm_sdk_core` and `rocm_sdk_libraries_custom`
- ROCm 7.x recommended

### Method 2: arlo-phoenix/CTranslate2-rocm Fork (Proven Community Solution)

The most mature community solution, tested with faster-whisper workflows:

```bash
git clone https://github.com/arlo-phoenix/CTranslate2-rocm.git --recurse-submodules
cd CTranslate2-rocm

# Set GPU architecture (check with: rocminfo | grep gfx)
export PYTORCH_ROCM_ARCH=gfx1030  # Example for RDNA2

# Build with HIP support
CLANG_CMAKE_CXX_COMPILER=clang++ CXX=clang++ HIPCXX="$(hipconfig -l)/clang" \
HIP_PATH="$(hipconfig -R)" cmake -S . -B build \
-DWITH_MKL=OFF -DWITH_HIP=ON \
-DCMAKE_HIP_ARCHITECTURES=$PYTORCH_ROCM_ARCH \
-DBUILD_TESTS=ON -DWITH_CUDNN=ON

cmake --build build -- -j16
cd build && cmake --install . --prefix $CONDA_PREFIX

# Build Python wheel
cd ../python
pip install -r install_requirements.txt
python setup.py bdist_wheel
pip install dist/*.whl
```

Requirements:
- ROCm 6.2+ (tested with rocm/pytorch Docker image)
- Conda environment with Python 3.9+
- Build dependencies (cmake, clang)

### Method 3: AMD Official Fork (ROCm/CTranslate2)

AMD maintains a fork at [github.com/ROCm/CTranslate2](https://github.com/ROCm/CTranslate2):

```bash
git checkout amd_dev
cd docker_rocm
docker build -t rocm_ct2_v3.23.0 -f Dockerfile.rocm .
```

No pre-built wheels available; Docker or source build required.

### Method 4: Docker Images for Faster-Whisper + ROCm

Several community Docker solutions exist:

| Image | Status | Notes |
|-------|--------|-------|
| pigeekcom/wyoming-faster-whisper-rocm | Active | Wyoming protocol integration |
| jjajjara/rocm-whisper-api | Active | API-based Whisper |
| Donkey545/wyoming-faster-whisper-rocm | Active | Home Assistant integration |

## Supported GPU Architectures

| Architecture | Support Level | Notes |
|--------------|---------------|-------|
| RDNA 3 (gfx1100, gfx1101, gfx1102) | Best | Primary target for official support |
| RDNA 2 (gfx1030, gfx1031) | Uncertain | Limited testing, likely works |
| CDNA (gfx90a, gfx940, gfx942) | Suboptimal | Wave size mismatch (32 vs 64-bit) |
| GCN (gfx803, gfx900, gfx906) | Community only | Via arlo-phoenix fork; may need HSA_OVERRIDE_GFX_VERSION |

Check your GPU architecture:
```bash
rocminfo | grep gfx
```

For unsupported architectures, try:
```bash
export HSA_OVERRIDE_GFX_VERSION=10.3.0  # Example: force gfx1030 compatibility
```

## Known Limitations

### Official Implementation (v4.7.1)
- No flash attention optimization yet
- RDNA2 support not fully tested
- CDNA suboptimal performance
- ROCm wheels not on PyPI (must download from GitHub)

### arlo-phoenix Fork
- **BF16 disabled**: All bfloat16 code commented out due to missing `__hip_bfloat16` to `float` implicit conversion
- **No Flash Attention 2 or AWQ support planned** until upstream BF16 support improves
- Custom MIOpen implementation for Conv1D (hipDNN deprecated)

### Faster-Whisper Integration
- No official AMD support
- Must use CTranslate2-rocm fork and potentially patch faster-whisper
- Community Docker images are the easiest path

## Performance

From AMD's ROCm blog (October 2024), using INT8 quantization:

| Configuration | Latency | Tokens/sec | Speedup |
|--------------|---------|------------|---------|
| Float32 | 0.151s | 19.86 | 1x |
| INT8 | 0.043s | 70.14 | 3.5x |

Whisper models supported: tiny, base, small, medium, large

## Timeline / Roadmap

| Date | Event |
|------|-------|
| Aug 2023 | Maintainer declined to prioritize ROCm (issue #1072) |
| Oct 2023 | Community attempts using hipify (incomplete) |
| Oct 2024 | AMD publishes ROCm blog post for CTranslate2 |
| Feb 2, 2026 | **PR #1989 merged** - Official ROCm support |
| Feb 4, 2026 | v4.7.1 released with ROCm/HIP |
| Future | Flash attention, AWQ, better CDNA support (no timeline) |

## Recommendations for Whisper-Key

1. **Short term**: Continue CUDA-only support; AMD ecosystem is still maturing
2. **Medium term**: Monitor official CTranslate2 ROCm wheel availability on PyPI
3. **For AMD users today**: Recommend Docker-based solutions (wyoming-faster-whisper-rocm)
4. **Build from source**: Only for advanced users comfortable with ROCm toolchain

## References

- [CTranslate2 Issue #1072](https://github.com/OpenNMT/CTranslate2/issues/1072) - Original AMD GPU feature request
- [CTranslate2 PR #1989](https://github.com/OpenNMT/CTranslate2/pull/1989) - Merged ROCm support
- [arlo-phoenix/CTranslate2-rocm](https://github.com/arlo-phoenix/CTranslate2-rocm) - Community fork
- [ROCm/CTranslate2](https://github.com/ROCm/CTranslate2) - AMD official fork
- [AMD ROCm Blog: CTranslate2](https://rocm.blogs.amd.com/artificial-intelligence/ctranslate2/README.html) - Official AMD documentation
- [faster-whisper Issue #1370](https://github.com/SYSTRAN/faster-whisper/issues/1370) - AMD GPU support request
- [whisperX Issue #566](https://github.com/m-bain/whisperX/issues/566) - ROCm support discussion
- [CTranslate2 Installation Docs](https://opennmt.net/CTranslate2/installation.html) - Official installation guide
