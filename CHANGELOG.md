# Changelog

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),

## [0.2.0] - 2025-08-15

### Added
- Max recording duration with callback-based duration limiting for audio capture
- Intelligent hotkey conflict detection with automatic resolution
- Global exception handling with stderr redirection to app.log
- VAD configuration reorganization into dedicated Voice Activity Detection section
- Instance Manager component (renamed from single_instance.py for consistency)

### Changed
- Massive code reduction: 50% reduction across 11 core files (4,200 → 2,087 lines)
- Complete removal of redundant docstrings and beginner-friendly comments
- Simplified component interfaces and eliminated circular dependencies
- Enhanced build script with improved Start Menu compatibility and asset path resolution
- Updated automation workflow to focus on real issues over defensive programming
- Exception handling standardization across all components
- Import reorganization following PEP 8 standards
- Magic number extraction to named constants
- Component interface simplification with better separation of concerns

### Fixed
- Critical race conditions in transcription pipeline and pending model changes
- Bare except clause that could mask critical exceptions
- Inconsistent OptionalComponent usage in SystemTray type annotations

### Removed
- Entire test suite to focus on shipping over ceremony
- Defensive programming patterns and unnecessary validation
- Windows API clipboard fallback complexity
- Complex model loading progress tracking
- Redundant configuration options and unused settings
- Dead code and unused functions throughout codebase

## [0.1.3] - 2025-08-11

### Added
- Comprehensive CHANGELOG.md for project releases
- Version bump command for Claude AI assistant

### Changed
- Updated build instructions and removed redundant builder.py

### Fixed
- Single instance detector exit error in built executable

## [0.1.2] - 2025-08-11

### Added
- Single-instance detection with mutex to prevent multiple app instances
- TEN VAD (Voice Activity Detection) pre-check system with advanced post-processing
- Audio feedback component for recording events
- PyInstaller packaging system for Windows executable distribution
- Auto-enter hotkey functionality with configurable modifiers
- Stop-with-modifier hotkey functionality
- Alternative keycode checker tool for hotkey configuration
- Context manager for consistent error handling across components

### Changed
- Default Whisper model changed from `tiny` to `base` for better accuracy
- Default hotkeys updated to CTRL+WIN+SPACE (record) and CTRL+WIN+SHIFT+SPACE (stop)
- Renamed `auto_enter_delay` to `key_simulation_delay` for clarity
- Simplified clipboard copy operation for better performance
- Default console logging level set to warning for regular users
- Disabled UPX compression in PyInstaller to reduce antivirus false positives
- Improved system tray model selection to show actual model names
- Streamlined user feedback messages around clipboard actions and startup

### Fixed
- CTRL+C unresponsiveness by adding proper hotkey listener cleanup during shutdown
- Windows key support in hotkey detection
- Auto-enter hotkey now respects auto-paste setting
- Config validation now persists properly to user settings file
- YAML structure corruption by using clean config template
- Unicode logging errors on Windows
- Executable Start Menu launch bug with working directory
- Module imports after directory refactor

### Removed
- `suppress_warnings` config option and related code
- Redundant system tray print statements
- Duplicate "Ready to paste" message

## [0.1.1] - 2025-07-15

### Added
- Complete working whisper speech-to-text application
- Comprehensive configuration system with YAML support
- Interactive key helper utility for hotkey configuration
- Auto-paste feature with Windows API integration
- System tray icon functionality with visual recording status
- User settings system with system tray controls
- Clipboard preservation feature
- Model selection submenu in system tray
- English-specific model options
- Async model loading with responsive system tray
- Tool to clear application log file
- Tool to clear model cache

### Changed
- Refactored project structure and updated documentation
- Renamed main.py to whisper-key.py for better clarity
- Renamed log file from whisper_app.log to app.log
- Updated to use faster-whisper framework
- Improved model download messaging with cache detection

### Fixed
- Module imports and directory structure issues
- System tray menu organization and cleanup

## [0.1.0] - 2025-06-01

### Added
- Initial project setup
- Core speech-to-text functionality
- Basic hotkey detection
- Audio recording capabilities
- Clipboard integration