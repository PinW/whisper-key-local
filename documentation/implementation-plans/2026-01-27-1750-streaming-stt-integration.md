# Streaming STT Integration

As a **User** I want **real-time transcription display while recording** so I can see my words appear as I speak them.

## Current State Analysis

**Existing Architecture:**
- `audio_recorder.py` captures audio via sounddevice callback, buffers to list
- `voice_activity_detection.py` processes chunks in parallel via `ContinuousVoiceDetector`
- VAD receives chunks in the same callback as audio buffering (line 199-204)
- After recording stops, `whisper_engine.py` transcribes the complete audio batch
- Console output shows status messages but no live text during recording

**Sherpa-ONNX Prototype (tools/sherpa_streaming_demo.py):**
- Validates streaming STT works on Windows with MME + soxr resampling
- Uses `OnlineRecognizer.from_transducer()` with int8 Zipformer model
- Feeds audio via `stream.accept_waveform()` in sounddevice callback
- Calls `decode_stream()`, `get_result()`, `is_endpoint()`, `reset()` in main loop
- Model loads in ~0.8s, recognition starts immediately

**Known Issue from Prototype:**
- First utterance after model load clips first syllable (e.g., "HELLO" → "O")
- Subsequent utterances after `reset()` work correctly

**Integration Goal:**
- When recording starts, also start sherpa-onnx streaming recognition
- Display partial results in real-time as user speaks
- Existing recording flow unchanged - audio still buffers for Whisper batch transcription
- Future: may use streaming results to auto-stop recording or as separate mode

## Implementation Plan

### Phase 1: StreamingRecognizer Component
- [x] Create `streaming_recognizer.py` with `StreamingRecognizer` class
  - ✅ Created `src/whisper_key/streaming_recognizer.py`
  - ✅ Implemented model loading with HuggingFace cache path detection
  - ✅ Added `process_chunk(audio_chunk)` method with internal resampling via soxr
  - ✅ Added `get_partial_result()` and `is_endpoint()` methods
  - ✅ Added `reset()` method for new utterance after endpoint
  - ✅ Added `is_loaded()` check and `set_recording_rate()` helper

### Phase 2: StreamingManager Orchestration
- [x] Create `StreamingManager` class (similar pattern to `VadManager`)
  - ✅ Created `src/whisper_key/streaming_manager.py`
  - ✅ Added config flags `streaming_enabled` and `streaming_model`
  - ✅ Implemented `create_continuous_recognizer()` factory method
  - ✅ Added `ContinuousStreamingRecognizer` with result callback for partial/final text
  - ✅ Added `is_available()` check for graceful degradation

### Phase 3: Audio Recorder Integration
- [x] Add `streaming_manager` parameter to `AudioRecorder.__init__()`
  - ✅ Added `streaming_manager` and `on_streaming_result` callback parameters
  - ✅ Created `_setup_continuous_streaming()` method with recording rate configuration
  - ✅ Feed audio chunks in `audio_callback()` alongside VAD processing
  - ✅ Reset streaming recognizer in `start_recording()` (like VAD reset)

### Phase 4: Real-Time Display
- [x] Add streaming result callback to `StateManager`
  - ✅ Added `handle_streaming_result(text, is_final)` method
  - ✅ Print partial results with carriage return for in-place update
  - ✅ Print final results (on endpoint) with newline
  - ✅ Added `_clear_streaming_display()` and called on recording stop/cancel/vad-timeout

### Phase 5: Configuration
- [x] Add `streaming:` section to `config.defaults.yaml`
  - ✅ Added `streaming_enabled: false` setting
  - ✅ Added `streaming_model: standard` setting
  - ✅ Added `get_streaming_config()` method in `ConfigManager`

### Phase 6: Main Integration
- [x] Create `StreamingManager` in `main.py` setup
  - ✅ Added `setup_streaming()` function (consistent with other setup functions)
  - ✅ Model loading handled by `StreamingManager.initialize()` method
  - ✅ Streaming model loads after main Whisper model, before AudioRecorder
  - ✅ Pass `streaming_manager` to `AudioRecorder` setup function
  - ✅ Wire `handle_streaming_result` callback through `StateManager`

