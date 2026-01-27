# Wake Word Detection Libraries - 2025/2026 Research Report

## Executive Summary

This report analyzes the current landscape of wake word and keyword detection libraries suitable for integration into local Windows speech-to-text applications. The focus is on detecting voice commands (like "stop") during active recording, which requires low-latency, lightweight solutions that run entirely on-device.

## Current Landscape Overview

The wake word detection space has matured significantly since 2020, with several distinct approaches:

1. **Dedicated Wake Word Engines** - Purpose-built for detecting specific phrases
2. **Open Vocabulary Keyword Spotting** - ASR-based systems that can detect any phrase
3. **VAD-Enhanced Solutions** - Voice activity detection combined with lightweight recognition

Key industry trends (2024-2026):
- Shift toward fully synthetic training data (no manual audio collection needed)
- ONNX runtime becoming the standard for cross-platform deployment
- Increasing focus on privacy-first, offline-capable solutions
- Emergence of open-source alternatives rivaling commercial accuracy

## Library Comparison

### Comparison Table

| Library | License | Custom Words | Training Required | CPU Usage | Windows Support | Active Maintenance |
|---------|---------|--------------|-------------------|-----------|-----------------|-------------------|
| **openWakeWord** | Apache 2.0 | Yes | Yes (synthetic) | Low-Medium | Yes (ONNX) | Active |
| **Porcupine** | Commercial (free tier) | Yes | Console tool | Very Low | Yes | Active |
| **sherpa-onnx KWS** | Apache 2.0 | Yes | No (open vocab) | Low | Yes | Active |
| **Vosk + Plugin** | Apache 2.0 | Yes | No | Medium | Yes | Active |
| **RealtimeSTT** | MIT | Via backends | Depends | Varies | Yes | Active |
| **micro-wake-word** | Apache 2.0 | Yes | Yes | Ultra-low | No (ESP32) | Active |
| **Mycroft Precise** | Apache 2.0 | Yes | Yes | Low | Linux-focused | Abandoned (2024) |
| **Snowboy** | Apache 2.0 | Was Yes | Was Yes | Low | Was Yes | Abandoned (2022) |

### Detailed Analysis

---

### 1. openWakeWord

**Repository**: https://github.com/dscripka/openWakeWord

**Overview**: Open-source wake word detection framework with pre-trained models and support for training custom wake words using 100% synthetic speech data.

**Key Features**:
- Pre-trained models: "alexa", "hey mycroft", "hey jarvis", "hey rhasspy", "current weather", "timers"
- Training requires only text-to-speech generated audio
- Uses Google's speech embedding model as shared backbone
- Processes 80ms audio frames at 16kHz
- VAD integration available

**Performance**:
- Raspberry Pi 3 can run 15-20 models simultaneously
- Target: <5% false-reject, <0.5/hour false-accept
- Benchmarks show comparable or better accuracy than Porcupine for some wake words

**Windows Considerations**:
- Uses ONNX runtime on Windows (tflite not supported)
- Install: `pip install openwakeword`
- Requires: Python 3.8+, numpy, onnxruntime

**Pros**:
- Fully open source with no API keys or usage limits
- Excellent documentation and training notebooks
- Active development and community (Home Assistant ecosystem)
- Can train custom wake words in under 1 hour

**Cons**:
- English models only
- Requires ML knowledge for custom training
- Not suitable for microcontrollers
- Larger memory footprint than commercial alternatives

---

### 2. Picovoice Porcupine

**Repository**: https://github.com/Picovoice/porcupine

**Overview**: Commercial wake word engine with a free tier for small projects. Industry-leading accuracy and efficiency.

**Key Features**:
- Console-based custom wake word training (no ML knowledge needed)
- Multi-language support (9 languages)
- Pre-built wake words: "Alexa", "Hey Siri", "OK Google", etc.
- Cross-platform SDKs

**Performance**:
- Claims 97%+ detection rate with <1 false alarm per 10 hours
- 3.8% CPU usage on Raspberry Pi 3
- 11x more accurate than Snowboy in benchmarks

**Windows Considerations**:
- Native Windows support
- Install: `pip install pvporcupine`
- Requires access key (free registration)

