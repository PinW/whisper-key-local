# Whisper Model Comparison: distil-large-v3.5 vs large-v3-turbo

A comprehensive technical comparison of two optimized Whisper variants for speech recognition.

## Executive Summary

| Aspect | distil-large-v3.5 | large-v3-turbo |
|--------|-------------------|----------------|
| **Parameters** | 756M | 809M |
| **Decoder Layers** | 2 | 4 |
| **Encoder Layers** | 32 (frozen) | 32 |
| **Language Support** | English only | 99 languages |
| **Translation** | No | Yes (degraded) |
| **Speed vs large-v3** | ~6x faster | ~6x faster |
| **Relative Speed** | ~1.5x faster than turbo | Baseline |
| **Best Use Case** | English transcription | Multilingual ASR |

---

## 1. Architecture Differences

### distil-large-v3.5 (Hugging Face / Distil-Whisper)

- **Total Parameters**: 756M (vs 1,550M for large-v3)
- **Encoder**: 32 layers (identical to large-v3, frozen during training)
- **Decoder**: 2 layers (copied from layers 1 and 32 of original 32-layer decoder)
- **Training Method**: Knowledge distillation from large-v3 "teacher" model
- **Key Innovation**: Maximally-spaced decoder layer initialization captures both early and late decoding representations

### large-v3-turbo (OpenAI)

- **Total Parameters**: 809M (vs 1,550M for large-v3)
- **Encoder**: 32 layers (identical to large-v3)
- **Decoder**: 4 layers (pruned from original 32 layers)
- **Training Method**: Fine-tuned on original Whisper training data after pruning
- **Key Innovation**: Direct pruning + retraining rather than distillation

### Architectural Comparison

| Component | large-v3 | distil-large-v3.5 | large-v3-turbo |
|-----------|----------|-------------------|----------------|
| Encoder Layers | 32 | 32 | 32 |
| Decoder Layers | 32 | 2 | 4 |
| Total Layers | 64 | 34 | 36 |
| Parameters | 1,550M | 756M | 809M |
| Size Reduction | - | 51% smaller | 48% smaller |

---

## 2. Speed Benchmarks

### Real-Time Factor (RTFx) - Higher is Better

From Hugging Face benchmarks on long-form audio:

| Model | RTFx (Long-Form) | Relative Speed |
|-------|------------------|----------------|
| large-v3 | ~33x | 1.0x baseline |
| large-v3-turbo | ~33x | ~1.0x |
| distil-large-v3.5 | ~49x | ~1.5x faster than turbo |

### Faster-Whisper Benchmarks (13 minutes of audio, NVIDIA GPU)

| Model | Precision | Time | Speed vs large-v3 |
|-------|-----------|------|-------------------|
| faster-whisper-large-v3 | fp16 | 52.02s | 1.0x |
| faster-distil-large-v3 | fp16 | 26.13s | 2.0x |
| faster-distil-large-v3 | int8 | 22.54s | 2.3x |
| faster-large-v3-turbo | fp16 | 19.16s | 2.7x |
| faster-large-v3-turbo | int8 | 19.59s | 2.7x |

### User-Reported Benchmarks (RTX 3090, Flash Attention 2, 100 minutes audio)

| Model | Time |
|-------|------|
| distil-whisper/distil-large-v3 | 2m 17s |
| openai/whisper-large-v3-turbo | 2m 59s |

**Key Finding**: In Transformers pipeline (HuggingFace), distil-large-v3.5 is ~1.5x faster than turbo. In faster-whisper (CTranslate2), turbo can be faster due to optimizations for 4-layer decoders.

---

## 3. Accuracy Comparison (WER)

### Short-Form Transcription (< 30 seconds)

| Dataset | large-v3 | large-v3-turbo | distil-v3 | distil-v3.5 |
|---------|----------|----------------|-----------|-------------|
| **ID Average** | 7.15% | 7.24% | 7.37% | **7.10%** |
| **OOD Average** | 7.12% | 7.30% | 7.53% | **7.08%** |
| GigaSpeech | 10.02% | 10.14% | 10.08% | **9.84%** |
| LibriSpeech Clean | **2.01%** | 2.10% | 2.54% | 2.37% |
| LibriSpeech Other | 4.00% | 4.12% | 4.27% | **3.93%** |

**Winner (Short-Form)**: distil-large-v3.5 slightly outperforms turbo

