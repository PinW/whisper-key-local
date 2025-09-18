# Continuous TEN VAD Monitoring Implementation Plan

As a **User** I want **continuous VAD monitoring during recording with configurable silence detection** so I can prevent silence hallucinations and automatically stop recordings after prolonged silence.

## Current State Analysis

**Existing TEN VAD Integration:**
- TEN VAD already integrated in `whisper_engine.py` with optional component wrapper
- Post-recording VAD processing in `_check_audio_for_speech()` method
- Hysteresis logic implemented for speech/silence transitions
- Fixed configuration: 16kHz sample rate, 256-sample chunks (16ms)
- Thresholds: onset 0.7, offset 0.55, min_speech_duration 0.1s

**Current Workflow:**
- Audio recording → Complete → VAD processing → Transcription
- No real-time silence monitoring during recording
- No automatic stop on prolonged silence

## Implementation Plan

### Phase 1: Core Streaming VAD Infrastructure
- [x] Create reusable `Hysteresis` class in `voice_activity_detection.py` for DRY implementation
  - ✅ Created Hysteresis class with high/low thresholds and speech state tracking
- [x] Create `ContinuousVoiceDetector` class in `voice_activity_detection.py`
  - ✅ Implemented complete ContinuousVoiceDetector with state machine and event system
- [x] Refactor `whisper_engine._detect_speech_with_hysteresis()` to use shared `Hysteresis` class from `voice_activity_detection.py`
  - ✅ Refactored to use shared Hysteresis class while maintaining same behavior
- [x] Implement circular buffer for continuous probability tracking with `deque`
  - ✅ Added probability_buffer as deque with maxlen=frames_for_timeout
- [x] Add consecutive silence frame counting
  - ✅ Implemented silence_frame_count tracking in state machine
- [x] Create robust state machine: WAITING/SPEECH_DETECTED/SILENCE_COUNTING/TIMEOUT_TRIGGERED
  - ✅ Complete state machine with VadState enum and _update_state() method
- [x] Design for `sounddevice` callback thread execution (thread-safe, minimal processing)
  - ✅ Thread-safe design with threading.Lock and minimal processing in process_chunk()
- [x] Add callback mechanism for silence events with thread-safe event dispatch
  - ✅ Event callback system with VadEvent enum and threaded event dispatch

### Phase 2: Configuration System
- [x] Add VAD monitoring settings to `config.defaults.yaml`:
  - ✅ Added `vad_realtime_enabled: true` (enabled by default)
  - ✅ Added `vad_silence_timeout_seconds: 20.0` (already completed in Phase 1)
- [x] Update `config_manager.py` with validation for new settings
  - ✅ Added boolean validation for `vad_realtime_enabled`
  - ✅ Added numeric range validation for `vad_silence_timeout_seconds` (1.0 to 36000.0 seconds)

### Phase 3: Audio Pipeline Integration
- [x] Modify `audio_recorder.py` to instantiate `ContinuousVoiceDetector` from `voice_activity_detection.py` when `vad.mode` is "realtime"
  - ✅ Updated AudioRecorder constructor to accept VAD configuration and whisper_engine reference
  - ✅ Added ContinuousVoiceDetector instantiation when `vad_realtime_enabled` is true
  - ✅ Added VAD event handling callback integration
- [x] Integrate VAD processing directly in `sounddevice` callback thread (`audio_callback`)
  - ✅ Modified audio_callback to process VAD chunks in real-time
  - ✅ Added 256-sample blocksize for optimal TEN VAD processing
  - ✅ Added error handling for VAD processing in callback thread
- [x] Call `ContinuousVoiceDetector.process_chunk()` for each 256-sample audio chunk
  - ✅ Implemented chunk processing with proper audio format handling
  - ✅ Added frame size validation (256 samples) for TEN VAD compatibility
  - ✅ Added audio dimension flattening for correct VAD input format
- [x] Add thread-safe event dispatch from callback to main thread for silence events
  - ✅ Updated main.py setup_audio_recorder to pass VAD configuration
  - ✅ Added StateManager.handle_vad_event() method for processing VAD events
  - ✅ Implemented automatic recording stop on SILENCE_TIMEOUT event
  - ✅ Added VAD state reset on new recording start

### Phase 4: State Management Integration
- [x] Update `state_manager.py` to handle VAD silence events
  - ✅ Added handle_vad_event() method to StateManager class
  - ✅ Added VadEvent import and event type handling
- [x] Add automatic recording stop on silence timeout
  - ✅ Implemented SILENCE_TIMEOUT event handling with automatic stop_recording()
  - ✅ Added user notification message for timeout events
- [x] Implement early transcription trigger for hallucination prevention
  - ✅ Automatic transcription pipeline triggered on silence timeout
  - ✅ Prevents silence hallucinations by stopping recording early
- [x] Add user notification for timeout events
  - ✅ Added console message "⏰ Silence timeout detected - stopping recording"
  - ✅ Added logging for VAD events (INFO for timeout, DEBUG for speech events)
