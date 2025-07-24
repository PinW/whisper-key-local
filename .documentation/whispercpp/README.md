# whisper.cpp Documentation

## Project Overview
High-performance C/C++ implementation of OpenAI's Whisper automatic speech recognition (ASR) model.

### Key Features
- Plain C/C++ implementation without dependencies
- Optimized for multiple platforms (Apple Silicon, x86, POWER architectures)
- Support for mixed precision and integer quantization
- GPU acceleration (NVIDIA, Vulkan, Core ML, OpenVINO)
- Zero memory allocations at runtime
- Voice Activity Detection (VAD)
- Confidence color-coding for transcriptions
- Real-time audio input streaming

## Installation
```bash
git clone https://github.com/ggml-org/whisper.cpp.git
cd whisper.cpp
sh ./models/download-ggml-model.sh base.en
cmake -B build
cmake --build build -j --config Release
```

## Quick Usage
```bash
./build/bin/whisper-cli -f samples/jfk.wav
```

## Supported Platforms
- Mac OS (Intel and Arm)
- iOS
- Android
- Linux
- Windows
- WebAssembly
- Raspberry Pi

## Model Sizes and Memory Usage
- tiny: 273 MB
- base: 388 MB
- small: 852 MB
- medium: 2.1 GB
- large: 3.9 GB

## GPU/Acceleration Support
- NVIDIA CUDA
- Vulkan
- Core ML
- OpenVINO
- OpenBLAS
- Ascend NPU
- Moore Threads GPU

## License
MIT License

Source: https://github.com/ggerganov/whisper.cpp