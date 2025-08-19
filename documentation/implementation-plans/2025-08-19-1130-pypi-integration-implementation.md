# PyPI Package Distribution Implementation Plan

As a *developer/advanced user* I want **to install whisper-key via pip/pipx** so I can easily install and manage it as a global CLI tool

## Current State Analysis

### Existing Architecture
- Well-structured modular codebase in `src/` directory
- Clean entry point in `whisper-key.py`
- Configuration already in proper location (`%APPDATA%\whisperkey\user_settings.yaml`)
- PyInstaller build system working well for .exe distribution
- Version currently hardcoded in build script (v0.2.0)

### Distribution Gaps
- No `pyproject.toml` or `setup.py` for PyPI packaging
- No package structure (`src/whisper_key/__init__.py`)
- Assets bundled for PyInstaller but not for pip packages
- No PyPI account or release automation
- Git-based dependency (ten-vad) incompatible with PyPI

### What's Already Good
- Configuration in AppData means no behavioral changes needed
- Modular architecture ready for packaging
- Clear dependencies in `requirements.txt`
- Windows-specific dependencies properly identified

## Implementation Plan

### Phase 1: Package Structure Setup
- [ ] Create `pyproject.toml` with minimal setuptools configuration
- [ ] Create `src/whisper_key/__init__.py` package initialization
- [ ] Move `whisper-key.py` to `src/whisper_key/main.py`
- [ ] Move assets and config.defaults.yaml to package directory
- [ ] Update imports in moved main.py file
- [ ] Address ten-vad git dependency (make optional or vendor)

### Phase 2: Asset and Path Resolution
- [ ] Update `resolve_asset_path()` in `utils.py` for dual-mode (PyInstaller + pip)
- [ ] Test asset loading with package resources
- [ ] Ensure sounds and icons are accessible from package
- [ ] Verify config.defaults.yaml bundling
- [ ] Update PyInstaller spec file paths for new package structure

### Phase 3: Entry Point Configuration
- [ ] Define console script entry point in pyproject.toml
- [ ] Add `__version__` to package for version management
- [ ] Test global command availability
- [ ] Verify no behavioral changes from existing .exe

### Phase 4: Build and Test
- [ ] Install build tools (`pip install build twine`)
- [ ] Build package with `python -m build`
- [ ] Test local installation with `pip install dist/*.whl`
- [ ] Test with pipx for isolated installation
- [ ] Verify all functionality works as expected

### Phase 5: PyPI Release (Optional/Future)
- [ ] Create PyPI account
- [ ] Test upload to TestPyPI
- [ ] Document installation methods in README
- [ ] Consider automated releases via GitHub Actions

## Implementation Details

### pyproject.toml Structure
```toml
[build-system]
requires = ["setuptools>=61.0", "wheel"]
build-backend = "setuptools.build_meta"

[project]
name = "whisper-key"
version = "0.2.0"
description = "Local faster-whisper speech-to-text app with global hotkeys for Windows"
dependencies = [
    "faster-whisper>=1.1.1",
    "numpy>=1.24.0",
    "sounddevice>=0.4.6",
    "global-hotkeys>=0.1.7; platform_system=='Windows'",
    "pyperclip>=1.8.2",
    "ruamel.yaml>=0.18.14",
    "pywin32>=306; platform_system=='Windows'",
    "pyautogui>=0.9.54; platform_system=='Windows'",
    "pystray>=0.19.5",
    "Pillow>=10.0.0",
    "hf-xet>=1.1.5",
    # Note: ten-vad git dependency handled separately
]

[project.scripts]
whisper-key = "whisper_key.main:main"

[tool.setuptools.packages.find]
where = ["src"]

[tool.setuptools.package-data]
"whisper_key" = ["assets/**/*", "config.defaults.yaml"]
```

### Dual-Mode Asset Resolution Pattern
```python
def resolve_asset_path(relative_path: str) -> str:
    """Resolve asset path for both PyInstaller and pip installations"""
    
    # PyInstaller mode (existing)
    if getattr(sys, 'frozen', False):
        base_dir = Path(sys._MEIPASS)
        return str(base_dir / relative_path)
    
    # pip/pipx installation mode
    try:
        import importlib.resources as pkg_resources
        package = "whisper_key"
        resource_path = Path(relative_path)
        
        # Handle nested paths like "assets/sounds/record_start.wav"
        if resource_path.parts[0] == "assets":
            sub_package = ".".join([package] + list(resource_path.parts[:-1]))
            filename = resource_path.parts[-1]
            
            with pkg_resources.path(sub_package, filename) as path:
                return str(path)
    except (ImportError, FileNotFoundError):
        pass
    
    # Development mode (existing fallback)
    return str(Path(__file__).parent.parent / relative_path)
```

