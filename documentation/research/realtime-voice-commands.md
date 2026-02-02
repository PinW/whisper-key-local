# Real-Time Voice Command System Research

## Executive Summary

This research investigates the feasibility of building an advanced voice command system that goes beyond simple wake words - one that can understand intent semantically, similar to Claude Code's skill system but triggered by voice. The goal is real-time, low-latency, local/offline processing on CPU.

### Key Findings

1. **Real-time STT is achievable on CPU** - Models like Moonshine (27M params), Distil-Whisper, and sherpa-onnx provide practical streaming STT on consumer CPUs with latencies of 1-3 seconds.

2. **Intent understanding has multiple viable paths** - Embedding-based similarity matching (fastest), small fine-tuned classifiers (SetFit, DistilBERT), or small LLMs (Phi-3-mini, TinyLlama) can all run locally on CPU.

3. **Sub-500ms end-to-end is challenging but possible** - Requires careful architecture design, streaming pipelines, optimized VAD, and lightweight models. Production systems typically achieve 600-800ms.

4. **The "Claude Code Skills" pattern is implementable** - A hybrid approach combining fast embedding-based command matching with a small LLM fallback for semantic understanding offers the best balance.

5. **CPU-only is viable for command recognition** - Full conversational AI may need GPU, but voice command recognition with 10-50 commands is well within CPU capability.

---

## Table of Contents

