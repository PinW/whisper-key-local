# Sherpa-ONNX Streaming STT Prototype [COMPLETE]

As a **Developer** I want **a working sherpa-onnx streaming prototype in this worktree** so I can evaluate real-time streaming STT as an alternative to faster-whisper batch transcription.

**Status:** ✅ Complete - Prototype successful, proceed to integration

## Current State Analysis

**Existing Architecture:**
- `audio_recorder.py` uses sounddevice for microphone input (16kHz target, WASAPI resampling support)
- `whisper_engine.py` provides batch transcription via faster-whisper after recording completes
- `voice_activity_detection.py` has continuous VAD monitoring with TEN-VAD during recording
- Audio flow: record → stop → resample if needed → VAD check → transcribe batch

**Why Sherpa-ONNX:**
- Native streaming support (recognizes as user speaks, not after recording)
- Lightweight Zipformer models (~20M params, ~150ms latency)
- ONNX Runtime CPU inference (no GPU required)
- Same sounddevice integration we already use
- Built-in endpoint detection

**Prototype Goals:**
- Standalone script in this worktree (not integrated into main app yet)
- Validate streaming works on Windows with our audio setup
- Measure real-world latency and accuracy
- Learn the API before planning full integration

## Implementation Plan

### Phase 1: Environment Setup
- [x] Install sherpa-onnx package in development environment
  - ✅ Installed sherpa-onnx v1.12.23 on Windows Python 3.13
- [x] Download streaming Zipformer English model (~20MB)
  - ✅ Downloaded to HuggingFace cache: `models--csukuangfj--sherpa-onnx-streaming-zipformer-en-20M-2023-02-17`
  - ✅ Includes both fp32 and int8 variants
- [x] Verify model files: encoder.onnx, decoder.onnx, joiner.onnx, tokens.txt
  - ✅ All files present: encoder (42MB int8), decoder (539KB int8), joiner (259KB int8), tokens.txt
- [x] Test basic import and model loading
  - ✅ `tools/sherpa_streaming_demo.py` created and tested
  - ✅ OnlineRecognizer loads successfully with int8 model
  - ✅ Stream creation works

### Phase 2: Minimal Streaming Demo
- [x] Create `tools/sherpa_streaming_demo.py` standalone script
  - ✅ Full streaming demo with `--test` flag for Phase 1 tests
- [x] Implement basic OnlineRecognizer setup with Zipformer model
  - ✅ Using int8 quantized model for efficiency
- [x] Add sounddevice microphone input (match our existing 16kHz or use native rate)
  - ✅ MME host API at 44100Hz with soxr resampling to 16kHz
- [x] Process audio chunks in real-time callback
  - ✅ 100ms chunks fed to recognizer via accept_waveform()
- [x] Print partial results as recognition progresses
  - ✅ `[Partial]` prefix with in-place updates
- [x] Detect speech endpoints and print final results
  - ✅ `[Final N]` when is_endpoint() triggers, then reset stream

### Phase 3: Evaluation & Metrics
- [x] Fix 5-10 second startup delay (blocking issue)
  - ✅ Root cause: missing `sample_rate=16000` and `feature_dim=80` parameters
  - ✅ Added endpoint detection config (`enable_endpoint_detection=True`)
  - ✅ Recognition now starts immediately when speaking
- [x] First-word clipping issue - **deferred to integration phase**
  - ⚠️ First utterance after startup clips first syllable (e.g., "YES" → "S")
  - ❌ **DO NOT feed silence/zeros** - tried 4x, always makes things worse
  - Subsequent utterances work fine after first `reset()`
  - May not affect hotkey workflow (natural delay before speaking)
  - Known issue: GitHub #3035 - encoder needs audio context
- [x] Latency: acceptable - text appears in real-time as speaking
- [x] Speech patterns: short commands and sentences both work well
- [x] Accuracy: subjectively good for English, formal comparison not needed
- [x] CPU usage: acceptable on AMD 5600X, no noticeable impact

### Phase 4: Documentation
- [x] Findings documented in this plan (separate research doc not needed)
- [x] Windows-specific: MME audio at native rate + soxr resampling works
- [x] Recommendation: **proceed to integration** - see Conclusion

## Implementation Details

### Installation Commands
```bash
# Install sherpa-onnx (CPU version)
pip install sherpa-onnx

# Verify installation
python -c "import sherpa_onnx; print(sherpa_onnx.__version__)"
```

### Model Download
```bash
# Download streaming Zipformer English model (recommended for CPU)
cd /tmp
wget https://github.com/k2-fsa/sherpa-onnx/releases/download/asr-models/sherpa-onnx-streaming-zipformer-en-20M-2023-02-17.tar.bz2
tar xf sherpa-onnx-streaming-zipformer-en-20M-2023-02-17.tar.bz2

# Or use huggingface-hub
pip install huggingface-hub
huggingface-cli download csukuangfj/sherpa-onnx-streaming-zipformer-en-20M-2023-02-17 --local-dir models/sherpa-zipformer-en
```

