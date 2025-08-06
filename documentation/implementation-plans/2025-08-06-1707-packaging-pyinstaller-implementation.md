# Packaging with PyInstaller Implementation Plan

As a **developer** I want **robust Windows executable packaging with PyInstaller** so I can distribute the whisper-key-local app to alpha testers easily

## Current State Analysis

### What Works
- Application runs perfectly in Python development environment
- All Windows-specific dependencies (pywin32, global-hotkeys, pystray) function correctly
- Complex dependency stack (faster-whisper, numpy, sounddevice) operates reliably
- Asset files (sounds, icons, config) load properly from file system

### What's Needed
- Executable packaging system that works with Python 3.12+
- Clean single-folder distribution for easy sharing
- Windows API functionality maintained in packaged version
- Simple, reliable build process executable from WSL

## Implementation Plan

### Phase 1: Build System Architecture
- [ ] Install PyInstaller in project environment
- [ ] Create py-build/config.py with centralized configuration
- [ ] Implement py-build/builder.py with PyInstaller execution logic
- [ ] Create py-build/build.ps1 for PowerShell orchestration from WSL
- [ ] Add py-build/build.sh wrapper script for bash execution

### Phase 2: Basic PyInstaller Setup and First Build
- [ ] Create basic PyInstaller spec file for whisper-key.py
- [ ] Build minimal executable and verify it launches
- [ ] Test that executable loads basic configuration

### Phase 3: Dependency Detection and Build Improvement
- [ ] Configure PyInstaller to detect all project dependencies automatically
- [ ] Add specific handling for Windows libraries (pywin32, global-hotkeys, pystray)
- [ ] Build updated executable with better dependency handling
- [ ] Test that hotkey detection works in packaged version
- [ ] Verify clipboard operations and system tray functionality

### Phase 4: Asset and Configuration Bundling
- [ ] Configure bundling of assets/ directory (sounds, icons)
- [ ] Include config.defaults.yaml in distribution
- [ ] Test that audio feedback sounds play correctly
- [ ] Verify system tray icons display properly

### Phase 5: Advanced Configuration and Optimization
- [ ] Configure PyInstaller for single-folder distribution
- [ ] Optimize executable size (exclude unnecessary modules like matplotlib, scipy, PIL.ImageQt)
- [ ] Add UPX compression to reduce distribution size
- [ ] Consider --onefile option vs --onedir for final distribution
- [ ] Configure console window visibility (--console for testing, --windowed for production)
- [ ] Handle faster-whisper model download paths correctly
- [ ] Add version information and executable metadata

### Phase 6: Testing and Validation
- [ ] Test build process from WSL environment
- [ ] Verify executable runs on clean Windows machine without Python
- [ ] Test all core functionality (recording, transcription, clipboard, hotkeys)
- [ ] Validate that ML model downloads work correctly on first run

## Implementation Details

### PyInstaller Spec File Configuration
```python
# whisper-key.spec
# -*- mode: python ; coding: utf-8 -*-

import sys
import pathlib

# Project paths
project_root = pathlib.Path.cwd()
src_path = project_root / "src"

a = Analysis(
    ['whisper-key.py'],
    pathex=[str(project_root)],
    binaries=[],
    datas=[
        ('config.defaults.yaml', '.'),
        ('assets', 'assets'),
    ],
    hiddenimports=[
        'win32gui', 'win32con', 'win32clipboard', 'win32api',
        'global_hotkeys',
        'pystray._win32', 'PIL._tkinter_finder',
        'sounddevice', 'numpy.core._methods',
        'faster_whisper', 'ctranslate2',
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=None,
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=None)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name='whisper-key',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=True,  # Keep console for alpha testing
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)

coll = COLLECT(
    exe,
    a.binaries,
    a.zipfiles,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name='whisper-key',
)
```

### Centralized Build Configuration
```python
# py-build/config.py
import pathlib

# Project Information
APP_NAME = "whisper-key"
APP_VERSION = "0.1.0"
ENTRY_POINT = "whisper-key.py"
ROOT_DIR = pathlib.Path(__file__).parent.parent

# Build Output
DIST_DIR = ROOT_DIR / f"dist/{APP_NAME}-v{APP_VERSION}"

# PyInstaller Configuration
SPEC_FILE = pathlib.Path(__file__).parent / f"{APP_NAME}.spec"
BUILD_ARGS = [
    "--clean",                    # Clean build cache
    "--noconfirm",               # Overwrite output without confirmation
    "--onedir",                  # Create one-folder bundle
    f"--distpath={DIST_DIR.parent}",  # Output directory
    f"--specpath={ROOT_DIR}",    # Spec file location
]
```

