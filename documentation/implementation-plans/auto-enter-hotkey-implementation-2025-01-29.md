# Auto-ENTER Hotkey Implementation Plan

**Note: Execute one line-item at a time and confirm with user before proceeding to next**
**Note: Update this document as you go, checking off tasks and taking notes needed for later**

## Current State Analysis

The application currently supports:
- Single hotkey for record/stop toggle (default: CTRL+`)
- Configurable auto-paste functionality after transcription
- Key simulation through pyautogui for clipboard operations

Missing functionality:
- Enhanced stop recording hotkey that includes auto-ENTER after paste
- Streamlined workflow for chat/messaging applications
- Single-action record → transcribe → paste → submit workflow

## Implementation Plan

### Phase 1: Configuration Setup ✅ COMPLETED
- [x] Add `auto_enter_hotkey` configuration to config.yaml under hotkey section
  - ✅ Added `auto_enter_combination: ctrl+shift+`` to hotkey section
  - ✅ Added `auto_enter_enabled: true` boolean flag
  - ✅ Added `auto_enter_delay: 0.1` for timing control
  - ✅ Added comprehensive comments explaining functionality
- [x] Set default combination to `ctrl+shift+grave` (CTRL+SHIFT+~)
  - ✅ Set default to `ctrl+shift+`` (backtick key with shift modifier)
  - ✅ Documented in config.yaml with usage explanation
- [x] Add configuration validation for the secondary hotkey
  - ✅ Added validation for `auto_enter_enabled` (boolean check)
  - ✅ Added validation for `auto_enter_delay` (numeric, non-negative)
  - ✅ Added validation for `auto_enter_combination` (string format)
  - ✅ Added conflict detection between main and auto-enter hotkeys
- [x] Update ConfigManager to handle the new hotkey setting
  - ✅ Enhanced `_validate_config()` method with auto-enter validation
  - ✅ Added display info mapping for auto-enter settings
  - ✅ All settings properly validated and defaulted

### Phase 2: Hotkey Detection Enhancement ✅ COMPLETED
- [x] Extend HotkeyListener to support multiple hotkey combinations
  - ✅ Modified `__init__` to accept `auto_enter_hotkey` and `auto_enter_enabled` parameters
  - ✅ Updated `_setup_hotkeys()` to handle multiple hotkey configurations
  - ✅ Implemented generic hotkey collection and processing system
- [x] Add registration for the auto-enter hotkey alongside existing recording hotkey
  - ✅ Both hotkeys registered in `hotkey_bindings` array
  - ✅ Auto-enter hotkey only registered when enabled and configured
  - ✅ Proper logging for both hotkey registrations
- [x] Implement callback handling to distinguish between standard and auto-enter hotkeys
  - ✅ Created `_standard_hotkey_pressed()` for standard recording behavior
  - ✅ Created `_auto_enter_hotkey_pressed()` for enhanced recording with auto-enter
  - ✅ Removed old generic `_hotkey_pressed()` method
  - ✅ Each callback calls `state_manager.toggle_recording()` with appropriate parameters
- [x] Add hotkey conflict detection between recording and auto-enter keys
  - ✅ Implemented `_get_hotkey_specificity()` method for automatic priority sorting
  - ✅ Hotkeys automatically sorted by modifier count (more modifiers = higher priority)
  - ✅ Generic solution works with any hotkey combinations, not hardcoded
  - ✅ CTRL+SHIFT+` automatically takes priority over CTRL+` regardless of configuration

### Phase 3: Auto-ENTER Functionality
- [ ] Add `send_enter_key()` method to ClipboardManager
- [ ] Implement ENTER key simulation using pyautogui
- [ ] Add configurable delay before ENTER key press
- [ ] Include error handling for key simulation failures

### Phase 4: State Management Integration
- [ ] Add auto-enter hotkey handler to StateManager
- [ ] Implement shared start recording logic for both hotkeys
- [ ] Implement enhanced stop recording for auto-enter hotkey (stop + force auto-paste + ENTER)
- [ ] Implement standard stop recording for regular hotkey (stop + respect auto-paste config)
- [ ] Handle auto-paste config override logic for auto-enter hotkey
- [ ] Add user feedback message for auto-ENTER

### Phase 5: User Experience Enhancements
- [ ] Add system tray menu option to enable/disable auto-enter hotkey
- [ ] Update tooltips and notifications to mention both hotkeys
- [ ] Add logging for auto-enter hotkey usage
- [ ] Include auto-enter hotkey in key_helper.py tool

## Implementation Details

### Configuration Structure
```yaml
hotkey:
  combination: "ctrl+grave"           # Existing recording hotkey
  auto_enter_combination: "ctrl+shift+grave"  # New auto-enter hotkey
  auto_enter_enabled: true            # Enable/disable feature
  auto_enter_delay: 0.1              # Delay before ENTER (seconds)
```

### Key Technical Patterns
- Extend existing hotkey registration pattern in HotkeyListener
- Use pyautogui.press('enter') for key simulation
- Implement shared start recording logic and differentiated stop recording logic
- Handle auto-paste configuration override for auto-enter hotkey
- Follow existing error handling patterns with graceful fallbacks

### User Workflow

**Both hotkeys can start and stop recording:**
- **CTRL+`** (standard): Start recording OR stop recording + respect auto-paste config
- **CTRL+SHIFT+~** (auto-enter): Start recording OR stop recording + force auto-paste + ENTER

**Standard workflow:**
1. User presses CTRL+` to start recording
2. User presses CTRL+` to stop recording
3. Transcription is copied to clipboard (and auto-pasted if enabled in config)

**Enhanced workflow:**
1. User presses CTRL+` (or CTRL+SHIFT+~) to start recording
2. User presses CTRL+SHIFT+~ to stop recording + force auto-paste + send ENTER
3. System confirms action with brief notification

**Auto-paste Configuration Override:**
- Standard hotkey respects the `auto_paste` configuration setting
- Auto-enter hotkey ignores the `auto_paste` setting and always pastes (required for ENTER functionality)

**Key Point:** The auto-enter hotkey provides identical start functionality but enhanced stop functionality (includes automatic ENTER key press).

## Files to Modify

- **config.yaml**: Add auto-enter hotkey configuration section
- **src/config_manager.py**: Extend validation for new hotkey settings
- **src/hotkey_listener.py**: Add secondary hotkey registration and callback handling
- **src/clipboard_manager.py**: Add ENTER key simulation method
- **src/state_manager.py**: Integrate auto-enter functionality with existing workflow
- **src/system_tray.py**: Add menu option and notification updates
- **tools/key_helper.py**: Include auto-enter hotkey in configuration tool

## Success Criteria

- [ ] CTRL+SHIFT+~ sends ENTER key to active window
- [ ] Both hotkeys can start/stop recording with identical start behavior
- [ ] Auto-enter hotkey provides enhanced stop recording (stop + force paste + ENTER)
- [ ] Standard hotkey respects auto-paste configuration setting
- [ ] Auto-enter hotkey ignores auto-paste configuration (always pastes)
- [ ] Configuration allows customization of hotkey combination
- [ ] System tray provides toggle control for the feature
- [ ] No conflicts with existing recording hotkey
- [ ] Graceful error handling if key simulation fails

## Testing Strategy

- Test hotkey detection and key simulation on Windows
- Verify enhanced stop recording behavior with various applications
- Test auto-paste configuration override behavior
- Test both hotkeys with auto-paste disabled in config
- Test hotkey conflict scenarios
- Validate configuration loading and validation
- Test system tray menu integration

---

*Implementation Plan Created: 2025-07-29*
*Target Completion: TBD*