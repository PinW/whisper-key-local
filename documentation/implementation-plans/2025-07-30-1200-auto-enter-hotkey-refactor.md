# Auto-Enter Hotkey Refactor Implementation Plan

As a *user* I want **stop with modifier key** so I can just hit one key to stop recording instead of a combination

As a *user* I want **auto-ENTER key** so I can auto-send transcription for cases where I don't need to edit like LLMs

**Note: Execute one line-item at a time and confirm with user before proceeding to next**
**Note: Update this document as you go, checking off tasks and taking notes needed for later**

## Current State Analysis

Current state:
- Standard hotkey (`ctrl+win`) for record/stop toggle 
- Auto-enter hotkey (`ctrl+shift+win`) with enhanced stop behavior
- Both hotkeys can start AND stop recording
- Auto-enter includes automatic paste + ENTER key on stop
- Stop-with-modifier feature for first modifier key stopping
- Auto-enter hotkey can never be triggered when "stop with modifier" enabled

Desired state:
- Auto-enter hotkey should be stop-only (cannot start recording)
- Default hotkey for auto-enter should be `alt+win` instead of `ctrl+shift+win`
- If stop-with-modifier enabled, auto-enter stops with just `alt` key
- Use existing keyup/down protection logic from stop-modifier feature
- Ignore auto-enter key when not recording (let user know its for stopping only)

## Implementation Plan

### Phase 1: Configuration Updates
- [x] Update default auto-enter hotkey from `ctrl+shift+win` to `alt+win` in config.yaml
  - [x] Update `auto_enter_combination` default value
    - ✅ Changed from `ctrl+shift+win` to `alt+win` in config.yaml:62
  - [x] Update configuration comments to reflect stop-only behavior
    - ✅ Updated comments to clarify "STOP-ONLY recording" behavior in config.yaml:59-61
  - [x] Update documentation to clarify stop-only functionality
    - ✅ Verified project documentation doesn't need updates (auto-enter not specifically documented)

### Phase 2: HotkeyListener Refactor
- [x] Modify auto-enter hotkey behavior to be stop-only
  - [x] Update `_auto_enter_hotkey_pressed()` to check recording state in HotkeyListener
    - ✅ Use `self.state_manager.audio_recorder.get_recording_status()` to check if recording
    - ✅ Return early if not recording (ignore hotkey press)
  - [x] Call `stop_only_recording(use_auto_enter=True)` instead of toggle behavior
    - ✅ Changed from `toggle_recording()` to `stop_only_recording()` with auto-enter flag
  - [x] Add logging to indicate when auto-enter hotkey is ignored
    - ✅ Added debug logging when hotkey ignored due to not recording
    - [x] Let user know auto-enter key is for auto-sending with ENTER only during recording
      - ✅ Updated docstring to clarify "STOP-ONLY hotkey" behavior
  - [x] Integrate with existing stop-modifier protection logic
    - ✅ Added stop-modifier protection check before proceeding

### Phase 3: Stop-Modifier Integration
- [x] Integrate auto-enter with stop-modifier protection logic
  - [x] Apply same `modifier_key_released` protection to auto-enter hotkey
    - ✅ Auto-enter hotkey already had stop-modifier protection in `_auto_enter_hotkey_pressed()`
  - [x] Extract first modifier from auto-enter hotkey for release tracking
    - ✅ Added `auto_enter_modifier_hotkey` attribute initialization in `__init__()`
    - ✅ Added logic in `_setup_hotkeys()` to extract auto-enter modifier with `_extract_first_modifier()`
    - ✅ Added separate auto-enter modifier hotkey registration when different from main modifier
  - [x] Disable auto-enter hotkey if stop-with-modifier enabled and shares same modifier as main hotkey (send message on bootup sequence)
    - ✅ Added conditional logic to detect when modifiers are the same and use shared behavior
    - ✅ Added logging to inform user of shared stop-modifier behavior
  - [x] Ensure auto-enter respects keyup/down protection when stop-modifier enabled
    - ✅ Added `_auto_enter_modifier_hotkey_pressed()` method with same protecthialtion logic as stop-modifier
    - ✅ Added `_auto_enter_modifier_key_released()` method to reset modifier state
  - [x] Use existing `_extract_first_modifier()` logic for consistency
    - ✅ Reused existing `_extract_first_modifier()` method for auto-enter modifier extraction

### Phase 3.5: User Feedback Message Updates
- [x] Update "Press the hotkey again to stop recording." message to be more informative (`src/state_manager.py` line 146)
  - [x] Update default message to show actual hotkey: "Press [HOTKEY] again to stop recording"
    - ✅ Implemented `_generate_stop_instructions()` method in StateManager
  - [x] If "stop-width-modifier" setting is enabled, the [HOTKEY] shows the modifier key
    - ✅ Logic extracts first modifier when stop-with-modifier enabled
  - [x] Dynamic message generation based on current configuration
    - [x] No auto-enter OR auto-paste: "Press [HOTKEY] to stop recording and copy to clipboard"
      - ✅ Implemented conditional logic for no auto-paste scenario
    - [x] Auto-paste on, no auto-enter: "Press [HOTKEY] to stop recording and auto-paste"
      - ✅ Implemented conditional logic for auto-paste only scenario
    - [x] Auto-paste on, auto-enter enabled: "Press [HOTKEY] to stop recording and auto-paste, [HOTKEY2] to also send with ENTER key press" (show modifier only for HOTKEY2 if stop-with-modifier is enabled)
      - ✅ Implemented conditional logic with proper modifier key display for both scenarios