### Package Structure After Changes
```
whisper-key-local/
├── pyproject.toml              # NEW: PyPI package configuration
├── MANIFEST.in                  # NEW: Asset inclusion rules
├── src/
│   └── whisper_key/            # NEW: Package directory (note underscore)
│       ├── __init__.py         # NEW: Package initialization
│       ├── main.py             # MOVED: from whisper-key.py
│       ├── assets/             # MOVED: from root assets/
│       │   ├── sounds/
│       │   └── *.png
│       ├── config.defaults.yaml # MOVED: from root
│       ├── audio_recorder.py   # MOVED: from src/
│       ├── audio_feedback.py   # MOVED: from src/
│       ├── clipboard_manager.py # MOVED: from src/
│       ├── config_manager.py   # MOVED: from src/
│       ├── hotkey_listener.py  # MOVED: from src/
│       ├── instance_manager.py # MOVED: from src/
│       ├── state_manager.py    # MOVED: from src/
│       ├── system_tray.py      # MOVED: from src/
│       ├── utils.py            # MOVED: from src/
│       └── whisper_engine.py   # MOVED: from src/
├── whisper-key.py              # KEEP: Wrapper for backward compatibility
└── py-build/                   # UNCHANGED: PyInstaller build system
```

## Files to Modify

### New Files
- `pyproject.toml` - PyPI package configuration
- `src/whisper_key/__init__.py` - Package initialization with version
- `src/whisper_key/main.py` - Renamed from whisper-key.py

### Modified Files
- `src/utils.py` → `src/whisper_key/utils.py` - Update resolve_asset_path()
- `whisper-key.py` - Keep as thin wrapper for backward compatibility
- All module imports - Update from `src.module` to relative imports
- `py-build/whisper-key.spec` - Update file paths for new package structure

### Unchanged Files
- `requirements.txt` - Keep for reference/development
- Configuration and logging behavior - No changes needed

## Success Criteria

### Functional Requirements
- [ ] `pipx install whisper-key` successfully installs the application
- [ ] `whisper-key` command starts app with system tray (identical to .exe)
- [ ] All hotkeys work as expected
- [ ] Audio recording and transcription function normally
- [ ] Configuration saves to same AppData location
- [ ] System tray icon and menu work correctly

### Technical Requirements
- [ ] PyInstaller build still produces working .exe
- [ ] No behavioral differences between pip and .exe versions
- [ ] Assets (sounds, icons) load correctly in both modes
- [ ] Clean uninstall with `pipx uninstall whisper-key`
- [ ] Package builds with `python -m build`

### Documentation Requirements
- [ ] README updated with pipx installation instructions
- [ ] Installation options clearly explained
- [ ] Note that pipx is recommended over pip

## Notes

### Why Not Poetry?
- Poetry is "best of bad options" with known issues
- Simple setuptools approach is sufficient for our needs
- Avoids additional complexity and tooling requirements

### Why pipx Over pip?
- Automatic isolation prevents dependency conflicts
- Global command availability without environment activation
- Designed specifically for CLI tools like whisper-key
- Cleaner installation and uninstallation

### Future Electron Consideration
- PyPI distribution still valuable for developer/power user segment
- Electron app will eventually serve mainstream users
- Both distribution methods can coexist without conflict

## Risk Mitigation

### Backward Compatibility
- Keep `whisper-key.py` as wrapper to avoid breaking existing workflows
- Update PyInstaller spec file to reflect new package structure
- Test both installation methods thoroughly

### PyInstaller Spec File Updates Required
The existing `py-build/whisper-key.spec` file will need these path updates:
```python
# Current paths that need updating:
# Line 21: [str(project_root / 'whisper-key.py')] 
#   → [str(project_root / 'src' / 'whisper_key' / 'main.py')]
# Line 25: (str(project_root / 'config.defaults.yaml'), '.')
#   → (str(project_root / 'src' / 'whisper_key' / 'config.defaults.yaml'), '.')
# Line 26: (str(project_root / 'assets'), 'assets')
#   → (str(project_root / 'src' / 'whisper_key' / 'assets'), 'assets')
```

### Asset Loading
- Carefully test all asset paths in both modes
- Consider fallback strategies if assets fail to load
- Maintain existing PyInstaller asset bundling

### Platform Constraints
- Clearly mark as Windows-only in PyPI metadata
- Use platform markers for Windows-specific dependencies
- Document Windows requirement prominently