# Issue #15 GPU Mode Fix - Permanent Solution Report

## Executive Summary

**Problem**: Users with NVIDIA GPUs experience crashes when enabling `device: cuda` in settings. The app fails silently or with cuDNN DLL errors.

**Root Cause**: The `faster-whisper` library depends on CTranslate2, which requires NVIDIA cuDNN 9 DLLs that are not automatically installed or included in the PyInstaller build.

**Impact**: GPU acceleration is effectively broken for end users without manual intervention, making the feature unusable out-of-the-box.

## Current Workaround (From Issue #15)

Users must manually execute these steps:

```powershell
# Step 1: Install NVIDIA packages
pip install nvidia-cudnn-cu12 nvidia-cublas-cu12 nvidia-cufft-cu12

# Step 2: Add DLL paths to system PATH
$nvidiaPath = python -c "import nvidia.cudnn; print(nvidia.cudnn.__path__[0])" | Split-Path
[System.Environment]::SetEnvironmentVariable(
    "PATH",
    "$nvidiaPath\cudnn\bin;$nvidiaPath\cublas\bin;$nvidiaPath\cufft\bin;" + [System.Environment]::GetEnvironmentVariable("PATH", "User"),
    "User"
)

# Step 3: Restart app
```

This workaround is confirmed working on RTX 3070, RTX 4050, and RTX 4090.

## Root Cause Analysis

### Dependency Chain
1. `whisper-key-local` depends on `faster-whisper`
2. `faster-whisper` depends on `ctranslate2` for GPU acceleration
3. `ctranslate2` requires NVIDIA CUDA runtime DLLs (cudnn, cublas, cufft) at runtime
4. These DLLs are NOT automatically installed by pip or included in PyInstaller builds

### Current State
- **PyPI Installation** (`pyproject.toml`): Does not include NVIDIA packages in dependencies
- **PyInstaller Build** (`whisper-key.spec`): Does not bundle NVIDIA DLLs
- **Build Script** (`build-windows.ps1`): References non-existent `requirements.txt` (line 91)
- **Error Handling**: No graceful degradation or helpful error messages when CUDA fails

### Why This Happens
The NVIDIA packages (`nvidia-cudnn-cu12`, etc.) are distributed as Python wheels that contain native DLLs. When installed via pip, these DLLs are placed in the Python site-packages directory but are NOT automatically added to the system PATH. PyInstaller doesn't automatically detect or bundle these optional GPU dependencies.

## Permanent Solution Options

### Option 1: Add NVIDIA Packages as Optional Dependencies (Recommended)

**Approach**: Declare NVIDIA packages as optional extras in `pyproject.toml`

**Implementation**:
```toml
[project.optional-dependencies]
cuda = [
    "nvidia-cudnn-cu12>=9.0.0",
    "nvidia-cublas-cu12>=12.0.0",
    "nvidia-cufft-cu12>=11.0.0",
]
```

**Installation**:
```bash
# For CPU-only users
pip install whisper-key-local

# For GPU users
pip install whisper-key-local[cuda]
```

**Pros**:
- Standard Python packaging practice
- Users choose what they need (smaller install for CPU-only)
- Automatic DLL management via pip
- Works for both development and pip installations

**Cons**:
- Doesn't help PyInstaller builds (separate solution needed)
- Users must know to install with `[cuda]` extra
- Requires clear documentation

### Option 2: Bundle NVIDIA DLLs in PyInstaller Build

**Approach**: Modify `whisper-key.spec` to detect and bundle NVIDIA DLLs

**Implementation**:
```python
# In whisper-key.spec
import pathlib
import site

# Detect NVIDIA DLL paths
nvidia_binaries = []
for site_dir in site.getsitepackages():
    nvidia_base = pathlib.Path(site_dir) / 'nvidia'
    if nvidia_base.exists():
        for lib in ['cudnn', 'cublas', 'cufft']:
            dll_dir = nvidia_base / lib / 'bin'
            if dll_dir.exists():
                for dll in dll_dir.glob('*.dll'):
                    nvidia_binaries.append((str(dll), '.'))

# Add to Analysis
a = Analysis(
    ...,
    binaries=nvidia_binaries,
    ...
)
```

**Pros**:
- Works out-of-the-box for end users of the exe
- No manual PATH configuration needed
- Single-file distribution includes everything

**Cons**:
- Significantly increases build size (~400MB+ of DLLs)
- All users download GPU DLLs even if using CPU
- Requires NVIDIA packages installed in build environment
- License compliance considerations (redistributing NVIDIA DLLs)

### Option 3: Runtime DLL Discovery + Better Error Handling

**Approach**: Detect missing DLLs at runtime and provide actionable error messages

