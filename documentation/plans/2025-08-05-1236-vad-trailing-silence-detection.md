# VAD Trailing Silence Detection Implementation Plan

As a *user* I want **VAD detection of trailing silence** so recordings don't hallucinate text at the end

**Note: Execute one line-item at a time and confirm with user before proceeding to next**
**Note: Update this document as you go, checking off tasks and taking notes needed for later**

## Current State Analysis

- Recordings with trailing silence or soft/unclear final words produce hallucinations
- No end-of-recording validation occurs
- Entire audio is sent to transcription regardless of trailing silence
- VAD is available in faster-whisper but not used for edge detection

## Implementation Plan

### Phase 1: Add Trailing Silence Detection Infrastructure
- [ ] Create method to determine VAD check window based on recording length
- [ ] Add configuration for trailing silence detection in config.yaml
- [ ] Create method to run VAD on audio tail and find last speech timestamp

### Phase 2: Implement Trimming Logic
- [ ] Integrate VAD tail check into transcribe_audio() method
- [ ] Trim audio at last detected speech point
- [ ] Add safety padding after last speech (e.g., 200ms)
- [ ] Log trimming decisions and amount trimmed

### Phase 3: Testing & Refinement
- [ ] Test with various recording lengths and trailing silence patterns
- [ ] Verify soft speech at end isn't cut off
- [ ] Fine-tune detection windows and padding

## Implementation Details

### Detection Window Logic
```python
def _get_vad_check_window(self, audio_duration: float) -> float:
    """
    Determine how much of the end to check based on total duration
    Returns 0 if no check needed (too short)
    """
    if audio_duration < 5.0:
        return 0  # No trailing check for recordings under 5 seconds
    elif audio_duration >= 10.0:
        return 3.0  # Check last 3 seconds for long recordings
    else:
        return 2.0  # Check last 2 seconds for medium recordings (5-10s)
```

### Trailing Silence Detection Method
```python
def _trim_trailing_silence(self, audio_data: np.ndarray, sample_rate: int) -> np.ndarray:
    """
    Use VAD to detect and trim trailing silence with robust error handling
    Returns trimmed audio data or original if processing fails
    """
    start_time = time.time()
    audio_duration = len(audio_data) / sample_rate
    
    try:
        check_window = self._get_vad_check_window(audio_duration)
        
        # Skip VAD check for recordings < 1 second
        if check_window == 0:
            self.logger.debug("Skipping VAD trim: recording too short")
            return audio_data
        
        # Performance safeguard: timeout check
        max_processing_time = getattr(self, 'vad_max_processing_time', 0.5)
        
        # Extract the tail portion to check
        check_samples = int(check_window * sample_rate)
        start_idx = max(0, len(audio_data) - check_samples)
        audio_tail = audio_data[start_idx:]
        
        self.logger.debug(f"VAD checking last {check_window:.1f}s of {audio_duration:.1f}s recording")
        
        # Use faster-whisper's built-in VAD on the audio tail
        segments, _ = self.model.transcribe(
            audio_tail,
            beam_size=1,  # Minimal beam for speed
            language=self.language,
            condition_on_previous_text=False,
            vad_filter=True,  # Enable VAD filtering
            vad_parameters=dict(
                threshold=0.5,
                min_speech_duration_ms=100,
                min_silence_duration_ms=100
            )
        )
        
        # Check processing time
        processing_time = time.time() - start_time
        if processing_time > max_processing_time:
            self.logger.warning(f"VAD processing timeout ({processing_time:.3f}s), using original audio")
            return audio_data
        
        # Convert segments to list to find last speech
        segment_list = list(segments)
        
        # If no speech segments detected in tail, trim the entire check window
        if not segment_list:
            self.logger.info("No speech detected in tail, trimming check window")
            return audio_data[:start_idx] if start_idx > 0 else audio_data
        
        # Find last speech segment end time (in tail coordinates)
        last_segment = segment_list[-1]
        last_speech_end_tail = last_segment.end  # End time in seconds within the tail
        
        # Convert back to full audio coordinates
        last_speech_end_samples = start_idx + int(last_speech_end_tail * sample_rate)
        
        # Add safety padding
        safety_padding_samples = int((getattr(self, 'vad_safety_padding_ms', 200) / 1000.0) * sample_rate)
        trim_point = min(len(audio_data), last_speech_end_samples + safety_padding_samples)
        
        # Only trim if we're actually removing significant silence
        if trim_point < len(audio_data):
            trimmed_samples = len(audio_data) - trim_point
            trimmed_duration = trimmed_samples / sample_rate
            
            # Don't trim tiny amounts (avoid unnecessary processing)
            min_trim_duration = getattr(self, 'vad_min_trim_duration', 0.1)  # 100ms minimum
            if trimmed_duration < min_trim_duration:
                self.logger.debug(f"Trim duration {trimmed_duration:.3f}s too small, keeping original")
                return audio_data
            
            self.logger.info(f"VAD trimmed {trimmed_duration:.2f}s of trailing silence (processing: {processing_time:.3f}s)")
            return audio_data[:trim_point]
        else:
            self.logger.debug("No significant trailing silence detected")
            return audio_data
            
    except Exception as e:
        processing_time = time.time() - start_time
        self.logger.warning(f"VAD trimming failed ({processing_time:.3f}s): {e}, using original audio")
        # Always return original audio on any error
        return audio_data
```

### Integration Point
```python
# In transcribe_audio() before transcription
if self.vad_trim_enabled:
    original_duration = len(audio_data) / sample_rate
    audio_data = self._trim_trailing_silence(audio_data, sample_rate)
    new_duration = len(audio_data) / sample_rate
    
    if new_duration < original_duration:
        trimmed_seconds = original_duration - new_duration
        self.logger.info(f"Trimmed {trimmed_seconds:.2f}s of trailing silence")
```

## Files to Modify

- **src/whisper_engine.py**: Add trailing silence detection and trimming logic
- **config.yaml**: Add trailing silence detection configuration
- **src/config_manager.py**: Validate new configuration options if needed

## Configuration
```yaml
whisper:
  # Trailing silence detection
  vad_trim:
    enabled: true
    safety_padding_ms: 200           # Keep this much after last detected speech
    max_processing_time_ms: 500      # Max time for VAD processing (performance guard)
    min_trim_duration_ms: 100        # Minimum silence to trim (avoid tiny trims)
    fallback_on_error: true          # Use original audio if VAD fails
    detection_windows:
      min_recording_length: 5.0       # seconds - skip VAD for recordings < 5s
      long_recording_threshold: 10.0  # seconds - recordings >= 10s check last 3s
      long_recording_window: 3.0      # check last 3s for long recordings (>=10s)
      short_recording_window: 2.0     # check last 2s for medium recordings (5-10s)
```

## Success Criteria

1. Recordings ≥5 seconds with trailing silence are trimmed effectively
2. Recordings <5 seconds skip trailing silence check entirely
3. Soft speech at end of recordings is preserved (not cut off)
4. Processing overhead stays under 500ms for longest recordings (with timeout protection)
5. Hallucinations from trailing silence are eliminated
6. Feature can be disabled via config
7. Two recording length buckets: 5-10s (check 2s) and 10s+ (check 3s)
8. **NEW**: Graceful fallback to original audio on any VAD processing errors
9. **NEW**: Performance timeout prevents VAD processing from blocking transcription
10. **NEW**: Minimum trim threshold prevents unnecessary tiny trims