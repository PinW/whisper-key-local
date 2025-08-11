*Generated: Mon Aug 11 17:27:14 CST 2025*

# Code Review Files Metrics

| Component | File | Lines | Methods |
|-----------|------|-------|---------|
| **Core Application Files** |
| Entry Point | `whisper-key.py` | 284 | 2 |
| State Coordination | `src/state_manager.py` | 672 | 22 |
| Configuration | `src/config_manager.py` | 669 | 25 |
| System Tray | `src/system_tray.py` | 554 | 16 |
| Clipboard Operations | `src/clipboard_manager.py` | 522 | 16 |
| Speech Recognition | `src/whisper_engine.py` | 493 | 14 |
| Hotkey Detection | `src/hotkey_listener.py` | 420 | 15 |
| Audio Feedback | `src/audio_feedback.py` | 211 | 10 |
| Audio Capture | `src/audio_recorder.py` | 181 | 8 |
| Utilities | `src/utils.py` | 109 | 3 |
| Single Instance | `src/single_instance.py` | 85 | 3 |
| **Test Suite** |
| Test Runner | `tests/run_component_tests.py` | 157 | 3 |
| Hotkey Tests | `tests/component/test_hotkeys.py` | 321 | 6 |
| Clipboard Tests | `tests/component/test_clipboard.py` | 305 | 5 |
| Audio Feedback Tests | `tests/component/test_audio_feedback.py` | 296 | 5 |
| Whisper Tests | `tests/component/test_whisper.py` | 270 | 4 |
| Audio Tests | `tests/component/test_audio.py` | 157 | 2 |
| **Tools** |
| Key Helper | `tools/key_helper.py` | 255 | 8 |
| Log Cleaner | `tools/clear_log.py` | 187 | 6 |
| Model Cache Cleaner | `tools/clear_model_cache.py` | 181 | 6 |
| Settings Reset | `tools/reset_user_settings.py` | 163 | 4 |
| Settings Opener | `tools/open_user_settings.py` | 139 | 4 |
| Tray Icon Creator | `tools/create_tray_icons.py` | 108 | 3 |
| Alt Key Helper | `tools/key_helper_alt.py` | 56 | 1 |

**Totals:** 6,695 lines across 23 files with 206 methods/functions

The biggest files are `state_manager.py` (672 lines, 22 methods) and `config_manager.py` (669 lines, 25 methods) - these are the architectural backbone.