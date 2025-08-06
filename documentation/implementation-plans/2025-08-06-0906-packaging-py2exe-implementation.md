# Packaging with py2exe Implementation Plan

As a **developer** I want **simple packaging system for Windows executables** so I can distribute the whisper-key-local app without requiring Python installation.

## Current State Analysis

### What We've Learned
- py2exe works best for Windows-specific apps with pywin32 dependencies
- Modern py2exe uses `freeze()` API, not deprecated setup.py method
- PowerShell scripts handle WSL network paths better than batch files
- cmdline_style parameter doesn't exist in current py2exe version

### What We Have
- Working app with Windows dependencies (pywin32, global-hotkeys, winsound)
- Clear understanding of required data files (config.yaml, assets/, tools/)
- Knowledge of py2exe compatibility issues and solutions

### Current Issues
- Build process not working due to invalid py2exe parameters
- Build files organization needs to be clean and simple

## Implementation Plan

### Phase 1: Create Working Build Script
- [ ] Create `build/build_py2exe.py` with correct project root path handling
- [ ] Remove invalid `cmdline_style` parameter 
- [ ] Test basic py2exe build with minimal configuration
- [ ] Verify executable can run with core functionality

### Phase 2: Handle Dependencies
- [ ] Add explicit includes for pywin32 modules (win32gui, win32con, win32clipboard)
- [ ] Add global-hotkeys to includes list
- [ ] Handle winsound gracefully (app already has fallbacks)
- [ ] Test that Windows APIs work in packaged executable

### Phase 3: Bundle Assets
- [ ] Include config.yaml in distribution
- [ ] Bundle assets/sounds/ directory for audio feedback
- [ ] Bundle assets/*.png for system tray icons
- [ ] Include tools/ directory for utilities
- [ ] Verify assets are accessible from executable

### Phase 4: Create User-Friendly Build Process
- [ ] Create `build/build.ps1` PowerShell script that calls py2exe script
- [ ] Add dependency checking and installation
- [ ] Add clear success/failure messages
- [ ] Test from WSL network path

### Phase 5: Documentation and Testing
- [ ] Create simple README with build instructions
- [ ] Test executable on clean Windows machine
- [ ] Document any remaining issues or limitations

## Implementation Details

### Build Script Approach
- `build/build_py2exe.py` with `Path(__file__).parent.parent` for project root
- Use py2exe `freeze()` with minimal, tested parameters (no cmdline_style)
- Bundle files approach (bundle_files=3) for Python 3.13 compatibility

### Key Dependencies to Handle
```python
includes = [
    'win32gui',        # Window management
    'win32con',        # Windows constants  
    'win32clipboard',  # Clipboard access
    'global_hotkeys',  # Hotkey detection
    'faster_whisper',  # Core ML functionality
    'sounddevice',     # Audio recording
    'pyperclip',       # Clipboard operations
    'pystray',         # System tray
    'PIL',             # Image processing
]
```

### Data Files Structure
```python
data_files = [
    ('', ['config.yaml']),
    ('assets/sounds', ['assets/sounds/*.wav']),
    ('assets', ['assets/*.png']),
    ('tools', ['tools/*.py']),
]
```

## Files to Modify

### New Files
- `build/build_py2exe.py` - Main build script using freeze() API
- `build/build.ps1` - PowerShell wrapper for easy execution  
- `build/README.md` - Simple build instructions

### Existing Files
- No modifications to existing app code needed

## Success Criteria

- [ ] `python build/build_py2exe.py` creates working executable
- [ ] Executable runs without Python installation
- [ ] All Windows APIs work (clipboard, hotkeys, system tray)
- [ ] Audio feedback works if sound files present
- [ ] Configuration file loads properly
- [ ] File size under 150MB total
- [ ] Build process works from WSL PowerShell session

## Risk Mitigation

### Known Issues and Solutions
- **py2exe parameter errors**: Use only documented freeze() parameters
- **Missing Windows DLLs**: Include Visual C++ redistributable info in docs
- **Large file size**: Expected due to ML dependencies, document this
- **WSL path issues**: Use PowerShell script that handles UNC paths

### Testing Strategy
- Test build process in WSL environment
- Test executable on Windows machine without Python
- Verify all core features work in packaged version
- Keep build process simple to reduce failure points