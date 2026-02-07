# GPU Acceleration Setup

GPU acceleration lets you run bigger Whisper models with faster transcription. On CPU, `tiny` and `base` models work well. With a GPU, you can comfortably run `medium`, `large`, and `large-v3-turbo` for significantly better accuracy.

To enable GPU mode, set these in your [user settings](../README.md#️-configuration):
```yaml
whisper:
  device: cuda
  compute_type: float16
```
Note: `cuda` applies to both [NVIDIA](#nvidia-cuda) and [AMD](#amd--rdna-2-rocm-7) GPUs.

## NVIDIA (CUDA)

**Requirements:** NVIDIA GPU with CUDA support (GTX 900 series or newer)

1. Install CUDA Toolkit 12 (CUDA 13 is not yet supported by faster-whisper):
   ```
   winget install Nvidia.CUDA --version 12.9
   ```
   Or download from [nvidia.com/cuda-downloads](https://developer.nvidia.com/cuda-downloads)
2. Verify with `nvidia-smi` — you should see your GPU name and driver version
3. Set `device: cuda` and `compute_type: float16`
4. Restart Whisper Key

## AMD — RDNA 2+ (ROCm 7+)

**Requirements:** AMD GPU with RDNA 2 or newer architecture (RX 6000 series+)

1. Install a CTranslate2 ROCm wheel — check [OpenNMT/CTranslate2 releases](https://github.com/OpenNMT/CTranslate2/releases) for builds
2. Install the HIP SDK version required by the wheel
3. Set `device: cuda` and `compute_type: float16`
4. Restart Whisper Key

## AMD — RDNA 1 (ROCm 6.2)

**Requirements:** AMD GPU with RDNA 1 architecture (RX 5000 series)

1. Follow the instructions at **[ctranslate2-rocm-rdna1](https://github.com/PinW/ctranslate2-rocm-rdna1)** to install the custom wheel and prerequisites
2. Set `device: cuda` and `compute_type: float16`
3. Restart Whisper Key

## CPU (no setup needed)

CPU mode works out of the box with no extra dependencies.

- Use `compute_type: int8` for the best speed (default)
- `tiny` and `base` models transcribe quickly on most machines
- `small` is usable but slower — larger models will be very slow on CPU