**Licensing**:
- Free tier: Up to 3 active users/month
- Commercial: Starts at $6,000/year
- Requires online activation for access keys

**Pros**:
- Best-in-class accuracy and efficiency
- No ML expertise required for custom wake words
- Excellent documentation and support
- Multi-language support

**Cons**:
- Requires API key and online activation
- Free tier limited to 3 users
- Commercial use at scale requires paid license
- Vendor lock-in concerns

---

### 3. sherpa-onnx Keyword Spotting

**Repository**: https://github.com/k2-fsa/sherpa-onnx

**Overview**: Open vocabulary keyword spotting using next-gen Kaldi with ONNX runtime. Can detect any keyword without model retraining.

**Key Features**:
- Open vocabulary: define keywords in text file, no retraining
- Multi-language models available
- Integrated VAD support
- Full speech-to-text capabilities included

**Performance**:
- Lightweight models (e.g., 3.3M parameters)
- Real-time processing on consumer hardware
- Multiple language support

**Windows Considerations**:
- Native Windows x64 support
- Install: `pip install sherpa-onnx`
- Python 3.8-3.14 supported
- Latest version: 1.12.23 (January 2026)

**Pros**:
- No training required for custom keywords
- Change keywords at runtime via text file
- Comprehensive speech toolkit beyond just wake words
- Apache 2.0 license with no usage restrictions

**Cons**:
- Heavier than dedicated wake word engines
- Less optimized for single wake word detection
- More complex setup than alternatives

---

### 4. RealtimeSTT (with Wake Word Backends)

**Repository**: https://github.com/KoljaB/RealtimeSTT

**Overview**: Full-featured speech-to-text library with integrated wake word support via pluggable backends (Porcupine or openWakeWord).

**Key Features**:
- Multiple VAD options (WebRTC, Silero)
- Wake word backend selection
- Real-time streaming transcription
- Low-latency design

**Windows Considerations**:
- Full Windows support
- Supports both CPU and GPU acceleration
- Install: `pip install RealtimeSTT`

**Pros**:
- Complete solution combining STT and wake word
- Flexible backend selection
- Active development
- Good for rapid prototyping

**Cons**:
- Adds dependency layer
- Wake word quality depends on chosen backend
- Heavier than using wake word library directly

---

### 5. Vosk with Wake Word Plugin (OpenVoiceOS)

**Repository**: https://github.com/alphacep/vosk-api

**Overview**: Offline speech recognition toolkit that can be configured for keyword/wake word detection via vocabulary restriction.

**Key Features**:
- Restrict vocabulary to specific keywords
- Rule-based matching (contains, equals, starts, ends)
- Small model sizes (~50MB per language)
- Supports 20+ languages

**Windows Considerations**:
- Full Windows support
- Install: `pip install vosk`

**Pros**:
- Proven offline speech recognition
- Flexible keyword matching rules
- Multi-language support
- Small model footprint

**Cons**:
- Not purpose-built for wake word detection
- May have higher false positive rates
- Requires model download

---

### 6. TEN VAD (Voice Activity Detection)

**Repository**: https://github.com/TEN-framework/ten-vad

**Overview**: While not a wake word detector, TEN VAD offers state-of-the-art voice activity detection that can complement wake word systems or serve as a pre-filter.

**Performance**:
- Superior to Silero VAD and WebRTC VAD
- 306KB library size (Linux)
- RTF: 0.015 on Windows i7
- Rapid speech-to-non-speech transition detection

**Windows Considerations**:
- Windows x64 support
- Python bindings available (Linux optimized, Windows via prebuilt-lib)
- Apache 2.0 license

**Relevance**: Could be used to detect end-of-speech more accurately than pure wake word detection for "stop" command scenarios.

---

### 7. micro-wake-word

**Repository**: https://github.com/OHF-Voice/micro-wake-word

**Overview**: TensorFlow-based wake word training framework optimized for microcontrollers (ESP32). Part of the Home Assistant ecosystem.

**Key Features**:
- Synthetic training data generation
- Optimized for ESP32-class devices
- Version 2 with improved accuracy
- Can run 3 wake words on standard ESP32

