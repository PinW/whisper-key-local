# Packaging with py2exe Implementation Plan

As a **developer** I want **simple packaging system for Windows executables** so I can distribute the whisper-key-local app without requiring Python installation.

*note: this is first implementation of build for an alpha product with no users (will have testers after this is implemented). So it should be elegantly implemented but simple*

## Learnings
- py2exe works best for Windows-specific apps with pywin32 dependencies
- Modern py2exe uses `freeze()` API, not deprecated setup.py method
- PowerShell scripts handle WSL network paths better than batch files
- cmdline_style parameter doesn't exist in current py2exe version

## Implementation Plan

- [ ] Create `build/config.py` - Centralized configuration separating "what" from "how"
    - [ ] Define APP_NAME, APP_VERSION, ENTRY_POINT in config.py
    - [ ] Configure PY2EXE_OPTIONS with includes and packages in config.py
    - [ ] Use glob patterns for automatic asset inclusion (no manual updates needed)
    - [ ] Set up versioned DIST_DIR for clean output organization
- [ ] Create `build/builder.py` - Clean build execution logic importing config
    - [ ] Implement build() function in builder.py with proper exception handling
    - [ ] Add build directory cleanup for fresh builds
    - [ ] Include clear success/failure feedback with emoji indicators
    - [ ] Test basic py2exe build with minimal configuration
- [ ] Create `build/build.ps1` - Enhanced PowerShell orchestration with dependency management
    - [ ] Add -InstallDeps parameter for dependency management
    - [ ] Include environment checks and clear error reporting
    - [ ] Test from WSL network path with robust path handling
    - [ ] Verify executable can run with core functionality

### Asset Bundling and Testing
- [ ] Verify glob-based asset inclusion works correctly
- [ ] Test that Windows APIs work in packaged executable  
- [ ] Test executable on clean Windows machine
- [ ] Document any remaining issues or limitations

### Final Polish
- [ ] Create simple bash wrapper script for WSL: `build.sh` calls PowerShell script
- [ ] Create simple build documentation

## Implementation Details

### Three-File Build Architecture

**Separation of Concerns:**
- `build/config.py` - Defines *what* to build (centralized configuration)
- `build/builder.py` - Defines *how* to build it (execution logic)
- `build/build.ps1` - *Orchestrates* the process (user interface)

### Centralized Configuration (`build/config.py`)
```python
# build/config.py
import pathlib
import glob

# --- General Project Info ---
APP_NAME = "WhisperKey"
APP_VERSION = "0.1.0"
ENTRY_POINT = "whisper-key.py"
ROOT_DIR = pathlib.Path(__file__).parent.parent

# --- Build Output ---
DIST_DIR = ROOT_DIR / f"dist/{APP_NAME}-v{APP_VERSION}"

# --- py2exe Configuration ---
PY2EXE_OPTIONS = {
    "includes": [
        "win32gui", "win32con", "win32clipboard", "global_hotkeys",
        "pystray", "PIL", "sounddevice", "pyperclip"
    ],
    "packages": ["src", "faster_whisper"],
    "bundle_files": 1,  # Creates a more self-contained executable folder
    "optimize": 2,
}

# --- Asset Bundling (using glob for automation) ---
DATA_FILES = [
    # config.defaults.yaml at the root
    ("", [str(ROOT_DIR / "config.defaults.yaml")]),
    # All .png assets
    ("assets", glob.glob(str(ROOT_DIR / "assets/*.png"))),
    # All .wav sound files
    ("assets/sounds", glob.glob(str(ROOT_DIR / "assets/sounds/*.wav"))),
]
```

### Build Execution (`build/builder.py`)
```python
# build/builder.py
import py2exe
import shutil
import sys
from config import APP_NAME, ENTRY_POINT, DIST_DIR, PY2EXE_OPTIONS, DATA_FILES

def build():
    """Executes the py2exe build process."""
    print(f"--- Starting {APP_NAME} Build ---")

    if DIST_DIR.exists():
        print(f"Cleaning previous build directory: {DIST_DIR}")
        shutil.rmtree(DIST_DIR)

    try:
        print("Running py2exe freeze...")
        py2exe.freeze(
            console=[{"script": ENTRY_POINT}],  # Icon optional for now
            options={"py2exe": {**PY2EXE_OPTIONS, "dist_dir": str(DIST_DIR)}},
            data_files=DATA_FILES,
        )
        print(f"\n✅ Build successful!")
        print(f"   Executable located in: {DIST_DIR}")

    except Exception as e:
        print(f"\n❌ Build Failed: {e}")
        sys.exit(1)

if __name__ == "__main__":
    build()
```

### PowerShell Orchestration (`build/build.ps1`)
```powershell
# build/build.ps1
param (
    [switch]$InstallDeps = $false
)

# --- Configuration ---
$RequirementsFile = ".\requirements.txt"
$BuilderScript = ".\build\builder.py"

# --- Main Logic ---
Write-Host "--- Starting WhisperKey Build Process ---" -ForegroundColor Cyan

# 1. Dependency Check
if ($InstallDeps) {
    Write-Host "Installing/updating dependencies from $RequirementsFile..."
    pip install -r $RequirementsFile
    if ($LASTEXITCODE -ne 0) {
        Write-Host "❌ Dependency installation failed." -ForegroundColor Red
        exit 1
    }
}

# 2. Execute Build
Write-Host "Running Python build script..."
python $BuilderScript
if ($LASTEXITCODE -ne 0) {
    Write-Host "❌ Python build script failed." -ForegroundColor Red
    exit 1
}

Write-Host "--- Build process finished. ---" -ForegroundColor Green
```

## Files to Create

### New Files
- `build/config.py` - Centralized build configuration
- `build/builder.py` - Main build script using freeze() API
- `build/build.ps1` - PowerShell orchestration wrapper

### Existing Files
- No modifications to existing app code needed

### Directory Structure After Build
```
project-root/
├── build/              # Build scripts (preserved)
│   ├── config.py
│   ├── builder.py
│   └── build.ps1
└── dist/               # Output directory (cleaned on each build)
    └── WhisperKey-v0.1.0/
        ├── whisper-key.exe
        ├── config.defaults.yaml
        ├── assets/
        └── [dependencies]
```

## Success Criteria
- [ ] `python build/build_py2exe.py` creates working executable
- [ ] Executable runs without Python installation
- [ ] All Windows APIs work (clipboard, hotkeys, system tray)
- [ ] Audio feedback works if sound files present
- [ ] Configuration file loads properly
- [ ] File size under 80MB total (excluding ML models which download separately)
- [ ] Build process works from WSL PowerShell session

## Important Notes

### ML Model Handling
**ML models are NOT included in the build** - faster-whisper automatically downloads models on first use. This keeps the distribution size manageable and ensures users get the latest models.

## Risk Mitigation

### Known Issues and Solutions
- **py2exe parameter errors**: Use only documented freeze() parameters
- **Missing Windows DLLs**: Include Visual C++ redistributable info in docs
- **File size**: Should be reasonable (~50-80MB) since ML models are downloaded separately
- **WSL path issues**: Use PowerShell script that handles UNC paths

### Testing Strategy (with user)
- Test build process in WSL environment (from Windows)
- Test executable on Windows machine without Python
- Verify all core features work in packaged version
- Keep build process simple to reduce failure points