### Long-Form Transcription (> 30 seconds)

| Dataset | large-v3-turbo | distil-v3 | distil-v3.5 |
|---------|----------------|-----------|-------------|
| **OOD Average** | **10.25%** | 11.60% | 11.39% |
| TED-LIUM Long-Form | **3.90%** | 3.90% | 4.63% |
| Earnings22 | 14.19% | 15.06% | **14.19%** |

**Winner (Long-Form)**: large-v3-turbo by ~1% WER

### Faster-Whisper WER (LibriSpeech Clean Val)

| Model | Precision | WER |
|-------|-----------|-----|
| faster-large-v3-turbo | fp16/int8 | **1.92%** |
| faster-distil-large-v3 | fp16/int8 | 2.39% |
| faster-whisper-large-v3 | fp16 | 2.88% |

---

## 4. Memory/VRAM Requirements

### Faster-Whisper VRAM Usage (Transcribing 13 min audio)

| Model | Precision | GPU Memory | CPU Memory |
|-------|-----------|------------|------------|
| faster-whisper-large-v3 | fp16 | 4,521 MB | 901 MB |
| faster-whisper-large-v3 | int8 | 2,953 MB | 2,261 MB |
| faster-large-v3-turbo | fp16 | 2,537 MB | 899 MB |
| faster-large-v3-turbo | int8 | 1,545 MB | 1,526 MB |
| faster-distil-large-v3 | fp16 | 2,409 MB | 900 MB |
| faster-distil-large-v3 | int8 | 1,481 MB | 1,468 MB |

### Model Size on Disk

| Model | Format | Approximate Size |
|-------|--------|------------------|
| large-v3 | fp16 | ~3.0 GB |
| large-v3-turbo | fp16 | ~1.6 GB |
| distil-large-v3.5 | fp32 | ~2.9 GB |
| distil-large-v3.5 | fp16 | ~1.5 GB |

### Recommended Minimum VRAM

| Precision | Minimum VRAM |
|-----------|--------------|
| fp16 | 4 GB |
| int8 | 2 GB |
| int4 (quantized) | 1 GB |

---

## 5. Language Support

### distil-large-v3.5

- **English only** (monolingual)
- Optimized specifically for English transcription
- No translation capability
- Trained on 98,000 hours of English audio data

### large-v3-turbo

- **99 languages** supported
- Speech-to-text translation to English available (but degraded quality)
- Trained on 5+ million hours of multilingual data
- Note: Translation quality is reduced compared to large-v3 because translation data was not included in turbo training

### Language Performance Notes

- Both models inherit uneven performance across languages from large-v3
- Lower accuracy on low-resource languages
- Varying WER across accents, dialects, and demographic groups

---

## 6. Use Case Recommendations

### Choose distil-large-v3.5 When:

1. **English-only transcription** is your use case
2. **Speed is critical** - 1.5x faster than turbo in Transformers
3. **Short-form audio** predominates (< 30 seconds)
4. **Speculative decoding** with large-v3 for identical outputs at 2x speed
5. **Reduced hallucinations** are important (1.3x fewer repeated phrases)
6. **Memory-constrained environments** - slightly lower VRAM usage
7. **HuggingFace Transformers** is your preferred framework

### Choose large-v3-turbo When:

1. **Multilingual support** is required (99 languages)
2. **Long-form transcription** is primary use case
3. **Translation to English** is needed (even if degraded)
4. **CTranslate2/faster-whisper** is your inference engine
5. **Best possible WER** on long-form English content
6. **Broader compatibility** with existing Whisper tooling

### Comparison Matrix

| Use Case | Recommended Model |
|----------|-------------------|
| English podcasts (short segments) | distil-large-v3.5 |
| English podcasts (long-form) | large-v3-turbo |
| Multilingual transcription | large-v3-turbo |
| Real-time English dictation | distil-large-v3.5 |
| Meeting transcription (English) | Either (turbo for long meetings) |
| Video subtitles (multilingual) | large-v3-turbo |
| Voice commands (English) | distil-large-v3.5 |
| Maximum accuracy needed | large-v3 + distil-v3.5 (speculative) |

---

## 7. Known Issues and Quirks

### distil-large-v3.5 Issues