### Phase 4: Code Cleanup and Documentation
- [x] Update method documentation and comments
  - [x] Clarify that auto-enter is stop-only in all relevant docstrings
    - ✅ Updated `_auto_enter_hotkey_pressed()` docstring with clear "STOP-ONLY HOTKEY" documentation
    - ✅ Updated `_auto_enter_modifier_hotkey_pressed()` docstring with stop-only behavior explanation
  - [x] Update configuration comments to reflect new behavior
    - ✅ Updated config.yaml comments to clarify "STOP-ONLY recording" behavior
  - [x] Add code comments explaining the stop-only logic
    - ✅ Added comprehensive documentation explaining auto-enter cannot start recording
- [x] Remove unused start-recording paths for auto-enter
  - [x] Ensure no duplicate start logic remains for auto-enter hotkey
    - ✅ Removed unused `use_auto_enter` parameter from `toggle_recording()` method
    - ✅ Auto-enter hotkeys now exclusively use `stop_only_recording()` method
  - [x] Clean up any conditional logic that's no longer needed
    - ✅ Verified no remaining auto-enter start-recording code paths exist

## Implementation Details

### HotkeyListener Changes
```python
def _auto_enter_hotkey_pressed(self):
    """
    Called when the auto-enter hotkey is pressed
    
    This is a STOP-ONLY hotkey - it only functions when recording is active.
    When not recording, the hotkey press is ignored.
    """
    self.logger.info(f"Auto-enter hotkey pressed: {self.auto_enter_hotkey}")
    
    # Check if currently recording (stop-only behavior)
    if not self.state_manager.is_recording():
        self.logger.debug("Auto-enter hotkey ignored - not currently recording")
        return
    
    # Apply stop-modifier protection if enabled
    if self.stop_with_modifier_enabled and not self.modifier_key_released:
        self.logger.debug("Auto-enter hotkey ignored - waiting for modifier key release")
        return
    
    # Disable stop-modifier until key is released
    self.modifier_key_released = False
    
    try:
        # Stop recording with auto-enter behavior (stop-only)
        self.state_manager.stop_recording_with_auto_enter()
    except Exception as e:
        self.logger.error(f"Error handling auto-enter hotkey press: {e}")
```

### StateManager Changes
```python
def stop_recording_with_auto_enter(self):
    """Stop recording and apply auto-enter behavior (paste + ENTER)"""
    if not self.is_recording():
        self.logger.warning("Cannot stop recording - not currently recording")
        return
    
    # Proceed with enhanced stop behavior
    self._stop_recording_and_process(use_auto_enter=True)
```

### Configuration Updates
```yaml
hotkey:
  # Auto-ENTER hotkey - STOP-ONLY recording with automatic ENTER key press
  # This hotkey ONLY stops recording (cannot start recording)
  # Provides automatic pasting and ENTER key press when stopping
  auto_enter_combination: alt+win
```

### Stop-Modifier Integration Logic
```python
def _setup_hotkeys(self):
    # ... existing code ...
    
    # Add stop-modifier for auto-enter if both features enabled
    if self.stop_with_modifier_enabled and self.auto_enter_enabled:
        auto_enter_modifier = self._extract_first_modifier(self.auto_enter_hotkey)
        if auto_enter_modifier == self.stop_modifier_hotkey:
            # Same modifier - stop-modifier can trigger auto-enter behavior
            self.logger.info(f"Stop-modifier will support auto-enter behavior: {auto_enter_modifier}")
```

## Files to Modify

- **config.yaml**: Update default auto-enter hotkey and documentation
- **src/hotkey_listener.py**: Implement stop-only behavior and stop-modifier integration
- **src/state_manager.py**: Add dedicated `stop_recording_with_auto_enter()` method
- **documentation/project-index.md**: Update workflow documentation to reflect stop-only behavior

## Success Criteria

- [x] Auto-enter hotkey (`alt+win`) only functions when recording is active
- [x] Auto-enter hotkey is ignored when not recording (no error messages)
- [x] Auto-enter hotkey uses same keyup/down protection as stop-modifier
- [x] Default hotkey changed from `ctrl+shift+win` to `alt+win`
- [x] Stop-modifier can trigger auto-enter behavior when appropriate
  - ✅ **TESTED SUCCESSFULLY** - User confirmed auto-enter stop modifier works with ENTER key
- [x] Existing start recording functionality remains unchanged
- [x] Standard hotkey continues to work for both start and stop
- [x] All existing stop-modifier protection logic continues to work

## Testing Strategy

- Test auto-enter hotkey when not recording (should be ignored)
- Test auto-enter hotkey when recording (should stop with ENTER)
- Test stop-modifier integration with auto-enter hotkey
- Test keyup/down protection with auto-enter hotkey
- Verify standard hotkey continues to work for start/stop
- Test configuration loading with new default hotkey
- Verify backward compatibility with existing workflows

---

*Implementation Plan Created: 2025-07-30*
*Target: Stop-only auto-enter hotkey with modifier integration*