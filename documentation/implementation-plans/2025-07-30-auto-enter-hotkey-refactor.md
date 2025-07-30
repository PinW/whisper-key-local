# Auto-Enter Hotkey Refactor Implementation Plan

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
- [ ] Update default auto-enter hotkey from `ctrl+shift+win` to `alt+win` in config.yaml
  - [ ] Update `auto_enter_combination` default value
  - [ ] Update configuration comments to reflect stop-only behavior
  - [ ] Update documentation to clarify stop-only functionality

### Phase 2: HotkeyListener Refactor
- [ ] Modify auto-enter hotkey behavior to be stop-only
  - [ ] Update `_auto_enter_hotkey_pressed()` to call StateManager directly
  - [ ] StateManager will handle recording state check and ignore if not recording
  - [ ] Add logging to indicate when auto-enter hotkey is ignored
    - [ ] Let user know auto-enter key is for auto-sending with ENTER only during recording

### Phase 3: Stop-Modifier Integration
- [ ] Integrate auto-enter with stop-modifier protection logic
  - [ ] Apply same `modifier_key_released` protection to auto-enter hotkey
  - [ ] Extract first modifier from auto-enter hotkey for release tracking
  - [ ] Disable auto-enter hotkey if stop-with-modifier enabled and shares same modifier as main hotkey (send message on bootup sequence)
  - [ ] Ensure auto-enter respects keyup/down protection when stop-modifier enabled
  - [ ] Use existing `_extract_first_modifier()` logic for consistency

### Phase 4: Code Cleanup and Documentation
- [ ] Update method documentation and comments
  - [ ] Clarify that auto-enter is stop-only in all relevant docstrings
  - [ ] Update configuration comments to reflect new behavior
  - [ ] Add code comments explaining the stop-only logic
- [ ] Remove unused start-recording paths for auto-enter
  - [ ] Ensure no duplicate start logic remains for auto-enter hotkey
  - [ ] Clean up any conditional logic that's no longer needed

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

- [ ] Auto-enter hotkey (`alt+win`) only functions when recording is active
- [ ] Auto-enter hotkey is ignored when not recording (no error messages)
- [ ] Auto-enter hotkey uses same keyup/down protection as stop-modifier
- [ ] Default hotkey changed from `ctrl+shift+win` to `alt+win`
- [ ] Stop-modifier can trigger auto-enter behavior when appropriate
- [ ] Existing start recording functionality remains unchanged
- [ ] Standard hotkey continues to work for both start and stop
- [ ] All existing stop-modifier protection logic continues to work

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