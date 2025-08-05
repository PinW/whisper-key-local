# TEN VAD Post-Processing Pipeline Fix Implementation Plan

As a *user* I want **reliable VAD speech detection using standard post-processing** so false positives from early-exit logic are eliminated and speech detection is accurate across all recording patterns.

## Current State Analysis

### Issues with Current Implementation
- **Early exit problem**: Returns `True` on first chunk with speech (lines 274-282), ignoring rest of recording
- **False positives**: Any recording with speech in first few chunks is marked as "speech" regardless of overall content
- **False negatives**: Recordings ending in silence may be incorrectly classified
- **No holistic analysis**: Processes chunks individually instead of analyzing entire recording
- **Missing standard pipeline**: No hysteresis, duration filtering, or segment merging

### What's Working
- ✅ TEN VAD initialization and basic chunk processing (256-sample frames)
- ✅ Audio preprocessing (float32 → int16 conversion)
- ✅ Integration point in `transcribe_audio()` method
- ✅ Proper error handling and fallback behavior
- ✅ Timing measurements and logging infrastructure

## Implementation Plan

### Phase 1: Implement Probability Buffering
- [x] Remove early exit logic from chunk processing loop
  - ✅ Removed `return True` inside chunk processing loop (lines 275-282)
  - ✅ Now processes ALL chunks before making decision
- [x] Collect all frame probabilities in array before making decision
  - ✅ Added `probabilities = []` array to collect all frame probabilities
  - ✅ All chunks processed and probabilities stored before decision
- [x] Maintain existing chunk processing (256 samples at 16ms intervals)
  - ✅ Chunk processing logic unchanged, still 256-sample frames
  - ✅ Padding logic for final chunk maintained
- [x] Update logging to show probability distribution (min/max/avg)
  - ✅ Added min/max/avg probability calculation and logging
  - ✅ Enhanced logging shows frame count, probability range, and processing time

### Phase 2: Add Speech Segment Detection Logic
- [x] Implement consecutive frame counting for speech detection
  - ✅ Added `_detect_speech_with_hysteresis()` method with consecutive frame logic
  - ✅ Counts consecutive speech frames and requires minimum duration
- [x] Add onset threshold parameter (0.60 starting value)
  - ✅ Added onset=0.6 parameter for speech start detection
- [x] Implement minimum duration filtering (min_speech_duration=0.05s)
  - ✅ Updated to 50ms minimum duration (WebRTC/Silero standard)
  - ✅ Converts to ~3 frames at 16ms per frame
- [x] Add hysteresis logic with onset/offset thresholds to prevent flickering
  - ✅ Added offset=0.4 parameter for speech end detection
  - ✅ Prevents rapid on/off switching on borderline probabilities
- [x] Return True if ANY valid speech segment found (not average/percentage)
  - ✅ Returns True as soon as minimum consecutive frames found
  - ✅ Uses "Did he talk?" logic, not averaging

### Phase 3: Enhanced Debugging and Tuning
- [ ] Add detailed probability trace logging for debugging
- [ ] Include segment information in log output
- [ ] Add configurable threshold parameters for easy tuning
- [ ] Update console feedback with post-processing timing

### Phase 4: User Testing and Validation
- [ ] Test with silent recordings (should return False consistently)
- [ ] Test with recordings ending in silence (should detect speech if present earlier)
- [ ] Test with brief speech recordings (should detect speech reliably)
- [ ] Fine-tune thresholds based on testing results

## Implementation Details

### Simple Speech Detection Method
```python
def _detect_any_speech_segments(self, probabilities, threshold=0.60, min_duration_sec=0.15):
    """
    Detect if ANY valid speech segments exist in audio.
    
    Logic: "Did the user speak?" not "Did the user speak on average?"
    
    Parameters:
    - probabilities: List of per-frame speech probabilities
    - threshold: Minimum probability to consider speech (0.60)
    - min_duration_sec: Minimum duration to filter noise (0.05s)
    
    Returns:
    - True if any valid speech segment found, False otherwise
    """
    hop_sec = 0.016  # 256 samples at 16kHz = 16ms per frame
    min_frames = int(min_duration_sec / hop_sec)  # ~9 frames for 0.15s
    
    consecutive_speech_frames = 0
    
    for prob in probabilities:
        if prob > threshold:
            consecutive_speech_frames += 1
            # Found enough consecutive speech frames = valid segment
            if consecutive_speech_frames >= min_frames:
                return True
        else:
            # Reset counter on silence/low probability
            consecutive_speech_frames = 0
    
    return False  # No valid speech segments found
```

