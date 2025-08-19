# Cancel Recording Hotkey Implementation Plan

As a *user*, I want **cancel recording action** so I can reset if I mess up too much without going through transcription and deleting what was pasted

## Current State Analysis

### Existing Infrastructure
- ✅ `audio_recorder.cancel_recording()` method already exists (src/audio_recorder.py:99)
- ✅ Sophisticated hotkey system using `global-hotkeys` library with conflict detection
- ✅ Comprehensive config management with validation and user settings override
- ✅ Audio feedback system ready for additional sound files
- ✅ State management with thread-safe operations

### Current Cancel Usage
- 🔄 Cancel recording only used during model switching (src/state_manager.py:192)
- 🔄 Uses same stop sound as normal recording completion
- 🔄 No user-accessible cancel hotkey

### Configuration Pattern
- ✅ Hotkeys configured in `config.defaults.yaml` under `hotkey` section
- ✅ User settings override system via `%APPDATA%\whisperkey\user_settings.yaml`
- ✅ Validation via `ConfigValidator.fix_config()`
- ✅ Dynamic hotkey changes supported

## Implementation Plan

### Phase 1: Configuration Setup
- [x] Add `cancel_combination: esc` to `config.defaults.yaml` hotkey section
  - ✅ Added cancel_combination configuration with default value "esc"
  - ✅ Added descriptive comments explaining format and examples
- [x] Update `ConfigValidator.fix_config()` to validate cancel_combination hotkey string
  - ✅ Added cancel_combination validation using existing _validate_hotkey_string method
  - ✅ Validation ensures string format and converts to lowercase for consistency

### Phase 2: Hotkey System Integration
- [x] Extend `HotkeyListener._setup_hotkeys()` to register cancel hotkey
  - ✅ Added cancel_combination parameter to constructor with proper line formatting
  - ✅ Integrated cancel hotkey registration into _setup_hotkeys() method
- [x] Add `_cancel_hotkey_pressed()` callback method to HotkeyListener
  - ✅ Added _cancel_hotkey_pressed() method that calls state_manager.cancel_recording()
  - ✅ Added proper logging for cancel hotkey activation
- [x] Add cancel hotkey to hotkey_configs list with proper priority
  - ✅ Cancel hotkey added to hotkey_configs following existing pattern
  - ✅ Updated change_hotkey_config() to support cancel_combination for dynamic changes

### Phase 3: State Management Integration
- [x] Add public `cancel_recording_hotkey_pressed()` method to StateManager (separate from model-switching logic)
  - ✅ Added state-checking hotkey handler method that validates recording state
  - ✅ Created shared `cancel_active_recording()` method for DRY code reuse
  - ✅ Updated model-switching logic to use shared cancellation method
- [x] Implement state check: only allow cancel during "recording" state
  - ✅ Only cancels when current_state == "recording", ignores otherwise
  - ✅ Returns boolean to indicate if cancel was actually performed
- [x] Add appropriate user feedback for cancel action
  - ✅ Clear "🛑 Recording cancelled" message for user feedback
- [x] Update system tray state transition (recording → idle)
  - ✅ System tray properly transitions from recording to idle state

### Phase 4: Integration & Constructor Updates
- [x] Update HotkeyListener constructor to accept cancel_combination parameter
  - ✅ Added cancel_combination parameter with proper line formatting (completed in Phase 2)
- [x] Update whisper-key.py to pass cancel_combination from config to HotkeyListener
  - ✅ Updated setup_hotkey_listener() to pass cancel_combination from hotkey_config
  - ✅ Integration follows existing pattern with .get() for optional parameter
- [x] Ensure all components properly wire together
  - ✅ Complete configuration chain: defaults → validation → config manager → main app
  - ✅ Complete initialization chain: main → setup_hotkey_listener → HotkeyListener
  - ✅ Complete runtime chain: ESC key → hotkey callback → state manager → cancellation

## Implementation Details

### Configuration Structure
```yaml
hotkey:
  recording_hotkey: ctrl+win
  stop_with_modifier_enabled: true
  auto_enter_enabled: true  
  auto_enter_combination: alt
  cancel_combination: esc  # NEW
```

### HotkeyListener Integration
```python
hotkey_configs.append({
    'combination': self.cancel_combination,
    'callback': self._cancel_hotkey_pressed,
    'name': 'cancel'
})

def _cancel_hotkey_pressed(self):
    self.logger.info(f"Cancel hotkey pressed: {self.cancel_combination}")
    self.state_manager.cancel_recording()
```

### StateManager Cancel Method
```python
def cancel_recording(self):
    current_state = self.get_current_state()
    
    if current_state == "recording":
        self.logger.info("User cancelled recording")
        print("🛑 Recording cancelled")
        
        self.audio_recorder.cancel_recording()
        self.audio_feedback.play_stop_sound()
        self.system_tray.update_state("idle")
    else:
        self.logger.debug(f"Cancel ignored - not recording (state: {current_state})")
```


## Files to Modify

### Configuration Files
- **config.defaults.yaml** - Add `cancel_combination: esc` to hotkey section

### Core Implementation
- **src/config_manager.py** - Add cancel_combination validation in ConfigValidator.fix_config()
- **src/hotkey_listener.py** - Add cancel hotkey registration and callback
- **src/state_manager.py** - Add public cancel_recording() method with state checking

### Integration Points
- **whisper-key.py** - Pass cancel_combination to HotkeyListener constructor

## Success Criteria

### Functional Requirements
- [ ] Escape key (default) cancels recording during recording state
- [ ] Cancel hotkey is configurable in user settings
- [ ] Cancel has no effect in non-recording states (idle, processing, model_loading)
- [ ] System tray updates correctly (recording → idle) on cancel
- [ ] Appropriate user feedback ("🛑 Recording cancelled")

### Technical Requirements  
- [ ] Configuration validation prevents invalid cancel hotkey strings
- [ ] Thread-safe cancel operation
- [ ] Existing hotkey functionality unchanged
- [ ] User settings override works for cancel_combination

### Edge Cases
- [ ] Rapid cancel key presses handled gracefully
- [ ] Cancel during brief recording→processing transition handled correctly
- [ ] Cancel hotkey can be set to complex combinations (e.g., "ctrl+shift+esc")

## Future Enhancements (Out of Scope)
- Distinct cancel sound (separate user story in roadmap)
- Cancel confirmation for long recordings
- Cancel undo functionality