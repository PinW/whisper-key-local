# VAD Pre-check for Short Recordings Implementation Plan

As a *user* I want **VAD pre-check on recordings ≤2.5 seconds** so silence doesn't waste processing time and create hallucinations

## Current State Analysis

- Short silent recordings (<2.5 seconds) are fully transcribed, causing hallucinations
- No pre-transcription validation occurs
- Processing time is wasted on silence that produces "Thank you for watching" etc.
- Need dedicated VAD solution for high-precision speech detection
- TEN VAD offers superior precision vs WebRTC/Silero with 5-57ms processing time
- App will use fixed 16kHz sample rate (optimal for speech + TEN VAD requirement)

## Implementation Plan

### Phase 1: Add TEN VAD Infrastructure
- [x] Install TEN VAD dependency: `pip install -U --force-reinstall -v git+https://github.com/TEN-framework/ten-vad.git`
  - ✅ Added TEN VAD to requirements.txt with git URL format
- [x] Add TEN VAD import and initialization in whisper_engine.py
  - ✅ Added safe import with availability check
  - ✅ Added VAD initialization in WhisperEngine.__init__() with error handling
  - ✅ Added vad_enabled parameter to WhisperEngine constructor
- [x] Add VAD pre-check enable/disable config option in config.yaml
  - ✅ Added vad_precheck_enabled: true under whisper section
- [x] Remove sample_rate configurability - hardcode 16kHz throughout app
  - ✅ Updated audio_recorder.py to hardcode 16000 Hz sample rate
  - ✅ Removed sample_rate parameter from AudioRecorder constructor
  - ✅ Updated config.yaml to remove configurable sample_rate
  - ✅ Updated config_manager.py to remove sample_rate validation
  - ✅ Updated whisper-key.py to remove sample_rate parameter passing
- [x] Create method to run TEN VAD check on audio data
  - ✅ Added _check_short_audio_for_speech() method with 2.5s duration check
  - ✅ Integrated VAD pre-check into transcribe_audio() method
  - ✅ Added proper error handling and fallback behavior

### Phase 2: Implement Pre-check Logic
- [ ] Add duration check in transcribe_audio() method
- [ ] Run VAD on short recordings (≤2.5 seconds)
- [ ] Skip transcription if no speech detected
- [ ] Log VAD decisions for debugging

### Phase 3: User Feedback & Testing (one item at a time with user)
- [ ] Add console message when VAD skips transcription
- [ ] Add temporary printed console message with VAD check time (pass or fail)
- [ ] Tweak maximum time to run VAD based on performance costclaude
- [ ] Test with various short recordings (silence, noise, brief speech)
- [ ] Adjust thresholds based on testing

## Implementation Details

### TEN VAD Pre-check Method
```python
def _check_short_audio_for_speech(self, audio_data: np.ndarray) -> bool:
    """
    Check if short audio contains speech using TEN VAD
    Returns True if speech detected, False otherwise
    Note: Audio is always 16kHz (app standard), perfect for TEN VAD
    """
    duration = len(audio_data) / 16000  # Fixed 16kHz sample rate
    
    # Only check recordings 2.5 seconds or shorter
    if duration > 2.5:
        return True  # Assume longer recordings have speech
    
    # Run TEN VAD check (audio already 16kHz - no conversion needed)
    result = self.ten_vad.detect(audio_data)
    speech_detected = any(segment['is_speech'] for segment in result)
    
    return speech_detected
```

### Integration Point
```python
# In transcribe_audio() before main transcription
if not self._check_short_audio_for_speech(audio_data):
    self.logger.info("TEN VAD pre-check: No speech detected in short recording")
    print("No speech detected (recording too short/silent)")
    return None
```

### TEN VAD Initialization
```python
# In WhisperEngine.__init__()
try:
    from ten_vad import TenVad
    self.ten_vad = TenVad()
    self.logger.info("TEN VAD initialized successfully")
except ImportError:
    self.logger.warning("TEN VAD not available, VAD pre-check disabled")
    self.ten_vad = None
```

## Files to Modify

- **src/whisper_engine.py**: Add TEN VAD import, initialization and pre-check logic
- **src/audio_recorder.py**: Remove sample_rate parameter, hardcode 16000
- **config.yaml**: Remove sample_rate config, add VAD pre-check enable/disable
- **src/config_manager.py**: Remove sample_rate validation, add VAD config validation
- **whisper-key.py**: Remove sample_rate config passing
- **requirements.txt**: Add TEN VAD dependency (optional - can install via git)

## Success Criteria

1. Silent recordings ≤2.5 seconds return immediately with "No speech detected" message
2. Short recordings with actual speech are transcribed normally  
3. Processing time for silent short recordings drops from ~1.2s to <50ms (TEN VAD: 5-57ms)
4. No impact on recordings longer than 2.5 seconds
5. User can disable feature via config if needed
6. Higher precision speech detection compared to built-in VAD solutions

## Additional Benefits of TEN VAD

- **Superior accuracy**: Better precision than WebRTC/Silero VAD
- **Consistent performance**: 16kHz audio format matches your current setup perfectly
- **Minimal overhead**: 277KB-2.22MB library size, very fast processing
- **Cross-platform**: Works on Windows (your target platform)