### Updated Main Method
```python
def _check_audio_for_speech(self, audio_data: np.ndarray) -> bool:
    """
    Check if audio contains speech using TEN VAD with simple segment detection
    """
    # ... existing preprocessing code ...
    
    # Collect ALL probabilities first (no early exit)
    probabilities = []
    for i in range(0, len(audio_int16), chunk_size):
        chunk = audio_int16[i:i + chunk_size]
        if len(chunk) < chunk_size:
            chunk = np.pad(chunk, (0, chunk_size - len(chunk)), mode='constant')
        
        prob, _ = self.ten_vad.process(chunk)  # Ignore flag, use probability
        probabilities.append(prob)
    
    # Simple detection: find ANY valid speech segment
    speech_detected = self._detect_any_speech_segments(
        probabilities, 
        threshold=0.60,
        min_duration_sec=0.05
    )
    
    # Enhanced logging
    if probabilities:
        self.logger.info(f"TEN VAD analysis: {len(probabilities)} frames, "
                        f"prob range [{min(probabilities):.3f}-{max(probabilities):.3f}], "
                        f"avg {np.mean(probabilities):.3f}, "
                        f"speech detected: {speech_detected}")
    
    return speech_detected
```

### Configurable Parameters
```python
# Add to WhisperEngine.__init__() for easy tuning
self.vad_speech_threshold = 0.60   # Probability threshold for speech detection
self.vad_min_speech_duration = 0.05  # Minimum speech segment length (seconds)
# Note: No hysteresis or min_off needed for binary "any speech?" detection
```

## Files to Modify

- **src/whisper_engine.py**: 
  - Update `_check_audio_for_speech()` method to remove early exit logic
  - Add `_detect_any_speech_segments()` method for consecutive frame counting
  - Add simple configurable parameters to `__init__()` (threshold, min_duration)
  - Enhance logging with probability distribution info

## Success Criteria

### Functional Requirements
1. **Silent recordings**: Consistently return `False` with no false positives
2. **Speech recordings**: Reliably return `True` for recordings with actual speech
3. **Mixed recordings**: Correctly handle recordings with speech followed by silence
4. **Brief speech**: Detect short speech segments (>0.15s) reliably
5. **No regression**: Processing time remains under 100ms for VAD analysis

### Technical Requirements  
1. **Holistic analysis**: All frames processed before decision made
2. **Standard pipeline**: Hysteresis + duration filtering + segment merging implemented
3. **Tunable parameters**: Thresholds easily adjustable for optimization
4. **Comprehensive logging**: Probability traces and segment info for debugging
5. **Backward compatibility**: No changes to external API or integration points

### Testing Validation
1. Silent 1-2 second recordings → `False` (no hallucinations)
2. "Hello world" recordings → `True` (proper detection)  
3. "Speech...long pause" recordings → `True` (detects early speech)
4. Very brief speech (<0.15s) → `False` (filters noise blips)
5. Processing time: <50ms for typical short recordings

## Risk Mitigation

- **Parameter tuning needed**: Start with proven threshold values (0.60) and adjust based on testing
- **Environment differences**: Include debugging output for threshold adjustment
- **Performance impact**: Simple consecutive frame counting adds minimal overhead
- **False negative risk**: Conservative defaults favor detection over rejection

## Future Enhancements (When Full Post-Processing Pipeline Needed)

The **hysteresis** and **min_off** parameters we're skipping could be valuable for:

1. **Real-time streaming VAD**: Smooth on/off transitions without chattering
2. **Segment-level transcription**: "Transcribe each sentence separately" 
3. **Long recording analysis**: Split recordings at natural pause boundaries
4. **Auto-editing features**: Remove long pauses, detect speaker changes
5. **Live transcription display**: Show/hide text smoothly as user speaks

For now, simple "any speech detected?" logic is perfect for preventing hallucinations on silent recordings.