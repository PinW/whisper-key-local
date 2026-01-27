# Moonshine Streaming STT Prototype Implementation Plan

As a **Developer** I want **a standalone prototype to test real-time streaming transcription with Moonshine** so I can validate latency, accuracy, and integration patterns before adding to the main application.

## Current State Analysis

**Existing Architecture:**
- Batch transcription via faster-whisper in `whisper_engine.py`
- Real-time VAD processing with TEN VAD in `voice_activity_detection.py`
- Audio capture in 256-sample chunks (16ms at 16kHz) in `audio_recorder.py`
- Event-driven patterns for VAD events already established

**Gap:**
- No streaming transcription capability
- Moonshine not yet integrated
- Unknown: Moonshine's actual streaming behavior and latency characteristics

**Why Prototype First:**
- Moonshine streaming API behavior needs validation
- ONNX runtime setup may have Windows-specific quirks
- Isolate experimentation from production code

## Implementation Plan

### Phase 1: Environment Setup
- [ ] Install moonshine-onnx package
- [ ] Verify ONNX runtime works on Windows
- [ ] Download Moonshine Tiny model (~190MB)

### Phase 2: Prototype Implementation
- [ ] Create `tools/moonshine_streaming_prototype.py`
- [ ] Implement audio capture loop (reuse sounddevice patterns)
- [ ] Implement Moonshine model loading
- [ ] Implement chunk accumulation and transcription
- [ ] Add timing instrumentation
- [ ] Add console output for partial results

### Phase 3: Testing & Measurement
- [ ] Test basic transcription functionality
- [ ] Measure chunk-to-text latency
- [ ] Measure end-to-end latency
- [ ] Test with various phrase lengths
- [ ] Document findings

## Implementation Details

### Moonshine Streaming Approach

Moonshine doesn't have native streaming like WebSocket APIs. The streaming pattern is:
1. Accumulate audio in a sliding window
2. Periodically transcribe the accumulated audio
3. Diff against previous transcription for "new" text

```python
# Sliding window approach
TRANSCRIBE_INTERVAL_MS = 500  # Transcribe every 500ms
MIN_AUDIO_MS = 200            # Minimum audio before first transcription

class StreamingBuffer:
    def __init__(self):
        self.audio_buffer = []
        self.last_transcription = ""
        self.last_transcribe_time = 0

    def add_chunk(self, chunk):
        self.audio_buffer.append(chunk)

    def should_transcribe(self) -> bool:
        elapsed = time.time() - self.last_transcribe_time
        audio_duration = len(self.audio_buffer) * CHUNK_MS / 1000
        return elapsed >= TRANSCRIBE_INTERVAL_MS/1000 and audio_duration >= MIN_AUDIO_MS/1000

    def get_audio(self) -> np.ndarray:
        return np.concatenate(self.audio_buffer)
```

### Prototype Structure