1. [Real-Time Speech-to-Text Options](#1-real-time-speech-to-text-options)
2. [Intent Understanding / NLU](#2-intent-understanding--nlu)
3. [End-to-End Solutions](#3-end-to-end-solutions)
4. [The "Claude Code Skills" Pattern](#4-the-claude-code-skills-pattern)
5. [CPU Feasibility Analysis](#5-cpu-feasibility-analysis)
6. [Emerging Technologies](#6-emerging-technologies)
7. [Architecture Recommendations](#7-architecture-recommendations)
8. [Comparison Tables](#8-comparison-tables)
9. [Implementation Roadmap](#9-implementation-roadmap)
10. [References & Resources](#10-references--resources)

---

## 1. Real-Time Speech-to-Text Options

### 1.1 Streaming STT Landscape

| Model/Framework | Parameters | CPU Latency | WER | Streaming | Best For |
|-----------------|------------|-------------|-----|-----------|----------|
| **Moonshine Tiny** | 27M | ~200ms/chunk | ~10% | Yes | Edge/embedded |
| **Moonshine Base** | 62M | ~400ms/chunk | ~8% | Yes | Desktop CPU |
| **Distil-Whisper small.en** | 166M | ~500ms | ~5% | Via wrapper | Resource-constrained |
| **Distil-Whisper large-v3** | 756M | ~1s | ~4% | Via wrapper | Balanced |
| **faster-whisper (base)** | 74M | ~800ms | ~7% | Via whisper_streaming | General use |
| **faster-whisper (turbo)** | 809M | ~600ms | ~5% | Via whisper_streaming | Speed priority |
| **Vosk (small)** | ~50M | ~100ms | ~12% | Native | True real-time |
| **sherpa-onnx** | Various | ~150ms | ~8% | Native | Production edge |

### 1.2 Whisper Streaming Solutions

**whisper_streaming (ufal/whisper_streaming)**
- State-of-the-art streaming implementation for Whisper
- Self-adaptive latency based on source complexity
- Achieves 3.3 seconds average latency on long-form speech
- Being superseded by **SimulStreaming** (faster, higher quality)
- Supports faster-whisper, whisper_timestamped, OpenAI API, mlx-whisper backends

**WhisperLiveKit**
- Docker-ready deployment
- Integrates SimulStreaming and WhisperStreaming research
- Works on both CPU and GPU environments

**WhisperFlow (MobiSys '25)**
- Research system achieving ~1 second per-word latency on entry-level MacBook Air
- CPU/GPU pipelining for optimal performance
- Falls back to CPU-only with higher latency

### 1.3 Non-Whisper Alternatives

**Vosk**
- True streaming with native support
- Optimized for edge and offline use
- Runs efficiently on CPU without GPU
- Supports mobile platforms, Raspberry Pi, embedded systems
- Research shows latency reduced from 3.5s to 1.2s with optimization
- 5.2% WER for American English (struggles with accents)

**sherpa-onnx (k2-fsa)**
- Production-ready with 100% offline operation
- Supports 12 programming languages
- INT8 quantized models for edge deployment
- Latest version (Jan 2026) supports CPython 3.14
- Streaming zipformer models available for multiple languages

**Moonshine**
- 5-15x faster than Whisper with same or better WER
- Processes variable-length audio (unlike Whisper's 30s chunks)
- ONNX runtime recommended for Raspberry Pi
- New "Flavors" variants (Sept 2025) for underrepresented languages
- 48% lower error rates than Whisper Tiny

### 1.4 Accuracy vs Latency Tradeoff

There is a fundamental tradeoff:
- **Fastest** (100-200ms): Vosk, sherpa-onnx with small models - WER 10-15%
- **Balanced** (500ms-1s): Moonshine Base, Distil-Whisper small - WER 5-8%
- **Most Accurate** (1-3s): Whisper Large V3, Parakeet TDT - WER 3-5%

For voice commands with a limited vocabulary, higher WER is acceptable because:
1. Commands are predictable and can be constrained
2. Post-processing can correct common errors
3. Intent matching can be fuzzy

---

## 2. Intent Understanding / NLU

### 2.1 Approaches Overview

| Approach | Latency | Accuracy | Training Data | Memory | Best For |
|----------|---------|----------|---------------|--------|----------|
| **Keyword/Rule-based** | <10ms | Variable | None | <1MB | Exact phrases |
| **Embedding similarity** | 10-50ms | Good | Examples | ~100MB | Semantic matching |
| **Fine-tuned classifier** | 20-100ms | High | ~100 samples | ~200MB | Fixed intents |
| **SetFit few-shot** | 30ms | High | 8 per class | ~100MB | Rapid prototyping |
| **Small LLM (1-3B)** | 200-500ms | Excellent | None/Few | 1-4GB | Flexible understanding |

### 2.2 Embedding-Based Similarity Matching

**Static Embedding Models (2025)**
- sentence-transformers/static-retrieval-mrl-en-v1
- sentence-transformers/static-similarity-mrl-multilingual-v1
- **100-400x faster on CPU** than attention-based models
- Reaches 85% of state-of-the-art performance
- Ideal for intent matching with predefined command embeddings

**How it works:**
1. Pre-compute embeddings for all command phrases/variations
2. Embed incoming transcription
3. Cosine similarity to find closest command
4. Threshold-based acceptance

**Example architecture:**
```
User says: "nevermind, stop that"
           ↓
    [STT] → "never mind stop that"
           ↓
    [Embed] → vector(384)
           ↓
    [Similarity Search]
           ↓
    Match: "cancel_recording" (0.87 similarity)
```

### 2.3 Fine-Tuned Classifiers

**DistilBERT**
- 66M parameters, 6 transformer layers
- 60% faster inference than BERT
- 10-20ms median latency with optimizations (quantized, ONNX)
- 97% of BERT's performance with 40% fewer parameters

**TinyBERT**
- 14.5M parameters
- Two-stage training: distillation + fine-tuning
- Even faster than DistilBERT

**Fast DistilBERT on CPUs (Intel)**
- Hardware-aware pruning + quantization
- 4.1x speedup over ONNX Runtime on AWS CPUs
- <1% accuracy loss on benchmark tasks

### 2.4 SetFit for Few-Shot Intent Classification

SetFit enables training effective classifiers with just 8 examples per intent:

**Advantages:**
- No prompts or verbalizers needed
- Trains in 30 seconds on GPU, minutes on CPU
- Multilingual via any Sentence Transformer
- Competitive with full fine-tuning at fraction of data

**Performance:**
- With 8 labeled examples: competitive with RoBERTa trained on 3k examples
- SetFit ModernBERT (2025): up to 50% improvement over baselines

**For voice commands:**
- Define 8-10 example phrases per command
- Train lightweight classifier
- Sub-50ms inference on CPU

### 2.5 Small Language Models for Intent

**Phi-3-mini (Microsoft)**
- 3.8B parameters
- Quantized to 4-bit: 1.8GB memory
- 12+ tokens/second on iPhone A16 (native)
- Rivals Mixtral 8x7B and GPT-3.5 quality

**TinyLlama (1.1B)**
- Runs on CPU-only systems via GGUF format
- Suitable for voice assistant "brain"
- Can handle flexible intent understanding

**llama.cpp CPU Performance:**
- For 1B models on iPhone 15 Pro: 17 tok/s (CPU) vs 12.8 tok/s (GPU)
- Smaller models often faster on CPU than GPU
- Memory bandwidth is the bottleneck, not compute

### 2.6 Traditional NLU Libraries

**Rasa NLU**
- Open source, self-hosted
- DIET model for intent + entity extraction
- Can be computationally expensive
- Lighter alternatives: NaiveBayesClassifier, FastTextFeaturizer

**Rhasspy (fsticuffs)**
- Recognizes only trained sentences
- Trains and performs recognition in milliseconds
- Best for constrained command sets

**Picovoice Rhino**
- Speech-to-intent (bypasses text)
- Runs on IoT devices and servers
- Commercial with free tier (100 MAU)

---

## 3. End-to-End Solutions

### 3.1 Speech-to-Intent (Skip Transcription)

**Picovoice Platform**
- Porcupine (wake word) + Rhino (speech-to-intent)
- Infers intent directly from speech
- 97%+ accuracy, <1 false alarm per 10 hours
- Free tier: 100 Monthly Active Users
- Commercial: starts at $6000

**SpeechBrain SLU**
- Spoken Language Understanding recipe
- 99.60% accuracy on Fluent Speech Commands
- Direct audio → intent mapping

**Fluent Speech Commands Dataset**
- Standard benchmark for speech-to-intent
- Commands like "turn on the lights", "set volume to 50"

### 3.2 End-to-End Voice Agent Architectures

**Cascaded Pipeline (Traditional)**
```
Voice → STT → LLM → TTS → Voice
```
- Maximum flexibility and reliability
- Higher cumulative latency (1-3 seconds)
- Each component can be optimized independently

**Speech-to-Speech (Emerging)**
```
Voice → S2S Model → Voice
```
- 200-300ms latency achievable
- Less mature, prone to hallucinations
- Limited function calling capability

**Hybrid Approach (Recommended)**
```
Voice → Fast S2S for simple commands
     → Full pipeline for complex queries
```
- Best of both worlds
- Supervisor model routes requests

### 3.3 Research Frameworks

**SpeechBrain 1.0**
- 200+ recipes for speech/audio/language tasks
- 100+ models on Hugging Face
- Efficient fine-tuning for speech self-supervised models

**ESPnet**
- End-to-end speech processing toolkit
- Streaming Transformer ASR demos
- Local inference support

**NVIDIA NeMo**
- Industrial-grade speech toolkit
- Parakeet TDT: #1 on HuggingFace ASR leaderboard
- 3380x real-time factor on batch processing

---

## 4. The "Claude Code Skills" Pattern

### 4.1 Requirements Breakdown

The goal: voice input that matches against available "skills/commands" with both exact phrases and semantic understanding.

| Requirement | Challenge | Solution |
|-------------|-----------|----------|
| Real-time streaming | Whisper is batch-based | Use whisper_streaming or Vosk |
| Intent matching | Need semantic understanding | Embedding similarity + LLM fallback |
| Both exact & fuzzy | Different approaches needed | Hybrid system |
| <500ms response | Multiple pipeline stages | Streaming + caching + optimization |

### 4.2 Proposed Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                    Voice Command System                      │
├─────────────────────────────────────────────────────────────┤
│                                                              │
│  ┌──────────┐   ┌──────────┐   ┌──────────────────────────┐ │
│  │   VAD    │──>│ Streaming │──>│    Intent Matching       │ │
│  │ (TEN-VAD)│   │   STT    │   │                          │ │
│  └──────────┘   │(Moonshine)│   │  ┌────────────────────┐ │ │
│                 └──────────┘   │  │ Tier 1: Exact Match │ │ │
│                                │  │ (keyword lookup)    │ │ │
│                                │  └─────────┬──────────┘ │ │
│                                │            │ no match   │ │
│                                │            ▼            │ │
│                                │  ┌────────────────────┐ │ │
│                                │  │ Tier 2: Embedding  │ │ │
│                                │  │ Similarity (0.8+)  │ │ │
│                                │  └─────────┬──────────┘ │ │
│                                │            │ uncertain  │ │
│                                │            ▼            │ │
│                                │  ┌────────────────────┐ │ │
│                                │  │ Tier 3: Small LLM  │ │ │
│                                │  │ Intent Extraction  │ │ │
│                                │  └────────────────────┘ │ │
│                                └──────────────────────────┘ │
│                                            │                │
│                                            ▼                │
│                                    ┌──────────────┐         │
│                                    │   Execute    │         │
│                                    │   Command    │         │
│                                    └──────────────┘         │
└─────────────────────────────────────────────────────────────┘
```

### 4.3 Component Selection

**VAD: TEN-VAD**
- 32% lower RTF than Silero VAD
- Superior precision on speech-to-non-speech transitions
- Cross-platform C compatibility
- ONNX model open-sourced (June 2025)

**STT: Moonshine Base or sherpa-onnx**
- Moonshine: Best accuracy/speed ratio for edge
- sherpa-onnx: Most deployment flexibility

**Tier 1 - Exact Match:**
- Simple dictionary lookup
- Handles canonical phrases: "cancel recording", "stop transcription"
- <1ms latency

**Tier 2 - Embedding Similarity:**
- Static embedding model for speed
- Pre-computed command embeddings
- Cosine similarity with 0.8 threshold
- 10-30ms latency

**Tier 3 - LLM Fallback:**
- Phi-3-mini or TinyLlama (quantized)
- Only invoked for ambiguous inputs
- Structured output: {intent: string, confidence: float}
- 200-500ms latency

### 4.4 Example Command Definitions

```yaml
commands:
  cancel_recording:
    canonical: "cancel recording"
    examples:
      - "stop recording"
      - "nevermind"
      - "abort that"
      - "cancel"
      - "forget it"
    semantic_hints: "user wants to stop current recording without saving"

  start_recording:
    canonical: "start recording"
    examples:
      - "begin recording"
      - "record this"
      - "start listening"
      - "transcribe"
    semantic_hints: "user wants to begin voice capture"
```

### 4.5 Latency Budget

Target: 500ms end-to-end

| Component | Budget | Achievable |
|-----------|--------|------------|
| VAD detection | 50ms | Yes (TEN-VAD ~16ms frames) |
| End-of-speech | 150ms | Yes (ML-based EOU) |
| STT streaming | 200ms | Yes (Moonshine) |
| Intent matching | 100ms | Yes (Tier 1+2) |
| **Total** | **500ms** | **Achievable for most commands** |

For Tier 3 LLM fallback, budget extends to 800-1000ms.

---

## 5. CPU Feasibility Analysis

### 5.1 What's Achievable on Modern Consumer CPUs

**Intel/AMD Desktop (8+ cores, 2023+)**
- Whisper small: ~3x real-time
- Whisper base: ~5x real-time
- Moonshine tiny: ~15x real-time
- DistilBERT inference: 10-20ms
- Embedding similarity: <10ms

**Memory Requirements**
| Component | RAM Usage |
|-----------|-----------|
| Moonshine Tiny (ONNX) | ~190MB |
| Moonshine Base (ONNX) | ~400MB |
| Static embedding model | ~100MB |
| DistilBERT classifier | ~250MB |
| Phi-3-mini (4-bit) | ~1.8GB |
| **Total (minimal)** | **~500MB** |
| **Total (with LLM)** | **~2.5GB** |

### 5.2 CPU vs GPU: When GPU Helps

| Task | CPU Viable? | GPU Benefit |
|------|-------------|-------------|
| Whisper tiny/base | Yes | 2-4x speedup |
| Whisper large | Slow | Essential |
| Embedding computation | Yes | Minor benefit |
| Small classifier | Yes | Negligible |
| LLM <3B params | Yes | 2-3x speedup |
| LLM >7B params | Slow | Essential |

**Key insight:** For voice command recognition (not full conversation), CPU is entirely viable.

### 5.3 Optimization Techniques

**ONNX Runtime**
- 2x performance improvement over PyTorch
- Up to 5x speedup with OpenVINO backend
- Cross-platform deployment

**Quantization**
- INT8 quantization: ~50% size reduction, minimal accuracy loss
- 4-bit for LLMs: 4x memory reduction

**Model Selection**
- Prefer models designed for edge: Moonshine, TinyBERT, static embeddings
- Avoid "scaling law" models designed for GPU

### 5.4 Real-World Benchmarks

**DistilBERT on CPU (production reports)**
- Roblox: <20ms median latency for BERT-tiny classification
- Single modern CPU core: tens of requests/second
- Linear scaling with core count

**llama.cpp Small Models**
- 1B params on Raspberry Pi 5: viable but slow
- 1B params on modern desktop CPU: 10-20 tok/s
- Memory bandwidth is the bottleneck

---

## 6. Emerging Technologies

### 6.1 2024-2026 Developments

**On-Device AI Shift**
- By 2026, 80% of AI inference expected to happen locally
- Hardware: 70+ TOPS NPUs, 8-24GB unified memory
- Sub-200ms response times becoming standard

**Hybrid Voice AI Architecture**
- Cloud for complex queries, device for trivial (80%)
- Minimizes expensive cloud LLM usage
- Sensitive data never leaves device

**NPU Acceleration**
- Windows 11 Copilot+ requires 40 TOPS
- AMD Ryzen AI, Intel OpenVINO, Qualcomm SNPE
- Apple M-series Neural Engine excels at speech
- Khronos working on standardization

### 6.2 Notable Projects

**SimulStreaming (2025)**
- Successor to whisper_streaming
- Much faster and higher quality
- By Dominik Machaček (WhisperStreaming author)

**Moonshine Flavors (Sept 2025)**
- Specialized 27M models for underrepresented languages
- 48% lower error than Whisper Tiny
- Matches Whisper Medium (28x larger)

**WhisperKit (Apple)**
- On-device ASR with billion-scale transformers
- Optimized for Apple Silicon

**NVIDIA Canary Qwen 2.5B**
- #1 on HuggingFace Open ASR Leaderboard (5.63% WER)
- Speech-Augmented Language Model (SALM) architecture
- Combines ASR with LLM capabilities

### 6.3 Trends to Watch

1. **Speech-to-Speech models** gaining traction but not production-ready
2. **Small Language Models** (SLMs) replacing LLMs for specific tasks
3. **Semantic VAD** reducing end-of-speech detection latency by 53%
4. **Function calling** becoming standard in small models
5. **On-device training** emerging with Apple MLX framework

---

## 7. Architecture Recommendations

### 7.1 Minimum Viable Version

**For immediate implementation with current whisper-key:**

```
┌────────────────────────────────────────────────┐
│         MVP Voice Command System               │
├────────────────────────────────────────────────┤
│                                                │
│  Existing faster-whisper transcription         │
│              ↓                                 │
│  Post-process text with:                       │
│    1. Exact keyword matching                   │
│    2. Sentence-transformers similarity         │
│              ↓                                 │
│  Execute matched command                       │
│                                                │
└────────────────────────────────────────────────┘
```

**Components:**
- STT: Existing faster-whisper setup
- Intent: sentence-transformers/all-MiniLM-L6-v2 (~80MB)
- Matching: Pre-computed embeddings for ~10-20 commands

**Latency:** ~1-2 seconds (existing transcription + <100ms intent)

**Memory:** +100MB for embeddings

### 7.2 Optimized Version

**For sub-500ms latency:**

```
┌────────────────────────────────────────────────┐
│       Optimized Voice Command System           │
├────────────────────────────────────────────────┤
│                                                │
│  TEN-VAD for speech detection                  │
│              ↓                                 │
│  Streaming STT (Moonshine via ONNX)            │
│              ↓                                 │
│  Tiered intent matching:                       │
│    Tier 1: Keyword lookup (<1ms)               │
│    Tier 2: Static embeddings (<30ms)           │
│              ↓                                 │
│  Execute matched command                       │
│                                                │
└────────────────────────────────────────────────┘
```

**Components:**
- VAD: TEN-VAD (ONNX)
- STT: Moonshine Base (ONNX, ~400MB)
- Intent: static-similarity-mrl-multilingual-v1 (~100MB)

**Latency:** 300-500ms typical

**Memory:** ~600MB total

### 7.3 Full-Featured Version

**For semantic understanding of any phrasing:**

```
┌────────────────────────────────────────────────┐
│      Full-Featured Voice Command System        │
├────────────────────────────────────────────────┤
│                                                │
│  TEN-VAD + Semantic end-of-speech              │
│              ↓                                 │
│  Streaming STT (sherpa-onnx or Moonshine)      │
│              ↓                                 │
│  Three-tier intent matching:                   │
│    Tier 1: Keyword lookup                      │
│    Tier 2: Embedding similarity                │
│    Tier 3: Phi-3-mini LLM (4-bit quantized)    │
│              ↓                                 │
│  Execute command with extracted parameters     │
│                                                │
└────────────────────────────────────────────────┘
```

**Components:**
- VAD: TEN-VAD
- STT: sherpa-onnx streaming
- Intent Tier 1-2: Same as optimized
- Intent Tier 3: Phi-3-mini via llama.cpp (4-bit, ~1.8GB)

**Latency:**
- Tier 1-2: 300-500ms
- Tier 3: 800-1200ms

**Memory:** ~2.5GB total

### 7.4 Windows Desktop Specific Considerations

1. **ONNX Runtime** is the recommended inference engine for Windows
2. **DirectML** execution provider for Windows GPU acceleration
3. **Consider NPU** if targeting Windows 11 Copilot+ PCs
4. **PortAudio** already bundled for audio capture
5. **Threading** - use dedicated threads for VAD, STT, and intent

---

## 8. Comparison Tables

### 8.1 STT Model Comparison

| Model | Size | CPU Latency | WER (English) | Streaming | License |
|-------|------|-------------|---------------|-----------|---------|
| Vosk small-en | ~50MB | ~100ms | 12% | Native | Apache 2.0 |
| Moonshine Tiny | 190MB | ~200ms | 10% | Native | MIT |
| Moonshine Base | 400MB | ~400ms | 8% | Native | MIT |
| sherpa-onnx (zipformer) | ~100MB | ~150ms | 8% | Native | Apache 2.0 |
| Distil-Whisper small.en | 166MB | ~500ms | 5% | Via wrapper | MIT |
| faster-whisper base | 150MB | ~800ms | 7% | Via wrapper | MIT |
| Whisper large-v3-turbo | ~1.6GB | ~600ms (GPU) | 5% | Via wrapper | MIT |

### 8.2 Intent Classification Comparison

| Approach | Setup Time | Inference | Accuracy | Flexibility | Memory |
|----------|------------|-----------|----------|-------------|--------|
| Keyword matching | Minutes | <1ms | Perfect for exact | None | <1MB |
| Static embeddings | Minutes | 10-30ms | Good | Moderate | ~100MB |
| SetFit (8 examples/class) | 30 seconds | ~30ms | High | Moderate | ~100MB |
| DistilBERT fine-tuned | Hours | 20ms | High | Fixed intents | ~250MB |
| Phi-3-mini (4-bit) | None | 200-500ms | Excellent | Full | ~1.8GB |

### 8.3 VAD Comparison

| VAD | RTF (CPU) | Accuracy (TPR@5%FPR) | Latency | License |
|-----|-----------|----------------------|---------|---------|
| WebRTC VAD | Very fast | 50% | <10ms | BSD |
| Silero VAD | Fast | 87.7% | ~100ms delay | MIT |
| TEN-VAD | 32% faster than Silero | 98.9% | ~16ms frames | MIT |
| Cobra (Picovoice) | Fast | 98.9% | Low | Commercial |

### 8.4 End-to-End Latency Comparison

| Architecture | Typical Latency | Best Case | Components |
|--------------|-----------------|-----------|------------|
| Cloud ASR + Cloud LLM | 2-5 seconds | 1.5s | Network dependent |
| Local Whisper + embeddings | 1-2 seconds | 800ms | CPU viable |
| Streaming STT + embeddings | 300-600ms | 250ms | CPU viable |
| Speech-to-Intent (Picovoice) | 200-400ms | 150ms | Commercial |
| Optimized local pipeline | 400-800ms | 300ms | CPU viable |

---

## 9. Implementation Roadmap

### Phase 1: MVP (1-2 weeks)

**Goal:** Add command recognition to existing whisper-key

**Tasks:**
1. Define initial command set (10-15 commands)
2. Integrate sentence-transformers for embedding computation
3. Pre-compute command embeddings on startup
4. Add post-transcription intent matching
5. Wire up command execution

**Expected Latency:** 1-2 seconds (limited by existing transcription)

### Phase 2: Optimization (2-4 weeks)

**Goal:** Sub-500ms latency for most commands

**Tasks:**
1. Replace/augment STT with Moonshine or sherpa-onnx
2. Integrate TEN-VAD for faster speech detection
3. Implement streaming transcription
4. Add keyword-based fast path
5. Optimize embedding model (static embeddings)

**Expected Latency:** 300-500ms

### Phase 3: Semantic Understanding (4-6 weeks)

**Goal:** Handle any natural phrasing

**Tasks:**
1. Integrate Phi-3-mini or TinyLlama via llama.cpp
2. Implement tiered matching architecture
3. Add parameter extraction for complex commands
4. Fine-tune/customize for domain-specific commands
5. Implement confidence scoring and fallback handling

**Expected Latency:** 300ms (simple) to 1s (complex)

### Phase 4: Production Polish (ongoing)

**Tasks:**
1. User customization of commands/phrases
2. Learning from user corrections
3. Multi-language support
4. NPU acceleration for supported hardware
5. Performance profiling and optimization

---

## 10. References & Resources

### Key Projects

| Project | URL | Description |
|---------|-----|-------------|
| whisper_streaming | https://github.com/ufal/whisper_streaming | Real-time Whisper streaming |
| Moonshine | https://github.com/moonshine-ai/moonshine | Fast edge ASR |
| sherpa-onnx | https://github.com/k2-fsa/sherpa-onnx | Production speech toolkit |
| TEN-VAD | https://github.com/TEN-framework/ten-vad | Low-latency VAD |
| faster-whisper | https://github.com/SYSTRAN/faster-whisper | CTranslate2 Whisper |
| sentence-transformers | https://github.com/huggingface/sentence-transformers | Embedding models |
| SetFit | https://github.com/huggingface/setfit | Few-shot classification |
| llama.cpp | https://github.com/ggml-org/llama.cpp | CPU LLM inference |
| Rhasspy | https://rhasspy.readthedocs.io/ | Open source voice assistant |
| SpeechBrain | https://github.com/speechbrain/speechbrain | Speech processing toolkit |

### Models on Hugging Face

- `sentence-transformers/static-similarity-mrl-multilingual-v1` - Fast CPU embeddings
- `distil-whisper/distil-large-v3` - Optimized Whisper
- `microsoft/phi-3-mini-4k-instruct` - Small capable LLM
- `TEN-framework/ten-vad` - VAD model
- `nvidia/parakeet-tdt-0.6b-v3` - State-of-art ASR

### Research Papers

1. WhisperFlow: Speech Foundation Models in Real Time (MobiSys '25)
2. Flavors of Moonshine: Tiny Specialized ASR Models for Edge Devices (2025)
3. Semantic VAD: Low-Latency Voice Activity Detection for Speech Interaction
4. SetFit: Efficient Few-Shot Learning Without Prompts
5. Fast DistilBERT on CPUs (NeurIPS 2022)
6. Small Models, Big Results: Superior Intent Extraction through Decomposition (Google, 2025)

### Commercial Solutions (for reference)

| Company | Product | Offering |
|---------|---------|----------|
| Picovoice | Porcupine + Rhino | Wake word + speech-to-intent |
| Speechmatics | Flow On-Premise | Full voice AI stack |
| Vivoka | Voice AI | Enterprise on-device |
| Deepgram | Nova-2 | Fast cloud ASR |
| AssemblyAI | Universal-2 | High-accuracy ASR |

---

## Conclusion

Building a "Claude Code Skills"-like voice command system is achievable today with local, CPU-only processing. The key insights:

1. **Don't need perfect transcription** - Command recognition can tolerate higher WER
2. **Tiered matching is essential** - Fast path for common cases, slow path for edge cases
3. **Streaming changes everything** - Batch transcription is too slow for <500ms
4. **Small models outperform expectations** - Moonshine, static embeddings, SetFit prove this
5. **LLMs are optional** - Only needed for truly flexible semantic understanding

The recommended approach for whisper-key:
- Start with MVP using existing faster-whisper + embedding similarity
- Optimize with Moonshine + TEN-VAD for streaming
- Add Phi-3-mini fallback only if needed for complex commands

This gives a practical path from working prototype to production-quality voice command system, all running locally on Windows desktop CPU.

---

*Last Updated: 2026-01-27*
*Research conducted for whisper-key-local project*
