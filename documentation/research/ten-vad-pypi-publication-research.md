# Ten-VAD PyPI Publication Research

**Date**: 2025-08-19  
**Purpose**: Document process for forking and publishing ten-vad to PyPI to resolve git dependency issue in whisper-key

## Problem Statement

The ten-vad library is currently only available via git installation:
```bash
pip install git+https://github.com/TEN-framework/ten-vad.git@v1.0-ONNX
```

This prevents PyPI publication of whisper-key since PyPI doesn't allow git-based dependencies. Solution is to fork ten-vad and publish it to PyPI ourselves.

## Legal Analysis

**License**: Apache 2.0 with additional restrictions
- ✅ Allows redistribution and modification
- ✅ Permits forking and republishing 
- ❌ Prohibits competing with Agora's offerings
- ✅ Our use case (making library easily installable) is not competitive

**Conclusion**: Legal to fork and publish for easier installation access.

## Current State of ten-vad Repository

### What's Already Good
- ✅ Working `setup.py` with cross-platform native library handling
- ✅ Clear package name (`ten_vad`)
- ✅ Working installation process with platform-specific binaries
- ✅ Good README documentation
- ✅ Apache 2.0 license file
- ✅ Requirements.txt with dependencies

### Missing for PyPI Publication
- ❌ Package metadata (author, description, URL)
- ❌ Long description from README
- ❌ Dependencies specification in setup.py
- ❌ Version management strategy
- ❌ PyPI classifiers for discoverability

## Publication Strategy Options

### Option 1: Minimal setup.py Fix (Quick)
Keep existing setup.py but add missing metadata:

```python
setup(
    name="ten-vad",
    version="1.0.0",
    description="High-performance real-time voice activity detection",
    long_description=open("README.md").read(),
    long_description_content_type="text/markdown",
    author="TEN Framework",
    author_email="contact@agora.io",  # Or maintainer email
    url="https://github.com/TEN-framework/ten-vad",
    license="Apache 2.0",
    install_requires=[
        "numpy",
        "scipy",
    ],
    python_requires=">=3.8",
    classifiers=[
        "Development Status :: 4 - Beta",
        "Intended Audience :: Developers", 
        "License :: OSI Approved :: Apache Software License",
        "Operating System :: OS Independent",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
        "Topic :: Multimedia :: Sound/Audio :: Speech",
        "Topic :: Scientific/Engineering :: Artificial Intelligence",
    ],
    # Keep existing package and data configurations
)
```

### Option 2: Modern pyproject.toml Conversion (Recommended)
Replace setup.py entirely with modern configuration:

```toml
[build-system]
requires = ["setuptools>=61.0", "wheel"]
build-backend = "setuptools.build_meta"

[project]
name = "ten-vad"
version = "1.0.0"
description = "High-performance real-time voice activity detection"
readme = "README.md"
license = {text = "Apache-2.0"}
authors = [{name = "TEN Framework"}]
maintainers = [{name = "Your Name", email = "your.email@example.com"}]
requires-python = ">=3.8"
dependencies = [
    "numpy",
    "scipy",
]
classifiers = [
    "Development Status :: 4 - Beta",
    "Intended Audience :: Developers",
    "License :: OSI Approved :: Apache Software License",
    "Operating System :: OS Independent",
    "Programming Language :: Python :: 3",
    "Topic :: Multimedia :: Sound/Audio :: Speech",
]

[project.urls]
Homepage = "https://github.com/TEN-framework/ten-vad"
Repository = "https://github.com/yourusername/ten-vad"
Issues = "https://github.com/TEN-framework/ten-vad/issues"

[tool.setuptools.packages.find]
where = ["."]

[tool.setuptools.package-data]
"ten_vad" = ["**/*"]  # Include native libraries
```

**Note**: Option 2 may require handling their custom installation logic for platform-specific libraries.

## Step-by-Step Publication Process

### 1. Fork Repository
```bash
# On GitHub: Fork TEN-framework/ten-vad to your account
git clone https://github.com/yourusername/ten-vad.git
cd ten-vad
```

### 2. Update Package Configuration
Choose Option 1 (setup.py fix) or Option 2 (pyproject.toml conversion) above.

### 3. Test Build Process
```bash
# Install build tools
pip install build twine

# Build the package
python -m build

# Creates dist/ with .tar.gz and .whl files
```

### 4. Test Local Installation
```bash
# Test installing built package
pip install dist/ten_vad-1.0.0-py3-none-any.whl

# Verify functionality
python -c "import ten_vad; print('Success!')"
```

### 5. Publish to PyPI
```bash
# Test on TestPyPI first (recommended)
twine upload --repository testpypi dist/*

# Test install from TestPyPI
pip install --index-url https://test.pypi.org/simple/ ten-vad

# If successful, publish to real PyPI
twine upload dist/*
```

## Package Name Options

- `ten-vad` (if available on PyPI)
- `ten-vad-pypi` (clearly indicates PyPI mirror)
- `agora-ten-vad` (gives credit to original authors)

## Impact on whisper-key Project

Once published, whisper-key's pyproject.toml becomes:
```toml
dependencies = [
    "faster-whisper>=1.1.1",
    "ten-vad>=1.0.0",  # Clean PyPI dependency!
    "numpy>=1.24.0",
    # ... rest of dependencies
]
```

Users can then install with:
```bash
pipx install whisper-key  # All dependencies included automatically
```

## Technical Considerations

### Native Libraries
ten-vad includes platform-specific native libraries that need special handling:
- Linux: `lib/linux/libten_vad.so`
- Windows: `lib/windows/ten_vad.dll`
- macOS: `lib/macos/libten_vad.dylib`

Their current setup.py handles this with custom install commands. This needs to be preserved in any modernization.

### Version Management
Consider extracting version from git tags or maintaining in separate `_version.py` file for consistency.

## Estimated Effort

- **Setup.py fix (Option 1)**: 30-60 minutes
- **pyproject.toml conversion (Option 2)**: 1-2 hours
- **Testing and publication**: 30 minutes

## Future Maintenance

- Monitor upstream ten-vad for updates
- Consider reaching out to TEN Framework about official PyPI publication
- Maintain attribution and license compliance
- Update whisper-key documentation about the dependency change

## References

- [TEN-VAD Repository](https://github.com/TEN-framework/ten-vad)
- [TEN-VAD License](https://github.com/TEN-framework/ten-vad/blob/main/LICENSE)
- [PyPI Publishing Guide](https://packaging.python.org/tutorials/packaging-projects/)
- [PEP 621 - pyproject.toml metadata](https://peps.python.org/pep-0621/)