# Error Print Statements Analysis

This document catalogs all print statements in the codebase that output error messages, warnings, or failure notifications.

## Main Application Files

### whisper-key.py
- [whisper-key.py:170](whisper-key.py#L170) - `print(f"Error occurred: {e}")`

### src/audio_recorder.py
- [src/audio_recorder.py:60](src/audio_recorder.py#L60) - `print("❌ Failed to start recording!")`

### src/clipboard_manager.py
- [src/clipboard_manager.py:161](src/clipboard_manager.py#L161) - `print("   ✗ Failed to copy text to clipboard")`
- [src/clipboard_manager.py:340](src/clipboard_manager.py#L340) - `print("❌ Auto-paste failed with all methods, text remains in clipboard for manual paste")`
- [src/clipboard_manager.py:378](src/clipboard_manager.py#L378) - `print("❌ Failed to copy transcription to clipboard")`
- [src/clipboard_manager.py:428](src/clipboard_manager.py#L428) - `print("❌ Auto-paste failed with all methods")`
- [src/clipboard_manager.py:541](src/clipboard_manager.py#L541) - `print("❌ Auto-paste failed. Text copied to clipboard - paste with Ctrl+V and press ENTER manually.")`
- [src/clipboard_manager.py:571](src/clipboard_manager.py#L571) - `print("❌ Failed to copy to clipboard!")`

### src/state_manager.py
- [src/state_manager.py:62](src/state_manager.py#L62) - `print(f"⏳ Cannot record while {current_state}...")`
- [src/state_manager.py:104](src/state_manager.py#L104) - `print(f"❌ Error processing recording: {e}")`
- [src/state_manager.py:150](src/state_manager.py#L150) - `print(f"❌ Test failed: {e}")`
- [src/state_manager.py:220](src/state_manager.py#L220) - `print(f"❌ Failed to change model: {message}")`
- [src/state_manager.py:234](src/state_manager.py#L234) - `print(f"❌ Failed to change model: {e}")`

### src/system_tray.py
- [src/system_tray.py:97](src/system_tray.py#L97) - `print(f"   ⚠️ System tray initialization failed: {e}")`
- [src/system_tray.py:492](src/system_tray.py#L492) - `print("   ⚠️ System tray failed to start")`

### src/utils.py
- [src/utils.py:96](src/utils.py#L96) - `print(f"\033[91m{error_message}\033[0m")` - Red colored error output to user

## Tools

### tools/clear_log.py
- [tools/clear_log.py:133](tools/clear_log.py#L133) - `print(f"❌ Error clearing log file: {e}")`
- [tools/clear_log.py:178](tools/clear_log.py#L178) - `print("❌ Log cleanup cancelled.")`

### tools/clear_model_cache.py
- [tools/clear_model_cache.py:136](tools/clear_model_cache.py#L136) - `print(f"❌ Error deleting cache directory: {e}")`
- [tools/clear_model_cache.py:172](tools/clear_model_cache.py#L172) - `print("❌ Cleanup cancelled.")`

### tools/key_helper.py
- [tools/key_helper.py:224](tools/key_helper.py#L224) - `print(f"\n❌ Error: {e}")`
- [tools/key_helper.py:248](tools/key_helper.py#L248) - `print(f"Failed to start Key Helper: {e}")`

### tools/key_helper_alt.py
- [tools/key_helper_alt.py:50](tools/key_helper_alt.py#L50) - `print("\n❌ Error: Could not import 'keycode_checker' from 'global_hotkeys'.")`
- [tools/key_helper_alt.py:53](tools/key_helper_alt.py#L53) - `print(f"\n❌ An unexpected error occurred: {e}")`

### tools/open_user_settings.py
- [tools/open_user_settings.py:74](tools/open_user_settings.py#L74) - `print(f"❌ User settings file not found: {settings_path}")`
- [tools/open_user_settings.py:104](tools/open_user_settings.py#L104) - `print(f"Error: {result.stderr}")`
- [tools/open_user_settings.py:113](tools/open_user_settings.py#L113) - `print(f"❌ Failed to launch {editor_name}: {e}")`
- [tools/open_user_settings.py:118](tools/open_user_settings.py#L118) - `print(f"❌ Error: {e}")`
- [tools/open_user_settings.py:134](tools/open_user_settings.py#L134) - `print("\n❌ Failed to open user settings automatically.")`

### tools/reset_user_settings.py
- [tools/reset_user_settings.py:56](tools/reset_user_settings.py#L56) - `print(f"⚠️  Warning: Could not create backup: {e}")`
- [tools/reset_user_settings.py:85](tools/reset_user_settings.py#L85) - `print("⚠️  Backup failed, but continuing with reset...")`
- [tools/reset_user_settings.py:111](tools/reset_user_settings.py#L111) - `print(f"❌ Error deleting settings file: {e}")`
- [tools/reset_user_settings.py:154](tools/reset_user_settings.py#L154) - `print("❌ Reset cancelled.")`

## Test Files

### tests/run_component_tests.py
- [tests/run_component_tests.py:35](tests/run_component_tests.py#L35) - `print(f"❌ Error: {script_name} not found!")`
- [tests/run_component_tests.py:52](tests/run_component_tests.py#L52) - `print(f"❌ {script_name} failed with exit code {result.returncode}")`
- [tests/run_component_tests.py:59](tests/run_component_tests.py#L59) - `print(f"❌ Error running {script_name}: {e}")`
- [tests/run_component_tests.py:113](tests/run_component_tests.py#L113) - `print("❌ Test had issues. Press Enter to continue anyway, or Ctrl+C to stop...")`
- [tests/run_component_tests.py:144](tests/run_component_tests.py#L144) - `print("❌ Several tests failed. The full app likely won't work correctly.")`

### tests/component/test_audio.py
- [tests/component/test_audio.py:47](tests/component/test_audio.py#L47) - `print("❌ Failed to start recording!")`
- [tests/component/test_audio.py:61](tests/component/test_audio.py#L61) - `print("❌ No audio data was recorded!")`
- [tests/component/test_audio.py:85](tests/component/test_audio.py#L85) - `print(f"❌ Error during audio test: {e}")`
- [tests/component/test_audio.py:119](tests/component/test_audio.py#L119) - `print("❌ Failed to start recording!")`
- [tests/component/test_audio.py:131](tests/component/test_audio.py#L131) - `print("❌ No audio data recorded!")`
- [tests/component/test_audio.py:137](tests/component/test_audio.py#L137) - `print(f"❌ Error in interactive test: {e}")`

### tests/component/test_audio_feedback.py
- [tests/component/test_audio_feedback.py:48](tests/component/test_audio_feedback.py#L48) - `print("❌ Audio feedback is not enabled (likely not on Windows)")`
- [tests/component/test_audio_feedback.py:67](tests/component/test_audio_feedback.py#L67) - `print(f"❌ Error during basic test: {e}")`
- [tests/component/test_audio_feedback.py:95](tests/component/test_audio_feedback.py#L95) - `print("❌ Audio feedback not available")`
- [tests/component/test_audio_feedback.py:109](tests/component/test_audio_feedback.py#L109) - `print(f"❌ Error during missing files test: {e}")`
- [tests/component/test_audio_feedback.py:137](tests/component/test_audio_feedback.py#L137) - `print("❌ Audio feedback not available")`
- [tests/component/test_audio_feedback.py:166](tests/component/test_audio_feedback.py#L166) - `print(f"❌ Error during configuration test: {e}")`
- [tests/component/test_audio_feedback.py:193](tests/component/test_audio_feedback.py#L193) - `print("❌ Audio feedback not available")`
- [tests/component/test_audio_feedback.py:205](tests/component/test_audio_feedback.py#L205) - `print(f"❌ Error during empty configuration test: {e}")`
- [tests/component/test_audio_feedback.py:241](tests/component/test_audio_feedback.py#L241) - `print("❌ Audio feedback not available")`
- [tests/component/test_audio_feedback.py:262](tests/component/test_audio_feedback.py#L262) - `print(f"❌ Error in interactive test: {e}")`

### tests/component/test_clipboard.py
- [tests/component/test_clipboard.py:41](tests/component/test_clipboard.py#L41) - `print("❌ Failed to copy text to clipboard!")`
- [tests/component/test_clipboard.py:59](tests/component/test_clipboard.py#L59) - `print("❌ Failed to retrieve text from clipboard!")`
- [tests/component/test_clipboard.py:65](tests/component/test_clipboard.py#L65) - `print(f"❌ Error during clipboard test: {e}")`
- [tests/component/test_clipboard.py:88](tests/component/test_clipboard.py#L88) - `print("   ❌ Copy with notification failed!")`
- [tests/component/test_clipboard.py:115](tests/component/test_clipboard.py#L115) - `print(f"❌ Error during copy and notify test: {e}")`
- [tests/component/test_clipboard.py:147](tests/component/test_clipboard.py#L147) - `print("❌ Copy failed!")`
- [tests/component/test_clipboard.py:154](tests/component/test_clipboard.py#L154) - `print(f"❌ Error in interactive test: {e}")`
- [tests/component/test_clipboard.py:191](tests/component/test_clipboard.py#L191) - `print(f"❌ Error during clipboard info test: {e}")`
- [tests/component/test_clipboard.py:223](tests/component/test_clipboard.py#L223) - `print("❌ Failed to set original clipboard content!")`
- [tests/component/test_clipboard.py:252](tests/component/test_clipboard.py#L252) - `print("   ❌ Failed to copy transcription")`
- [tests/component/test_clipboard.py:260](tests/component/test_clipboard.py#L260) - `print("   ❌ Transcription not found in clipboard")`
- [tests/component/test_clipboard.py:268](tests/component/test_clipboard.py#L268) - `print("   ❌ Failed to restore original content")`
- [tests/component/test_clipboard.py:276](tests/component/test_clipboard.py#L276) - `print(f"   ❌ Clipboard preservation failed. Expected: '{original_text}', Got: '{final_content}'")`
- [tests/component/test_clipboard.py:284](tests/component/test_clipboard.py#L284) - `print(f"❌ Error during clipboard preservation test: {e}")`

### tests/component/test_hotkeys.py
- [tests/component/test_hotkeys.py:76](tests/component/test_hotkeys.py#L76) - `print("❌ No hotkey presses detected.")`
- [tests/component/test_hotkeys.py:93](tests/component/test_hotkeys.py#L93) - `print(f"❌ Error during hotkey test: {e}")`
- [tests/component/test_hotkeys.py:135](tests/component/test_hotkeys.py#L135) - `print(f"   ❌ {hotkey} not detected (might conflict with other apps)")`
- [tests/component/test_hotkeys.py:142](tests/component/test_hotkeys.py#L142) - `print(f"   ❌ Error with {hotkey}: {e}")`
- [tests/component/test_hotkeys.py:208](tests/component/test_hotkeys.py#L208) - `print(f"❌ Error during cross-application test: {e}")`
- [tests/component/test_hotkeys.py:262](tests/component/test_hotkeys.py#L262) - `print(f"❌ {hotkey} not detected.")`
- [tests/component/test_hotkeys.py:267](tests/component/test_hotkeys.py#L267) - `print(f"❌ Error with '{hotkey}': {e}")`
- [tests/component/test_hotkeys.py:273](tests/component/test_hotkeys.py#L273) - `print(f"❌ Error in interactive test: {e}")`
- [tests/component/test_hotkeys.py:319](tests/component/test_hotkeys.py#L319) - `print("\n⚠️  Basic hotkey test failed. This needs to be resolved before the main app will work.")`

### tests/component/test_whisper.py
- [tests/component/test_whisper.py:49](tests/component/test_whisper.py#L49) - `print(f"❌ Error loading Whisper model: {e}")`
- [tests/component/test_whisper.py:69](tests/component/test_whisper.py#L69) - `print("❌ Cannot proceed without Whisper model!")`
- [tests/component/test_whisper.py:95](tests/component/test_whisper.py#L95) - `print("❌ No audio recorded!")`
- [tests/component/test_whisper.py:115](tests/component/test_whisper.py#L115) - `print("❌ Transcription failed or no speech detected!")`
- [tests/component/test_whisper.py:122](tests/component/test_whisper.py#L122) - `print(f"❌ Error during transcription test: {e}")`
- [tests/component/test_whisper.py:167](tests/component/test_whisper.py#L167) - `print(f"   ❌ Error with {model_size} model: {e}")`
- [tests/component/test_whisper.py:228](tests/component/test_whisper.py#L228) - `print("❌ No speech detected")`
- [tests/component/test_whisper.py:230](tests/component/test_whisper.py#L230) - `print("❌ Recording failed")`
- [tests/component/test_whisper.py:238](tests/component/test_whisper.py#L238) - `print(f"❌ Error in interactive test: {e}")`

## Summary

**Total Error Print Statements Found: 77**

- Main application files: 12
- Tools: 15
- Test files: 50

Most error print statements use red ❌ emoji or ⚠️ warning emoji for visual distinction. The majority of errors are found in test files, which is expected as they exercise error conditions. The main application uses consistent error formatting and includes appropriate user feedback.

---
*Generated on 2025-08-13*