**Windows Considerations**:
- Training runs on Windows
- Inference designed for embedded devices, not Windows
- Not suitable for Windows desktop deployment

**Relevance**: Primarily useful for embedded/IoT projects, not Windows desktop apps.

---

## Recommendations for Windows Desktop Speech-to-Text App

### Primary Recommendation: openWakeWord

For a local Windows speech-to-text application needing voice command detection during recording:

**Why openWakeWord**:
1. **Fully Open Source**: No API keys, no usage limits, Apache 2.0 license
2. **Windows Compatible**: Uses ONNX runtime which works well on Windows
3. **Custom Training**: Can train "stop" or any command word with synthetic data
4. **Integration**: Already popular in the voice assistant community
5. **Performance**: Sufficient for real-time detection on desktop hardware
6. **Active Development**: Regular updates and active community

**Implementation Approach**:
```python
from openwakeword.model import Model

# Load pre-trained or custom model
model = Model(wakeword_models=["path/to/stop_model.onnx"])

# Process audio frames (80ms at 16kHz)
prediction = model.predict(audio_frame)
if prediction["stop"] > threshold:
    # Trigger stop action
```

### Secondary Recommendation: sherpa-onnx

If you need flexibility to change command words without retraining:

**Why sherpa-onnx**:
1. **Open Vocabulary**: Define keywords in text file
2. **No Training Required**: Works out of the box
3. **Windows Native**: Excellent Windows support
4. **Comprehensive**: Full speech toolkit if needed later

### Alternative: Porcupine (if licensing acceptable)

If the free tier limitations (3 users) are acceptable:

**Why Porcupine**:
1. **Easiest Setup**: Console-based training, no ML knowledge
2. **Best Accuracy**: Industry-leading performance
3. **Lowest CPU**: Most efficient option

### Not Recommended

- **Mycroft Precise**: Project abandoned in 2024
- **Snowboy**: Discontinued in 2022
- **micro-wake-word**: Designed for microcontrollers, not Windows

## Implementation Considerations

### For "Stop Command" Detection During Recording

The use case of detecting a voice command to stop recording has specific requirements:

1. **Low Latency**: Detection must be fast enough to feel responsive
2. **High Precision**: False positives interrupt the user
3. **Robustness**: Must work alongside ongoing speech

**Recommended Architecture**:
```
Audio Stream → VAD Filter (TEN VAD/Silero) → Wake Word Detection (openWakeWord)
                                          ↓
                                    Command Detected → Stop Recording
```

Using VAD as a pre-filter reduces false positives and CPU usage by only running wake word detection on speech segments.

### Model Training Considerations

For custom commands like "stop recording" or "cancel":
- openWakeWord: Generate ~3000 synthetic samples using TTS, train for ~1 hour
- Porcupine: Use console to create model (requires free account)
- sherpa-onnx: No training needed, just add to keywords file

## Links and Resources

### Primary Repositories
- openWakeWord: https://github.com/dscripka/openWakeWord
- Porcupine: https://github.com/Picovoice/porcupine
- sherpa-onnx: https://github.com/k2-fsa/sherpa-onnx
- TEN VAD: https://github.com/TEN-framework/ten-vad
- RealtimeSTT: https://github.com/KoljaB/RealtimeSTT
- Vosk: https://github.com/alphacep/vosk-api
- micro-wake-word: https://github.com/OHF-Voice/micro-wake-word

### Training Resources
- openWakeWord Training Notebook: https://github.com/dscripka/openWakeWord/blob/main/notebooks/training_models.ipynb
- Picovoice Console: https://console.picovoice.ai/

### Benchmarks and Comparisons
- Picovoice Wake Word Benchmark: https://github.com/Picovoice/wake-word-benchmark
- openWakeWord Accuracy Comparison: https://github.com/dscripka/openWakeWord#performance-and-evaluation

### Related Research
- EdgeSpot (2025): https://arxiv.org/html/2601.16316
- Small-Footprint KWS Review (2025): https://arxiv.org/abs/2506.11169
- Howl Open Source Wake Word: https://arxiv.org/abs/2008.09606

---

## TEN Framework

### Overview

