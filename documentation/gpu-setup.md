# GPU Acceleration Setup

GPU acceleration lets you run bigger Whisper models with faster transcription. On CPU, `tiny` and `base` models work well. With a GPU, you can comfortably run `medium`, `large`, and `large-v3-turbo` for significantly better accuracy.

To enable GPU mode, set these in your [user settings](../README.md#️-configuration):
```yaml
whisper:
  device: cuda
  compute_type: float16
```
Note: `cuda` applies to both [NVIDIA](#nvidia-cuda) and [AMD](#amd--rdna-2-rocm) GPUs.

## NVIDIA (CUDA)

**Requirements:** NVIDIA GPU with CUDA support (GTX 900 series or newer)

1. Install CUDA Toolkit 12 (CUDA 13 is not yet supported by faster-whisper):
   ```
   winget install Nvidia.CUDA --version 12.9
   ```
   Or download from [nvidia.com/cuda-downloads](https://developer.nvidia.com/cuda-downloads)
2. Verify with `nvidia-smi` — you should see your GPU name and driver version
3. Set `device: cuda` and `compute_type: float16` (or `int8` on RTX 2000+ for faster but slightly less accurate transcription)
4. Restart Whisper Key

## AMD — RDNA 2+ (ROCm)

**Requirements:** AMD GPU with RDNA 2 or newer (RX 6000, 7000, 9000 series)

First, install the ROCm prerequisites using **one** of these two methods:

#### Method A: HIP SDK 7.1 installer

1. Install [HIP SDK 7.1](https://www.amd.com/en/developer/resources/rocm-hub/hip-sdk.html)
2. **DLL fix required:** HIP 7.1 renamed `hipblas.dll` to `libhipblas.dll`, which CTranslate2 doesn't recognize. Go to the ROCm bin folder (e.g. `C:\Program Files\AMD\ROCm\7.1\bin`), find `libhipblas.dll`, and copy it as `hipblas.dll` in the same folder.

#### Method B: ROCm SDK via pip (HIP 7.2)

**Prerequisite:** [AMD Adrenalin 26.1.1](https://www.amd.com/en/resources/support-articles/release-notes/RN-RAD-WIN-26-1-1.html) graphics driver or newer

```powershell
pip install --no-cache-dir `
    https://repo.radeon.com/rocm/windows/rocm-rel-7.2/rocm_sdk_core-7.2.0.dev0-py3-none-win_amd64.whl `
    https://repo.radeon.com/rocm/windows/rocm-rel-7.2/rocm_sdk_devel-7.2.0.dev0-py3-none-win_amd64.whl `
    https://repo.radeon.com/rocm/windows/rocm-rel-7.2/rocm_sdk_libraries_custom-7.2.0.dev0-py3-none-win_amd64.whl `
    https://repo.radeon.com/rocm/windows/rocm-rel-7.2/rocm-7.2.0.dev0.tar.gz
```

Then install Whisper Key:

### Portable exe

1. Download `whisper-key-v*-windows-amd-gpu-rocm.zip` from the [latest release](https://github.com/PinW/whisper-key-local/releases/latest)
2. Extract and run `whisper-key.exe`
3. Set `device: cuda` and `compute_type: float16`

### pip

1. Download `rocm-python-wheels-Windows.zip` from [CTranslate2 v4.7.1](https://github.com/OpenNMT/CTranslate2/releases/tag/v4.7.1) and extract
2. Install the wheel matching your Python version:
   ```
   pip install ctranslate2-4.7.1-cp313-cp313-win_amd64.whl --force-reinstall --no-deps
   ```
3. Set `device: cuda` and `compute_type: float16`
4. Restart Whisper Key

### pipx

1. Download `rocm-python-wheels-Windows.zip` from [CTranslate2 v4.7.1](https://github.com/OpenNMT/CTranslate2/releases/tag/v4.7.1) and extract
2. Install the wheel into the pipx venv:
   ```
   pipx runpip whisper-key-local install ctranslate2-4.7.1-cp313-cp313-win_amd64.whl --force-reinstall --no-deps
   ```
3. Set `device: cuda` and `compute_type: float16`
4. Restart Whisper Key

## AMD — RDNA 1 (ROCm 6.2)

**Requirements:** AMD GPU with RDNA 1 architecture (RX 5000 series)

> **Note:** The portable exe AMD variant ships with RDNA 2+ support. RDNA 1 users should install via pip or pipx.

1. Follow the instructions at **[ctranslate2-rocm-rdna1](https://github.com/PinW/ctranslate2-rocm-rdna1)** to install the custom wheel and prerequisites
   - For pip: `pip install <wheel> --force-reinstall --no-deps`
   - For pipx: `pipx runpip whisper-key-local install <wheel> --force-reinstall --no-deps`
2. Set `device: cuda` and `compute_type: float16`
3. Restart Whisper Key

## CPU (no setup needed)

CPU mode works out of the box with no extra dependencies.

- Use `compute_type: int8` for the best speed (default)
- `tiny` and `base` models transcribe quickly on most machines
- `small` is usable but slower — larger models will be very slow on CPU
