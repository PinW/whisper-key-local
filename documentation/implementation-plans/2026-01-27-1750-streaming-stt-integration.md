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
- [ ] Create `streaming_recognizer.py` with `StreamingRecognizer` class
- [ ] Implement model loading with HuggingFace cache path detection
- [ ] Add `process_chunk(audio_chunk)` method for callback integration
- [ ] Add `get_partial_result()` and `is_endpoint()` methods
- [ ] Add `reset()` method for new utterance after endpoint
- [ ] Handle resampling internally (native rate → 16kHz via soxr)

### Phase 2: StreamingManager Orchestration
- [ ] Create `StreamingManager` class (similar pattern to `VadManager`)
- [ ] Add config flag `streaming_enabled` (default: false for now)
- [ ] Implement `create_continuous_recognizer()` factory method
- [ ] Add result callback for partial/final text delivery
- [ ] Handle model availability check (graceful degradation if unavailable)

### Phase 3: Audio Recorder Integration
- [ ] Add `streaming_manager` parameter to `AudioRecorder.__init__()`
- [ ] Create continuous recognizer in `_setup_continuous_streaming()`
- [ ] Feed audio chunks in `audio_callback()` alongside VAD processing
- [ ] Reset streaming recognizer in `start_recording()` (like VAD reset)

### Phase 4: Real-Time Display
- [ ] Add streaming result callback to `StateManager`
- [ ] Print partial results with carriage return (`\r`) for in-place update
- [ ] Print final results (on endpoint) with newline
- [ ] Clear streaming display when recording stops

### Phase 5: Configuration
- [ ] Add `streaming:` section to `config.defaults.yaml`
- [ ] Add `streaming_enabled: false` setting
- [ ] Add `streaming_model: "standard"` setting (for future model selection)
- [ ] Add config getter in `ConfigManager`

### Phase 6: Main Integration
- [ ] Create `StreamingManager` in `main.py` setup
- [ ] Pass to `AudioRecorder` setup function
- [ ] Wire streaming callback through `StateManager`

### Phase 7: First-Utterance Clipping Investigation
- [ ] Test if hotkey workflow naturally avoids clipping (delay before speaking)
- [ ] If clipping occurs, try pre-roll buffer approach:
  - Keep rolling 200-500ms audio buffer before recording "starts"
  - Feed pre-roll to streaming recognizer when recording begins
- [ ] If pre-roll doesn't help, try warmup approach:
  - Feed brief real audio (not silence) during model init
  - Or accept minor clipping as known limitation
- [ ] Document findings and chosen mitigation

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

## Files to Modify

| File | Changes |
|------|---------|
| `src/whisper_key/streaming_recognizer.py` | **NEW** - StreamingRecognizer class |
| `src/whisper_key/streaming_manager.py` | **NEW** - StreamingManager factory class |
| `src/whisper_key/audio_recorder.py` | Add streaming integration to callback |
| `src/whisper_key/state_manager.py` | Add streaming result callback handler |
| `src/whisper_key/main.py` | Create and wire StreamingManager |
| `src/whisper_key/config.defaults.yaml` | Add streaming section |
| `src/whisper_key/config_manager.py` | Add streaming config getter |

## Success Criteria

- [ ] When `streaming_enabled: true`, partial transcription appears during recording
- [ ] Text updates in-place as user speaks (no scrolling spam)
- [ ] Endpoint detection shows finalized segments
- [ ] Existing Whisper batch transcription still works unchanged
- [ ] Graceful fallback if sherpa-onnx not installed
- [ ] No noticeable impact on recording quality or CPU usage
- [ ] Model loads during app startup (not on first recording)
- [ ] First-utterance clipping tested and either mitigated or documented as known limitation

## Out of Scope (Future Work)

- Using streaming results to auto-stop recording
- Separate hotkey for streaming-only mode
- Replacing Whisper batch transcription with streaming
- Multiple streaming model selection
- Streaming accuracy comparison vs Whisper