### Build Execution Logic
```python
# py-build/builder.py
import subprocess
import shutil
import sys
from pathlib import Path
from config import APP_NAME, DIST_DIR, SPEC_FILE, BUILD_ARGS

def build():
    """Execute PyInstaller build process."""
    print(f"🚀 Starting {APP_NAME} build with PyInstaller...")
    
    # Clean previous build
    if DIST_DIR.exists():
        print(f"🧹 Cleaning previous build: {DIST_DIR}")
        shutil.rmtree(DIST_DIR)
    
    # Execute PyInstaller
    try:
        cmd = ["pyinstaller"] + BUILD_ARGS + [str(SPEC_FILE)]
        print(f"📦 Running: {' '.join(cmd)}")
        
        result = subprocess.run(cmd, check=True, capture_output=True, text=True)
        
        print(f"✅ Build successful!")
        print(f"📂 Executable location: {DIST_DIR}")
        print(f"💾 Distribution size: {get_folder_size(DIST_DIR):.1f} MB")
        
    except subprocess.CalledProcessError as e:
        print(f"❌ PyInstaller build failed!")
        print(f"Error output: {e.stderr}")
        sys.exit(1)

def get_folder_size(folder_path):
    """Calculate folder size in MB."""
    total_size = sum(f.stat().st_size for f in Path(folder_path).rglob('*') if f.is_file())
    return total_size / (1024 * 1024)

if __name__ == "__main__":
    build()
```

## Files to Modify

### New Files to Create
- `py-build/whisper-key.spec` - PyInstaller specification file with dependency configuration
- `py-build/config.py` - Centralized build configuration and constants
- `py-build/builder.py` - PyInstaller build execution script with error handling
- `py-build/build.ps1` - PowerShell orchestration script for WSL compatibility
- `py-build/build.sh` - Simple bash wrapper for easy execution

### Existing Files
- `requirements.txt` - Add PyInstaller dependency
- No modifications to existing application code required

### Directory Structure After Implementation
```
whisper-key-local/
├── py-build/                    # Build system (new)
│   ├── config.py               # Build configuration
│   ├── builder.py              # Build execution logic
│   ├── build.ps1               # PowerShell orchestration
│   ├── build.sh                # Bash wrapper
│   └── whisper-key.spec        # PyInstaller specification
├── dist/                       # Build output (generated)
│   └── whisper-key-v0.1.0/    # Versioned distribution folder
│       ├── whisper-key.exe     # Main executable
│       ├── config.defaults.yaml # Default configuration
│       ├── assets/             # Bundled assets
│       └── _internal/          # PyInstaller dependencies
└── [existing project files]    # Unchanged
```

## Success Criteria

### Build Process
- [ ] `./py-build/build.sh` executes successfully from WSL bash
- [ ] Build completes in under 2 minutes
- [ ] No manual dependency configuration required
- [ ] Clean, repeatable build process with clear success/failure feedback

### Executable Functionality  
- [ ] Executable launches without Python installation on clean Windows machine
- [ ] All Windows APIs work correctly (clipboard, hotkeys, system tray)
- [ ] Audio recording and playback function properly
- [ ] Configuration loading works with bundled config.defaults.yaml
- [ ] ML model download and transcription work on first run

### Distribution Quality
- [ ] Single self-contained folder under 100MB (excluding downloaded models)
- [ ] All assets (sounds, icons) load correctly from bundled resources
- [ ] System tray icons display properly
- [ ] Error handling and logging work in packaged version

### Developer Experience
- [ ] Build process works reliably from WSL development environment
- [ ] Clear error messages when build fails
- [ ] Easy to modify build configuration for future changes
- [ ] Build artifacts organized in versioned output folders

## Risk Mitigation

### Known PyInstaller Challenges
- **Large executable size**: Can be 700MB+ with all dependencies; mitigate by excluding unnecessary modules (matplotlib, scipy, PIL.ImageQt) and using UPX compression
- **Console window management**: Use --console for alpha testing (can see errors), --windowed for final release
- **Slow startup time**: Acceptable for alpha testing, can optimize later with --onefile if needed
- **Missing DLLs on target machines**: PyInstaller bundles all dependencies automatically
- **Antivirus false positives**: Expected for any packaged Python executable, document for testers

### Testing Strategy
- Test build process on current WSL development setup
- Validate executable on clean Windows 10 and Windows 11 VMs
- Verify all core functionality works identically to development version
- Test model download and caching behavior in packaged environment

## Post-Implementation Tasks
- [ ] Document build process for future development
- [ ] Create distribution instructions for testers
- [ ] Add build artifacts to .gitignore
- [ ] Consider GitHub Actions integration for automated builds