**Implementation**:
```python
# In whisper_engine.py
def validate_cuda_availability(self):
    """Check if CUDA is actually usable"""
    if self.device == "cuda":
        try:
            import ctranslate2
            # Try to initialize a dummy translator to test CUDA
            test = ctranslate2.Translator("dummy", device="cuda")
        except Exception as e:
            if "cudnn" in str(e).lower():
                raise RuntimeError(
                    "CUDA mode requires NVIDIA cuDNN libraries.\n"
                    "Install with: pip install nvidia-cudnn-cu12 nvidia-cublas-cu12 nvidia-cufft-cu12\n"
                    "See: https://github.com/PinW/whisper-key-local#gpu-support"
                )
            raise
```

**Pros**:
- Helps users diagnose problems
- Provides clear fix instructions
- Minimal code changes

**Cons**:
- Doesn't prevent the issue, just explains it
- Users still need manual intervention
- Not a complete solution

### Option 4: Automatic DLL Discovery via Runtime Hook

**Approach**: Create a PyInstaller runtime hook that adds NVIDIA DLL paths to PATH automatically

**Implementation**:
```python
# In py-build/hooks/runtime_hook_nvidia.py
import os
import sys
import pathlib

def add_nvidia_dlls_to_path():
    """Add NVIDIA DLL directories to PATH at runtime"""
    if getattr(sys, 'frozen', False):
        # Running in PyInstaller bundle
        bundle_dir = pathlib.Path(sys._MEIPASS)
        # Add potential DLL locations to PATH
        nvidia_paths = [
            bundle_dir / 'nvidia' / 'cudnn' / 'bin',
            bundle_dir / 'nvidia' / 'cublas' / 'bin',
            bundle_dir / 'nvidia' / 'cufft' / 'bin',
        ]
        for path in nvidia_paths:
            if path.exists():
                os.environ['PATH'] = str(path) + os.pathsep + os.environ['PATH']

add_nvidia_dlls_to_path()
```

**Pros**:
- Automatic PATH management for bundled builds
- Works seamlessly for end users
- No manual configuration

**Cons**:
- Still requires bundling DLLs (Option 2)
- Adds complexity to the build process

## Recommended Solution: Hybrid Approach

Implement **Options 1 + 2 + 3** together:

### Phase 1: Fix PyPI Installation (Immediate)
1. Add NVIDIA packages as optional dependencies in `pyproject.toml`
2. Update README with clear GPU installation instructions
3. Release as patch version (0.3.3)

### Phase 2: Improve PyInstaller Build (Short-term)
1. Create separate build targets: `whisper-key-cpu.exe` and `whisper-key-gpu.exe`
2. GPU build bundles NVIDIA DLLs using modified `.spec` file
3. Update build script to generate both versions
4. Document which build users should download

### Phase 3: Better Error Handling (Short-term)
1. Add CUDA validation in `whisper_engine.py` initialization
2. Provide clear error messages with links to documentation
3. Consider automatic fallback to CPU if CUDA fails

## Implementation Steps

### Step 1: Fix `pyproject.toml`
```toml
[project]
# ... existing config ...
dependencies = [
    "faster-whisper>=1.1.1",
    # ... existing dependencies ...
]

[project.optional-dependencies]
cuda = [
    "nvidia-cudnn-cu12>=9.0.0",
    "nvidia-cublas-cu12>=12.0.0",
    "nvidia-cufft-cu12>=11.0.0",
]
```

### Step 2: Create `requirements.txt`
The build script expects this file but it doesn't exist. Generate it:
```bash
pip freeze > requirements.txt
```

Or better, create it dynamically from `pyproject.toml` dependencies.

### Step 3: Create GPU-Specific Build Script
```powershell
# py-build/build-windows-gpu.ps1
param([switch]$NoZip)

# Install GPU dependencies before building
& pip install nvidia-cudnn-cu12 nvidia-cublas-cu12 nvidia-cufft-cu12

# Use GPU-specific spec file
& pyinstaller whisper-key-gpu.spec --distpath dist/whisper-key-gpu --clean
```

### Step 4: Create `whisper-key-gpu.spec`
Copy `whisper-key.spec` and add NVIDIA DLL bundling logic (see Option 2).

### Step 5: Update Documentation
- README.md: Add GPU installation section
- CHANGELOG.md: Document the fix
- Create troubleshooting guide for GPU issues

