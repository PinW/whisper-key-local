# Unicode Logging Fix Implementation Plan

As a **developer** I want **to fix Unicode encoding errors in logging messages** so that **error tracebacks don't appear in console and all log messages properly reach the log file**.

**Note: Execute one line-item at a time and confirm with user before proceeding to next**
**Note: Update this document as you go, checking off tasks and taking notes needed for later**

## Current State Analysis

### Problem Identified
- Unicode characters (like `→`) in clipboard content cause `UnicodeEncodeError: 'charmap' codec can't encode character` when logging
- Error tracebacks appear in console but never reach the log file
- Specifically occurs in `src/clipboard_manager.py:361` when logging clipboard content
- Windows console uses cp1252 encoding which can't handle Unicode characters

### Existing Solution Pattern
- Codebase already has a solution in `src/config_manager.py:567-573`
- Uses dual-version approach: ASCII for logging, Unicode/emoji for console display
- Pattern: `ascii_prefix` for logging, `emoji` for console output
- Comment states: "Use ASCII version for logging (avoids Unicode encoding errors on Windows)"

### Current Working Implementation
- `config_manager.py` successfully handles Unicode in settings using dual-version system
- All setting changes use ASCII versions for logging, emoji versions for console
- No Unicode errors in configuration logging

## Implementation Plan (Streamlined for Alpha)

### Core Fix (Execute Immediately)
- [x] Add `sanitize_for_logging()` function to `src/utils.py`
  - ✅ Added function following config_manager.py pattern
  - ✅ Uses `encode('ascii', errors='replace')` approach
  - ✅ Includes fallback to repr() for edge cases
- [x] Import and apply to `src/clipboard_manager.py:361`
  - ✅ Added import statement
  - ✅ Fixed Unicode logging error on line 361-363
- [x] Quick search for other obvious user content logging issues
  - ✅ Found and fixed `whisper_engine.py:273` transcribed text logging
  - ✅ Found and fixed `whisper_engine.py:310` file transcription logging
- [x] Done - ship it

### Deferred for Later (Post-Alpha)
- ~~Extensive testing with various Unicode characters~~
- ~~Systematic codebase scanning~~
- ~~Dual output patterns~~
- ~~Comprehensive verification~~

## Implementation Details

### Utility Function Pattern
Following the existing `config_manager.py` approach:
```python
def sanitize_for_logging(text: str) -> str:
    """
    Sanitize text for logging to avoid Unicode encoding errors on Windows.
    Following the pattern from config_manager.py for ASCII-safe logging.
    """
    if not text:
        return text
    
    try:
        return text.encode('ascii', errors='replace').decode('ascii')
    except Exception:
        return repr(text)[1:-1]  # Remove quotes from repr()
```

### Application Pattern
Replace logging statements containing user content:
```python
# Before (problematic):
self.logger.info(f"Content: '{user_content}'")

# After (safe):
from src.utils import sanitize_for_logging
self.logger.info(f"Content: '{sanitize_for_logging(user_content)}'")
```

### Dual Output Pattern (if needed)
Follow config_manager pattern for important information:
```python
# ASCII version for logging
log_message = f"Content: '{sanitize_for_logging(user_content)}'"
self.logger.info(log_message)

# Unicode version for console (optional)
console_message = f"Content: '{user_content}'"
print(console_message)
```

## Files to Modify

### Primary Files
- `src/utils.py` - Add `sanitize_for_logging()` utility function
- `src/clipboard_manager.py` - Fix line 361 Unicode logging error

### Potential Additional Files (to be confirmed)
- `src/state_manager.py` - If transcription logging has Unicode issues
- `src/whisper_engine.py` - If transcribed text logging has issues
- `src/hotkey_listener.py` - If hotkey logging has Unicode issues
- Any other files that log user-generated content

## Success Criteria

### Primary Success
- [ ] No more `UnicodeEncodeError: 'charmap' codec` tracebacks in console
- [ ] All logging messages successfully reach the log file
- [ ] Clipboard content logging works with Unicode characters

### Secondary Success
- [ ] Console output remains user-friendly and informative
- [ ] Log file content is readable and useful for debugging
- [ ] No regression in existing logging functionality
- [ ] Pattern established for handling future Unicode logging issues

### Test Cases
- [ ] Test with clipboard content containing `→` character (original error case)
- [ ] Test with various Unicode characters: emojis, arrows, special symbols
- [ ] Test with mixed ASCII/Unicode content
- [ ] Verify both empty and null content handling
- [ ] Confirm log file rotation still works properly