```python
#!/usr/bin/env python3
"""Moonshine streaming STT prototype."""

import time
import threading
import numpy as np
import sounddevice as sd
from moonshine_onnx import MoonshineOnnxModel

SAMPLE_RATE = 16000
CHUNK_MS = 32
CHUNK_SIZE = int(SAMPLE_RATE * CHUNK_MS / 1000)  # 512 samples
TRANSCRIBE_INTERVAL_MS = 500

class MoonshineStreamingPrototype:
    def __init__(self, model_name="moonshine/tiny"):
        print(f"Loading Moonshine model: {model_name}")
        self.model = MoonshineOnnxModel(model_name=model_name)
        print("Model loaded!")

        self.audio_buffer = []
        self.buffer_lock = threading.Lock()
        self.last_transcription = ""
        self.running = False

        # Metrics
        self.transcription_times = []
        self.chunk_count = 0

    def audio_callback(self, indata, frames, time_info, status):
        if status:
            print(f"Audio status: {status}")
        with self.buffer_lock:
            self.audio_buffer.append(indata.copy().flatten())
            self.chunk_count += 1

    def transcription_loop(self):
        last_transcribe = time.time()

        while self.running:
            time.sleep(0.05)  # 50ms polling

            elapsed = time.time() - last_transcribe
            if elapsed < TRANSCRIBE_INTERVAL_MS / 1000:
                continue

            with self.buffer_lock:
                if len(self.audio_buffer) == 0:
                    continue
                audio = np.concatenate(self.audio_buffer)

            # Transcribe
            start = time.time()
            try:
                text = self.model.transcribe(audio)
                if isinstance(text, list):
                    text = " ".join(text)
            except Exception as e:
                print(f"Transcription error: {e}")
                continue

            latency_ms = (time.time() - start) * 1000
            self.transcription_times.append(latency_ms)

            # Show result if changed
            if text and text != self.last_transcription:
                audio_duration = len(audio) / SAMPLE_RATE
                print(f"[{audio_duration:.1f}s | {latency_ms:.0f}ms] {text}")
                self.last_transcription = text

            last_transcribe = time.time()

    def run(self, duration_seconds=30):
        print(f"\nRecording for {duration_seconds} seconds...")
        print("Speak now! Partial transcriptions will appear below.\n")

        self.running = True
        self.audio_buffer = []
        self.chunk_count = 0
        self.transcription_times = []

        # Start transcription thread
        transcribe_thread = threading.Thread(target=self.transcription_loop, daemon=True)
        transcribe_thread.start()

        # Start audio capture
        with sd.InputStream(
            samplerate=SAMPLE_RATE,
            channels=1,
            dtype=np.float32,
            blocksize=CHUNK_SIZE,
            callback=self.audio_callback
        ):
            time.sleep(duration_seconds)

        self.running = False
        transcribe_thread.join(timeout=1.0)

        # Print metrics
        self._print_metrics()

    def _print_metrics(self):
        print("\n" + "="*50)
        print("METRICS")
        print("="*50)
        print(f"Total chunks processed: {self.chunk_count}")
        print(f"Audio duration: {self.chunk_count * CHUNK_MS / 1000:.1f}s")

        if self.transcription_times:
            avg = sum(self.transcription_times) / len(self.transcription_times)
            min_t = min(self.transcription_times)
            max_t = max(self.transcription_times)
            print(f"Transcription latency: avg={avg:.0f}ms, min={min_t:.0f}ms, max={max_t:.0f}ms")
            print(f"Transcription count: {len(self.transcription_times)}")

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="Moonshine streaming STT prototype")
    parser.add_argument("--duration", type=int, default=30, help="Recording duration in seconds")
    parser.add_argument("--model", default="moonshine/tiny", help="Model name (moonshine/tiny or moonshine/base)")
    args = parser.parse_args()

    proto = MoonshineStreamingPrototype(model_name=args.model)
    proto.run(duration_seconds=args.duration)
```

### Audio Format

```python
SAMPLE_RATE = 16000       # 16kHz (Moonshine requirement)
CHANNELS = 1              # Mono
DTYPE = np.float32        # Float32 normalized [-1.0, 1.0]
CHUNK_SIZE = 512          # 32ms chunks (larger than VAD's 256)
```

### Expected Output

```
Loading Moonshine model: moonshine/tiny
Model loaded!

Recording for 30 seconds...
Speak now! Partial transcriptions will appear below.

[0.5s | 180ms] Hello
[1.0s | 195ms] Hello world
[1.5s | 210ms] Hello world this is a test
[2.0s | 188ms] Hello world this is a test of streaming

==================================================
METRICS
==================================================
Total chunks processed: 937
Audio duration: 30.0s
Transcription latency: avg=193ms, min=175ms, max=245ms
Transcription count: 60
```

## Files to Create

| File | Purpose |
|------|---------|
| `tools/moonshine_streaming_prototype.py` | Standalone prototype script |

## Success Criteria

**Functionality:**
- [ ] Prototype runs without crashes
- [ ] Audio capture works correctly
- [ ] Moonshine model loads and transcribes
- [ ] Partial results appear while speaking

**Performance:**
- [ ] Per-transcription latency <500ms on CPU
- [ ] Memory usage stable (no leaks)
- [ ] CPU usage reasonable (<50% single core)

**Output:**
- [ ] Timing metrics displayed
- [ ] Partial transcriptions shown incrementally
- [ ] Final summary of latency statistics

## Open Questions to Investigate

1. **Does Moonshine handle variable-length audio well?**
   - Test with 0.5s, 1s, 2s, 5s audio chunks

2. **What's the optimal transcription interval?**
   - 250ms? 500ms? 1000ms?
   - Trade-off: latency vs accuracy vs CPU

3. **How does Moonshine handle silence?**
   - Does it hallucinate on silence like Whisper?
   - May need VAD pre-filtering

4. **ONNX runtime performance on Windows?**
   - CPU vs DirectML acceleration
   - Memory footprint

## Next Steps After Prototype

If successful:
1. Document findings in `documentation/research/moonshine-streaming-results.md`
2. Design integration with existing VAD
3. Plan voice command detection layer
4. Consider adding to main app as optional feature
