# State Management Analysis & Improvement Plan

**Note: Execute one line-item at a time and confirm with user before proceeding to next**
**Note: Update this document as you go, checking off tasks and taking notes needed for later**

## Current State Analysis

### Existing Protection ✅
- StateManager.is_processing flag prevents new recordings during transcription
- Recording state tracking via AudioRecorder.is_recording
- System tray state management ("idle", "recording", "processing")
- Hotkey debouncing during processing state

### Critical Gap ❌
- No protection against model changes during active operations
- System tray model selection can interrupt recording/processing without state checks
- WhisperEngine.change_model() has no safety guards in `src/whisper_engine.py:228`
- Race condition risk when switching models during active transcription
- No graceful handling of model changes during recording (should cancel and switch)
- No prevention of new recordings during model loading (should be blocked like processing)

## Implementation Plan

### 1. Enhanced State Management
- [x] Add model_loading state to track model change operations
  - ✅ Added `is_model_loading` flag to StateManager
  - ✅ Updated `toggle_recording()` to check model_loading state
  - ✅ Added `set_model_loading()` method for state management
  - ✅ System tray now shows processing icon during model loading
  - ✅ Model selection menu disabled during model_loading
  - ✅ Added comprehensive state transition logging
- [x] Create atomic state checking methods in StateManager
  - ✅ Added `can_start_recording()` method with thread-safe state checking
  - ✅ Added `can_change_model()` method for model change validation
  - ✅ Added `can_stop_recording()` method for safe recording termination
  - ✅ Added `get_current_state()` method for human-readable state description
- [x] Implement proper state transition guards
  - ✅ Updated `toggle_recording()` to use atomic state checking methods
  - ✅ Added comprehensive state validation with user feedback
  - ✅ Implemented safe state transitions with proper error handling
- [ ] Add model loading progress feedback

### 2. Model Change Protection
- [x] Modify WhisperEngine.change_model() to check StateManager state before proceeding
  - ✅ Added `request_model_change()` method to StateManager with comprehensive state checking
  - ✅ Implemented state-aware model changing logic with safety guards
- [x] **During recording**: Cancel active recording and switch model immediately
  - ✅ Recording cancellation implemented with immediate model switching
  - ✅ User feedback: "Cancelling recording to switch to [model] model..."
- [x] **During processing**: Queue model change until transcription completes (latest model selected wins)
  - ✅ Added `_pending_model_change` queue with atomic handling
  - ✅ Automatic execution of pending model changes after processing completes
- [x] **During model_loading**: Disabled (ignore new requests for model change)
  - ✅ Model change requests ignored during model loading with user feedback
- [x] Add recording cancellation method to AudioRecorder
  - ✅ Added `cancel_recording()` method with proper cleanup
  - ✅ Thread-safe cancellation with resource cleanup
- [x] Provide user feedback: "Recording cancelled - switching to [model]"
  - ✅ Comprehensive user feedback for all model change scenarios
- [x] Show immediate status updates in system tray
  - ✅ System tray state updates integrated with model change workflow

### 3. System Tray Integration Updates
- [x] Update SystemTray._select_model() to handle state-specific behaviors
  - ✅ Replaced direct WhisperEngine calls with StateManager.request_model_change()
  - ✅ Integrated with comprehensive state management system
- [x] **During recording**: Allow model selection, print "Cancelling recording..."
  - ✅ Model selection triggers recording cancellation with user feedback
- [x] **During processing**: Disable model selection when model change queued
  - ✅ Model changes queued during processing with status feedback
- [x] **During model_loading**: Disable model selection
  - ✅ Model selection menu disabled during loading (implemented previously)
- [x] When a model is loading, use the processing icon for system tray
  - ✅ System tray shows processing icon during model loading (implemented previously)

### 4. Thread Safety Improvements
- [x] Implement `threading.Lock` in StateManager for atomic state operations
  - ✅ Added `_state_lock` threading.Lock to StateManager constructor
- [x] Add state transition validation with lock acquisition/release patterns
  - ✅ All state checking methods use context managers with locks
- [x] Use context managers (`with lock:`) for all state-modifying methods
  - ✅ `can_start_recording()`, `can_change_model()`, `can_stop_recording()` use locks
  - ✅ `get_current_state()` and `set_model_loading()` use locks
- [x] Ensure atomic state transitions between idle/recording/processing/model_loading
  - ✅ Critical state transitions in `_stop_recording_and_process()` use locks
  - ✅ Pending model change handling with atomic state transitions
- [x] Prevent race conditions between recording and model changes
  - ✅ Thread-safe state checking prevents race conditions
  - ✅ Atomic state transitions with proper lock management

## Implementation Details

### StateManager Threading Pattern
```python
import threading

class StateManager:
    def __init__(self):
        self._state_lock = threading.Lock()
        self._pending_model_change = None
        
    def transition_to_state(self, new_state):
        with self._state_lock:
            # Validate transition is allowed
            # Update state atomically
            # Process pending model changes if returning to idle
```

### Model Change Logic by State
- **idle**: Change model immediately
- **recording**: Cancel recording, change model immediately
- **processing**: Queue model change (latest request wins)
- **model_loading**: Ignore new model change requests

### Recording Cancellation System
- AudioRecorder.cancel_recording() method
- Clean buffer disposal and resource cleanup
- User notification: "Recording cancelled for model switch"
- Automatic model change after cancellation

## Files to Modify

1. **src/state_manager.py** - Add model_loading state, threading.Lock, and state-aware model changing
2. **src/audio_recorder.py** - Add cancel_recording() method for clean cancellation
3. **src/whisper_engine.py** - Add state-aware change_model() with recording cancellation
4. **src/system_tray.py** - Update model selection logic with immediate/queued behaviors