### Core API Pattern (WORKING CONFIG)
```python
import sherpa_onnx
import sounddevice as sd
import soxr
import numpy as np

# CRITICAL: These parameters are required for immediate recognition
recognizer = sherpa_onnx.OnlineRecognizer.from_transducer(
    encoder="encoder-epoch-99-avg-1.int8.onnx",
    decoder="decoder-epoch-99-avg-1.int8.onnx",
    joiner="joiner-epoch-99-avg-1.int8.onnx",
    tokens="tokens.txt",
    num_threads=4,
    sample_rate=16000,      # REQUIRED - without this, 9+ second delay
    feature_dim=80,         # REQUIRED - without this, 9+ second delay
    decoding_method="greedy_search",
    provider="cpu",
    enable_endpoint_detection=True,
    rule1_min_trailing_silence=2.4,
    rule2_min_trailing_silence=1.2,
    rule3_min_utterance_length=300,
)
stream = recognizer.create_stream()

# Audio callback - resample from native rate to 16kHz
def audio_callback(indata, frames, time_info, status):
    samples = indata[:, 0].astype(np.float32)
    samples = soxr.resample(samples, native_rate, 16000).astype(np.float32)
    stream.accept_waveform(16000, samples)

# Main recognition loop
with sd.InputStream(samplerate=native_rate, channels=1, callback=audio_callback):
    while True:
        while recognizer.is_ready(stream):
            recognizer.decode_stream(stream)

        text = recognizer.get_result(stream).strip()
        if text:
            print(f"Partial: {text}", end="\r")

        if recognizer.is_endpoint(stream):
            print(f"\nFinal: {text}")
            recognizer.reset(stream)
```

### Model File Structure
```
models/sherpa-zipformer-en/
├── encoder-epoch-99-avg-1.onnx      # ~8MB (int8)
├── decoder-epoch-99-avg-1.onnx      # ~2MB
├── joiner-epoch-99-avg-1.onnx       # ~2MB
└── tokens.txt                        # Vocabulary
```

### Expected Performance (CPU)
| Metric | Target | Notes |
|--------|--------|-------|
| Model load time | <2s | One-time startup cost |
| Recognition latency | 100-300ms | From speech end to text |
| CPU usage | <25% | Single thread typically sufficient |
| Memory | ~200-400MB | Model + runtime buffers |

### Windows Considerations
- **MME audio**: Record at native rate (44.1kHz) and resample to 16kHz via soxr
- **DLL conflicts**: If onnxruntime.dll exists in System32, may load wrong version
- **Visual C++ Runtime**: Requires VC++ 2019 redistributable

## Files Created

- `tools/sherpa_streaming_demo.py` - Standalone streaming demo script ✅
- Model files in HuggingFace cache (not in repo) ✅

**Not created (not needed):**
- `documentation/research/sherpa-onnx-evaluation.md` - findings documented in this plan instead

## Current Status: COMPLETE ✅

**Working:**
- Model loads in ~0.8s
- Streaming recognition works immediately when speaking
- Partial results update in real-time
- Endpoint detection triggers final results
- CPU usage acceptable on AMD 5600X
- Latency feels instantaneous

**Known Issue (deferred):**
- First utterance after startup clips first syllable (e.g., "HELLO" → "O")
- Subsequent utterances after `reset()` work correctly
- May not affect hotkey workflow due to natural delay before speaking
- GitHub Issue #3035 documents root cause - encoder needs audio context
- **DO NOT feed silence/zeros** - makes things worse (tried 4x)
- Will revisit during integration if needed

**Demo script:** `tools/sherpa_streaming_demo.py`
- Run: `python tools\sherpa_streaming_demo.py`
- ORT model (untested): `python tools\sherpa_streaming_demo.py --ort`

## Success Criteria

**Phase 1 Complete:** ✅
- [x] `import sherpa_onnx` works without errors
- [x] Model files downloaded and accessible
- [x] Basic model loading succeeds

**Phase 2 Complete:** ✅
- [x] Demo script runs and captures microphone audio
- [x] Partial recognition results print in real-time as speaking
- [x] Final results print when speech ends
- [x] Clean shutdown with Ctrl+C

**Phase 3 Complete:** ✅
- [x] Startup delay fixed or acceptable workaround found
- [x] First-word clipping issue understood, deferred to integration
- [x] Latency acceptable (real-time partial results)
- [x] Accuracy subjectively good for English
- [x] CPU usage acceptable on AMD 5600X

**Phase 4 Complete:** ✅
- [x] Evaluation documented in this plan
- [x] Go/no-go decision: **GO** - proceed to integration
- [x] Integration approach: new implementation plan to follow

## Risk Mitigation

| Risk | Mitigation |
|------|------------|
| ONNX Runtime DLL conflict | Use isolated venv, check for System32 conflicts |
| Poor accuracy vs Whisper | Document tradeoffs, may need larger model |
| High latency | Try different chunk sizes, threading configs |
| Startup delay | Warmup inference, model preloading, or lazy init |

## Out of Scope (for prototype)

- Integration with main whisper-key application
- GUI or system tray changes
- Configuration file changes
- Production error handling
- Model switching at runtime

## Conclusion

**Decision: GO - Proceed to full integration**

Sherpa-ONNX streaming STT is viable for whisper-key integration:

| Criteria | Result |
|----------|--------|
| Works on Windows | ✅ Yes, with MME + soxr resampling |
| Acceptable latency | ✅ Real-time partial results |
| Acceptable CPU | ✅ Fine on AMD 5600X |
| Acceptable accuracy | ✅ Subjectively good for English |
| API learnable | ✅ Simple callback-based pattern |

**Open item for integration:**
- First-utterance clipping may or may not affect hotkey workflow
- Natural delay between hotkey press and speaking may provide enough context
- If issue persists, consider: pre-roll buffer, or accepting minor clipping

**Next step:** Create implementation plan for integrating sherpa-onnx streaming into whisper-key as an alternative to faster-whisper batch transcription.