- [x] Ensure existing post-recording VAD still works when `vad.mode` is "precheck"
  - ✅ Verified that WhisperEngine.transcribe_audio() still calls _check_audio_for_speech()
  - ✅ Confirmed both realtime and post-recording VAD can work independently or together
  - ✅ Backward compatibility maintained - existing VAD behavior unchanged
  - ✅ Configuration allows flexible combinations: vad_precheck_enabled + vad_realtime_enabled

### Phase 5: Documentation Updates
- [x] Update `documentation/project-index.md` component architecture table to include `voice_activity_detection.py`
  - ✅ Added Voice Activity Detection component to architecture table with proper description
  - ✅ Added voice_activity_detection.py to project structure section
  - ✅ Updated last modified date to 2025-09-18
- [x] Add continuous VAD monitoring feature description to `README.md`
  - ✅ Added "Voice activity detection" feature to main features list
  - ✅ Enhanced configuration section to mention VAD settings
- [x] Update component responsibilities and key technologies in project index
  - ✅ Listed "Continuous VAD monitoring & silence detection" as primary responsibility
  - ✅ Listed "ten-vad, threading, collections" as key technologies
- [x] Document new configuration options in README
  - ✅ Added VAD configuration mention to README configuration section

## Implementation Details

### Hysteresis Class
```python
class Hysteresis:
    def __init__(self, high_threshold=0.7, low_threshold=0.55):
        self.high_threshold = high_threshold
        self.low_threshold = low_threshold
        self.speech_detected = False
    
    def detect_speech(self, probability):
        if self.speech_detected:
            self.speech_detected = probability > self.low_threshold
        else:
            self.speech_detected = probability > self.high_threshold
        return self.speech_detected
```

### ContinuousVoiceDetector Architecture
```python
class ContinuousVoiceDetector:
    def __init__(self, ten_vad, silence_timeout_sec=20.0):
        self.ten_vad = ten_vad
        self.hysteresis = Hysteresis(high_threshold=0.7, low_threshold=0.55)
        self.silence_frame_count = 0
        self.frames_for_timeout = int(silence_timeout_sec / 0.016)  # 1250 frames for 20s
        self.probability_buffer = deque(maxlen=self.frames_for_timeout)
        self.state = VadState.WAITING
        
    def process_chunk(self, audio_chunk) -> VadEvent:
        probability, _ = self.ten_vad.process(audio_chunk)
        speech_detected = self.hysteresis.detect_speech(probability)
        return self._update_state(speech_detected)
```

### Configuration Schema
```yaml
vad:
  # Voice Activity Detection mode
  # Options: "off", "precheck", "realtime"
  # - off: no VAD processing
  # - precheck: post-recording VAD check
  # - realtime: continuous monitoring during recording
  mode: precheck
  
  # Silence timeout for real-time monitoring (seconds)
  # Only used when mode is "realtime"
  silence_timeout_seconds: 20.0
  
  # VAD thresholds (used by precheck and realtime modes)
  vad_onset_threshold: 0.7
  vad_offset_threshold: 0.55
  vad_min_speech_duration: 0.1
```

### Integration Points
- **Audio Recorder**: Stream audio chunks to VAD monitor during recording
- **State Manager**: Handle VAD events (SILENCE_TIMEOUT, EARLY_SPEECH_END)
- **Whisper Engine**: Dual-mode operation (streaming + post-processing)

### Backward Compatibility
- Keep existing post-recording VAD as default behavior
- Streaming VAD only active when explicitly enabled
- Existing configuration values remain unchanged
- No breaking changes to current workflow

## Files to Modify

**New Files:**
- `src/whisper_key/voice_activity_detection.py` - Core streaming VAD monitor implementation

**Existing Files:**
- `src/whisper_key/config.defaults.yaml` - Add VAD monitoring configuration
- `src/whisper_key/config_manager.py` - Configuration validation and management
- `src/whisper_key/audio_recorder.py` - Integration with streaming VAD
- `src/whisper_key/state_manager.py` - Handle VAD events and workflow changes
- `src/whisper_key/whisper_engine.py` - Dual-mode VAD operation support

## Success Criteria

**Core Functionality:**
- [ ] Continuous VAD monitoring processes audio chunks in real-time during recording
- [ ] Configurable silence timeout (default 20 seconds) automatically stops recording
- [ ] CPU usage remains under 25% with VAD monitoring enabled
- [ ] Memory usage stays minimal with circular buffer management

**Configuration:**
- [ ] VAD monitoring can be enabled/disabled through configuration
- [ ] Silence timeout is user-configurable
- [ ] Settings persist across application restarts

**Integration:**
- [ ] Existing post-recording VAD continues to work when streaming VAD disabled
- [ ] No breaking changes to current user workflow
- [ ] Silence events properly trigger recording stop in state manager
- [ ] System provides clear feedback when timeout occurs