1. **English-only limitation**: Cannot process other languages
2. **Long-form gap**: ~1% WER behind turbo on long-form content
3. **Prompt appending reduced**: Uses 20% prompt appending (vs 50% in earlier versions) - may affect context continuity on very long sequences
4. **Sequential long-form slower**: For single long files, chunked processing is faster

### large-v3-turbo Issues

1. **Translation quality degraded**: Not trained on translation data, so translation mode underperforms
2. **Hallucinations**: Inherits Whisper v3 hallucination tendencies
   - 4x more hallucinations than v2 in some real-world tests
   - Silence can trigger "Thank you for watching" type hallucinations
   - Asian language transcription can insert random English words
3. **Repetitive text generation**: Prone to looping/repetition
4. **Uneven language performance**: Lower accuracy on low-resource languages

### Common Mitigations

```python
# For hallucination reduction
generate_kwargs = {
    "temperature": (0.0, 0.2, 0.4, 0.6, 0.8, 1.0),
    "compression_ratio_threshold": 1.35,
    "no_speech_threshold": 0.6,
    "condition_on_prev_tokens": False,  # Reduces repetition
}

# Use VAD preprocessing to filter silence
# Use hallucination_silence_threshold in whisper CLI
```

---

## 8. Training Data and Methodology

### distil-large-v3.5

| Aspect | Details |
|--------|---------|
| Training Data | 98,000 hours (4x more than v3) |
| Data Sources | Common Voice, LibriSpeech, VoxPopuli, TED-LIUM, People's Speech, GigaSpeech, AMI, Yodas |
| Quality Filter | WER ≤ 10% against pseudo-labels |
| Training Duration | 80 epochs (vs 11 in v3) |
| Batch Size | 4,096 packed segments |
| Hardware | 64 H100 GPUs, 3 days |
| Augmentation | SpecAugment + aggressive augmentation |
| Method | Knowledge distillation with frozen encoder |

### large-v3-turbo

| Aspect | Details |
|--------|---------|
| Training Data | Original Whisper data (5M+ hours) |
| Method | Pruning + fine-tuning |
| Base Model | large-v3 with decoder reduced 32→4 |
| Translation Data | Not included (degraded translation) |

---

## 9. Framework Compatibility

| Framework | distil-large-v3.5 | large-v3-turbo |
|-----------|-------------------|----------------|
| HuggingFace Transformers (4.39+) | Yes | Yes |
| faster-whisper (CTranslate2) | Yes | Yes |
| whisper.cpp (GGML) | Yes | Yes |
| OpenAI Whisper | Yes (with conversion) | Yes |
| Candle (Rust) | Yes | Yes |
| ONNX Runtime | Yes | Yes |

---

## 10. Quick Reference Commands

### HuggingFace Transformers

```python
from transformers import pipeline
import torch

# distil-large-v3.5
pipe = pipeline(
    "automatic-speech-recognition",
    model="distil-whisper/distil-large-v3.5",
    torch_dtype=torch.float16,
    device="cuda:0",
)

# large-v3-turbo
pipe = pipeline(
    "automatic-speech-recognition",
    model="openai/whisper-large-v3-turbo",
    torch_dtype=torch.float16,
    device="cuda:0",
)

result = pipe("audio.mp3")
```

### faster-whisper

```python
from faster_whisper import WhisperModel

# distil-large-v3.5
model = WhisperModel("distil-large-v3", device="cuda", compute_type="float16")

# large-v3-turbo
model = WhisperModel("large-v3-turbo", device="cuda", compute_type="float16")

segments, info = model.transcribe("audio.mp3")
```

---

## Sources

- [distil-whisper/distil-large-v3.5 - Hugging Face](https://huggingface.co/distil-whisper/distil-large-v3.5)
- [openai/whisper-large-v3-turbo - Hugging Face](https://huggingface.co/openai/whisper-large-v3-turbo)
- [faster-whisper Benchmark Issue #1030](https://github.com/SYSTRAN/faster-whisper/issues/1030)
- [Demystifying OpenAI's new Whisper Turbo](https://amgadhasan.substack.com/p/demystifying-openais-new-whisper)
- [Whisper Large V3 Turbo - Medium](https://medium.com/axinc-ai/whisper-large-v3-turbo-high-accuracy-and-fast-speech-recognition-model-be2f6af77bdc)
- [huggingface/distil-whisper GitHub](https://github.com/huggingface/distil-whisper)

---

*Report generated: January 2026*