The [TEN Framework](https://github.com/TEN-framework/ten-framework) (Transformative Extensions Network) is an open-source framework for building real-time multimodal conversational AI agents. Since this project already uses `ten-vad` for voice activity detection, understanding the broader TEN ecosystem is relevant for potential integration opportunities.

### TEN Ecosystem Components

The TEN ecosystem consists of several open-source projects:

| Component | Purpose | Status |
|-----------|---------|--------|
| **TEN Framework** | Core framework for building voice agents | Active |
| **TEN VAD** | Voice activity detection (already used by this project) | Active |
| **TEN Turn Detection** | Full-duplex dialogue turn management | Active |
| **TEN Agent** | Reference implementation with multiple extensions | Active |
| **TMAN Designer** | Visual workflow creation tool | Active |
| **TEN Portal** | Documentation and resources | Active |

### Does TEN Framework Have Wake Word Detection?

**No.** After thorough research, TEN Framework does not currently offer wake word or keyword detection capabilities. The framework focuses on:

- Voice Activity Detection (VAD)
- Turn detection for conversational flow
- Real-time audio streaming (RTC/WebSocket)
- Integration with third-party ASR, LLM, and TTS services

Wake word detection would need to be implemented using a separate library (openWakeWord, Porcupine, or sherpa-onnx as recommended earlier in this report).

### TEN Framework Audio/Speech Modules

**Built-in Modules:**
- **TEN VAD**: High-performance voice activity detector with 0.0050 RTF on high-end devices
- **TEN Turn Detection**: 98% accuracy in natural conversational turn-taking, supports English and Chinese

**Extension-Based Integrations (requires third-party API keys):**
- **ASR/STT**: Deepgram integration (cloud-based)
- **TTS**: ElevenLabs, FishAudio, Cartesia (cloud-based)
- **LLM**: OpenAI, Deepseek, Gemini (cloud-based)
- **RTC**: Agora for real-time communication
- **Speaker Diarization**: Real-time speaker identification

### Integration Benefits for This Project

**Currently Using:**
- `ten-vad` for voice activity detection during recording

**Potential Additional Benefits:**
1. **TEN Turn Detection**: Could improve end-of-speech detection for more natural recording stops. The module classifies utterances into "finished", "wait", and "unfinished" states using semantic analysis rather than simple silence detection.

2. **Unified Ecosystem**: Both TEN VAD and TEN Turn Detection are designed to work together, potentially offering better integration than mixing different VAD/turn detection solutions.

**Limitations:**
- TEN's ASR/TTS integrations are cloud-based services requiring API keys, not suitable for a fully local speech-to-text application
- No wake word detection module available
- Turn Detection requires a 7B parameter model (Qwen2.5-7B), which may be too heavy for a lightweight desktop application

### Recent Developments (2025-2026)

- **June 2025**: TEN VAD ONNX model and preprocessing code open-sourced
- **July 2025**: TEN VAD integrated into sherpa-onnx for enhanced ASR experience
- **November 2025**: Added Go and Java bindings for TEN VAD across multiple platforms
- **January 2026**: Active development continues with PR challenges and new features

### Recommendation

For this project's wake word/stop command detection needs, TEN Framework is **not the solution**. Continue using `ten-vad` for VAD (excellent choice), but implement wake word detection using one of the dedicated libraries recommended in this report:

1. **openWakeWord** (recommended): Fully open-source, ONNX-based, can train custom "stop" command
2. **sherpa-onnx**: Open vocabulary keyword spotting without retraining
3. **Porcupine**: Best accuracy if free tier limitations (3 users) are acceptable

The TEN Turn Detection module could be valuable for improving end-of-speech detection, but its model size (7B parameters) may be prohibitive for a lightweight desktop application.

### Links

- TEN Framework: https://github.com/TEN-framework/ten-framework
- TEN VAD: https://github.com/TEN-framework/ten-vad
- TEN Turn Detection: https://github.com/TEN-framework/ten-turn-detection
- TEN Agent: https://github.com/TEN-framework/TEN-Agent
- Official Website: https://theten.ai/

---

*Report compiled: January 2026*
*Focus: Windows desktop speech-to-text application with voice command detection*