### Phase 7: First-Utterance Clipping Fix
- [x] Investigate and fix first-utterance clipping issue
  - ✅ Root cause: Zipformer left-context caches not properly initialized until first real speech
  - ✅ Solution: Warmup with pre-recorded speech audio at model load time
  - ✅ Added `warmup()` method to `StreamingRecognizer` with bundled speech sample
  - ✅ Warmup called automatically during `StreamingManager.initialize()`

**Attempts that FAILED:**
- ❌ reset() immediately after model load
- ❌ Feeding silence/zeros before speech, then reset
- ❌ Feeding 200ms ambient mic audio, then reset
- ❌ Skip reset() on first recording only
- ❌ Feed 1s of zeros at model load (no reset) - prime the stream
- ❌ Warmup with beep sound in throwaway stream, then create fresh stream

**Solution that WORKED:**
- ✅ Pre-recorded SPEECH audio file for warmup (not beeps/silence)
- Speech audio properly initializes Zipformer's chunk-based left-context caches

## Implementation Details

### StreamingRecognizer API
```python
class StreamingRecognizer:
    def __init__(self, model_type="standard", recording_rate=16000):
        # Load sherpa-onnx OnlineRecognizer
        # Store recording rate for resampling

    def process_chunk(self, audio_chunk: np.ndarray) -> None:
        # Resample if needed, feed to stream.accept_waveform()
        # Call decode_stream() while is_ready()

    def get_partial_result(self) -> str:
        # Return current recognition text

    def is_endpoint(self) -> bool:
        # Check if utterance complete

    def reset(self) -> None:
        # Reset stream for new utterance
```

### Audio Callback Integration
```python
# In audio_recorder.py audio_callback():
def audio_callback(audio_data, frames, _time, status):
    if self.is_recording:
        self.audio_data.append(audio_data.copy())

        # Existing VAD processing
        if self.continuous_vad and frames == vad_blocksize:
            # ... VAD code ...

        # NEW: Streaming STT processing
        if self.continuous_streaming:
            self.continuous_streaming.process_chunk(audio_data)
            self._check_streaming_results()
```

### Display Pattern
```python
# Partial result (in-place update)
print(f"\r  💬 {partial_text:<70}", end="", flush=True)

# Final result (on endpoint)
print(f"\r  💬 {final_text}")

# Recording stops - clear line
print("\r" + " " * 80 + "\r", end="")
```

### Config Structure
```yaml
streaming:
  # Real-time streaming speech recognition (experimental)
  # Shows transcription as you speak, separate from final Whisper transcription
  streaming_enabled: false

  # Streaming model type
  # Options: "standard" (default int8 Zipformer)
  streaming_model: standard
```

## Files Modified

| File | Changes |
|------|---------|
| `src/whisper_key/streaming_recognizer.py` | **NEW** - StreamingRecognizer class with warmup() method |
| `src/whisper_key/streaming_manager.py` | **NEW** - StreamingManager with initialize() method |
| `src/whisper_key/audio_recorder.py` | Add streaming integration to callback |
| `src/whisper_key/state_manager.py` | Add streaming result callback handler |
| `src/whisper_key/main.py` | Create and wire StreamingManager |
| `src/whisper_key/config.defaults.yaml` | Add streaming section |
| `src/whisper_key/config_manager.py` | Add streaming config getter |
| `src/whisper_key/assets/streaming-recognizer-warmup.wav` | **NEW** - Speech sample for warmup |

## Success Criteria

- [x] When `streaming_enabled: true`, partial transcription appears during recording
- [x] Text updates in-place as user speaks (no scrolling spam)
- [x] Endpoint detection shows finalized segments
- [x] Existing Whisper batch transcription still works unchanged
- [x] Graceful fallback if sherpa-onnx not installed
- [x] No noticeable impact on recording quality or CPU usage
- [x] Model loads during app startup (not on first recording)
- [x] First-utterance clipping fixed with speech warmup at model load

## Out of Scope (Future Work)

- Using streaming results to auto-stop recording
- Separate hotkey for streaming-only mode
- Replacing Whisper batch transcription with streaming
- Multiple streaming model selection
- Streaming accuracy comparison vs Whisper