### Step 6: Add Runtime Validation
```python
# In src/whisper_key/whisper_engine.py
def __init__(self, ...):
    self.device = device
    if device == "cuda":
        self._validate_cuda()
    # ... rest of init

def _validate_cuda(self):
    """Validate CUDA is actually available and working"""
    try:
        import torch
        if not torch.cuda.is_available():
            logger.warning("CUDA requested but not available, falling back to CPU")
            self.device = "cpu"
            return
    except ImportError:
        pass  # torch not required, continue

    try:
        # Test if ctranslate2 can actually use CUDA
        import ctranslate2
        info = ctranslate2.get_cuda_device_count()
        if info == 0:
            raise RuntimeError("No CUDA devices found")
    except Exception as e:
        if "cudnn" in str(e).lower():
            raise RuntimeError(
                "CUDA mode requires NVIDIA cuDNN libraries.\n\n"
                "For pip installation, reinstall with GPU support:\n"
                "  pip install whisper-key-local[cuda]\n\n"
                "For standalone executable, download the GPU build:\n"
                "  https://github.com/PinW/whisper-key-local/releases\n\n"
                f"Original error: {e}"
            )
        raise
```

## Additional Considerations

### 1. Documentation Updates

**README.md** should include:
```markdown
## GPU Support (NVIDIA only)

### PyPI Installation
For GPU acceleration with NVIDIA GPUs:

```bash
pip install whisper-key-local[cuda]
```

This installs the required NVIDIA CUDA libraries (cuDNN, cuBLAS, cuFFT).

### Standalone Executable
Download the appropriate build:
- `whisper-key-v0.3.3-windows-cpu.zip` - CPU only (smaller, works everywhere)
- `whisper-key-v0.3.3-windows-gpu.zip` - NVIDIA GPU support (larger, requires compatible GPU)

### System Requirements for GPU Mode
- Windows 10/11
- NVIDIA GPU with CUDA support (GTX 900 series or newer)
- Latest NVIDIA drivers

### Troubleshooting GPU Mode
If GPU mode crashes, try:
1. Update NVIDIA drivers
2. Verify GPU is CUDA-capable
3. Check Windows Event Viewer for DLL errors
4. Fall back to CPU mode if issues persist
```

### 2. License Compliance
Redistributing NVIDIA DLLs in the PyInstaller build may require:
- Reviewing NVIDIA's redistribution license
- Including NVIDIA license notices in the distribution
- Considering legal implications

Check: https://docs.nvidia.com/cuda/eula/

### 3. Build Size Impact
Current CPU build: ~400MB
GPU build estimate: ~800MB+ (400MB NVIDIA DLLs + existing)

Consider:
- Separate release artifacts (CPU vs GPU builds)
- Clear naming to help users choose
- Document size differences

### 4. Testing Strategy
Before release:
- Test CPU build on clean Windows VM (no NVIDIA drivers)
- Test GPU build on multiple NVIDIA GPUs (3000/4000 series)
- Test PyPI installation with `[cuda]` extra
- Verify error messages are helpful
- Test automatic fallback to CPU

### 5. AMD GPU Support
Note: AMD GPUs (like the 7900 XTX mentioned in issue #15) are NOT supported by CUDA. ROCm support would require:
- Different build of `faster-whisper`/`ctranslate2`
- ROCm runtime DLLs
- Significant additional complexity

Recommendation: Document that only NVIDIA GPUs are supported, or explore alternative inference backends (ONNX Runtime with DirectML).

## Estimated Effort

| Task | Time | Priority |
|------|------|----------|
| Add optional dependencies | 5 min | High |
| Create requirements.txt | 5 min | High |
| Update README documentation | 30 min | High |
| Add runtime CUDA validation | 1 hour | High |
| Create GPU build script | 1 hour | Medium |
| Modify spec for DLL bundling | 2 hours | Medium |
| Test on multiple GPUs | 2 hours | Medium |
| Update CHANGELOG | 15 min | Medium |
| Create troubleshooting docs | 1 hour | Low |

**Total**: ~8 hours of development + testing

## Conclusion

The current GPU mode issue stems from missing NVIDIA cuDNN DLLs that are not automatically included in either pip installations or PyInstaller builds. The recommended hybrid solution involves:

1. **Immediate fix**: Add optional CUDA dependencies for pip users
2. **Short-term fix**: Create separate CPU/GPU builds with bundled DLLs
3. **Long-term improvement**: Better error handling and automatic fallback

This approach balances user experience, build complexity, and maintenance burden while ensuring GPU mode "just works" for end users without manual PATH configuration.

## References

- Issue #15: https://github.com/PinW/whisper-key-local/issues/15
- CTranslate2 CUDA requirements: https://opennmt.net/CTranslate2/installation.html
- NVIDIA CUDA Toolkit: https://developer.nvidia.com/cuda-toolkit
- PyInstaller binary bundling: https://pyinstaller.org/en/stable/spec-files.html#adding-binary-files
