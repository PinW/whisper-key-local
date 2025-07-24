# pywhispercpp API Documentation

## Overview
Python bindings for whisper.cpp providing a Pythonic API for speech transcription with multiple backend support.

## Installation
```bash
# From source (recommended)
pip install git+https://github.com/absadiki/pywhispercpp

# Pre-built wheels
pip install pywhispercpp

# With backend acceleration
GGML_CUDA=1 pip install git+https://github.com/absadiki/pywhispercpp  # NVIDIA
WHISPER_COREML=1 pip install git+https://github.com/absadiki/pywhispercpp  # CoreML
GGML_VULKAN=1 pip install git+https://github.com/absadiki/pywhispercpp  # Vulkan
```

## Model Class

### Constructor
```python
Model(model="tiny", models_dir=None, params_sampling_strategy=0, redirect_whispercpp_logs_to=False, **params)
```

#### Parameters:
- **model**: Model name (tiny, base, small, medium, large) or path to ggml model
- **models_dir**: Directory for model storage/download (default: MODELS_DIR)
- **params_sampling_strategy**: Sampling strategy parameter (default: 0)
- **redirect_whispercpp_logs_to**: Log redirection (False, file path, sys.stdout, sys.stderr, None)
- **params**: Any whisper.cpp parameters as keyword arguments

### Transcribe Method
```python
transcribe(media_file, new_segment_callback=None, **params)
```

#### Parameters:
- **media_file**: Path to audio/video file or raw numpy array
- **new_segment_callback**: Callback function for real-time processing
- **params**: Additional whisper.cpp parameters

#### Returns:
List of Segment objects with:
- `text`: Transcribed text
- `start`: Start timestamp
- `end`: End timestamp

## Basic Usage
```python
from pywhispercpp.model import Model

# Initialize model
model = Model('base.en', n_threads=6, print_progress=False)

# Transcribe
segments = model.transcribe('audio.wav')
for segment in segments:
    print(f"[{segment.start:.2f}s -> {segment.end:.2f}s] {segment.text}")
```

## Advanced Features
- Real-time transcription with callbacks
- Multiple output formats (txt, vtt, srt, csv)
- Voice activity detection
- GPU acceleration support
- CLI tool: `pwcpp`
- GUI interface: `pwcpp-gui`

## Key whisper.cpp Parameters
- `n_threads`: Number of threads for processing
- `language`: Target language (auto-detect if None)
- `translate`: Translate to English
- `print_progress`: Show progress during transcription
- `print_realtime`: Print segments in real-time

Source: https://github.com/absadiki/pywhispercpp
Documentation: https://absadiki.github.io/pywhispercpp/