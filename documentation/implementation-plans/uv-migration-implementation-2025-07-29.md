# uv Package Management Migration Implementation Plan

**Note: Execute one line-item at a time and confirm with user before proceeding to next**
**Note: Update this document as you go, checking off tasks and taking notes needed for later**

## Current State Analysis

### Existing Functionality
- **Package Manager**: pip with requirements.txt
- **Dependencies**: 10 packages (faster-whisper, numpy, sounddevice, global-hotkeys, pyperclip, ruamel.yaml, pywin32, pyautogui, pystray, Pillow, hf-xet)
- **Virtual Environment**: Standard Python venv (`venv_new/`)
- **Development Tools**: Component test runner, utility scripts in tools/
- **Platform**: Windows 10+ runtime with WSL development environment

### Gaps and Issues
- Slow dependency resolution with pip
- No lock file for reproducible builds
- Manual virtual environment management
- No integrated project configuration

### What's Already Working
- All dependencies install and function correctly
- Application runs successfully on Windows
- Component tests pass
- Development workflow is established

## Implementation Plan

### Phase 1: Environment Setup and Validation
- [ ] Install uv on WSL development system
  ```bash
  curl -LsSf https://astral.sh/uv/install.sh | sh
  ```
- [ ] Install uv on Windows for user testing
  ```bash
  powershell -c "irm https://astral.sh/uv/install.ps1 | iex"
  ```
- [ ] Document current package versions with `pip list`
- [ ] Test current application functionality on Windows
- [ ] Create backup of working `venv_new/` environment

### Phase 2: Project Configuration Migration
- [ ] Initialize uv project structure
  ```bash
  uv init --no-readme --no-gitignore
  ```
- [ ] Create pyproject.toml with project metadata and dependencies
- [ ] Import existing requirements using `uv add --requirements requirements.txt`
- [ ] Validate pyproject.toml configuration
- [ ] Keep requirements.txt for pip fallback compatibility

### Phase 3: Virtual Environment Migration
- [ ] Create new uv-managed virtual environment
  ```bash
  uv venv .venv --python 3.12
  ```
- [ ] Sync dependencies with `uv sync`
- [ ] Test all dependencies load correctly in new environment
- [ ] Verify Windows-specific packages (pywin32, global-hotkeys) function
- [ ] Run component tests in new environment

### Phase 4: Workflow Integration
- [ ] Update test runner script to use uv commands
- [ ] Modify utility scripts in tools/ for uv compatibility
- [ ] Update CLAUDE.md with new development commands
- [ ] Update README.md installation instructions
- [ ] Validate complete application workflow on Windows
- [ ] Document performance improvements vs pip

## Implementation Details

### New Project Structure
```
whisper-key-local/
├── pyproject.toml          # Project configuration (NEW)
├── uv.lock                 # Lock file (NEW)
├── requirements.txt        # Kept for compatibility
├── .venv/                  # uv-managed venv (REPLACES venv_new/)
├── src/                    # No changes
├── tests/                  # Minor script updates
├── tools/                  # Minor script updates
└── ...
```

### pyproject.toml Configuration
```toml
[project]
name = "whisper-key-local"
version = "1.0.0"
description = "Local faster-whisper speech-to-text with global hotkey"
requires-python = ">=3.10"
dependencies = [
    "faster-whisper>=1.1.1",
    "numpy>=1.24.0",
    "sounddevice>=0.4.6",
    "global-hotkeys>=0.1.7",
    "pyperclip>=1.8.2",
    "ruamel.yaml>=0.18.14",
    "pywin32>=306; platform_system=='Windows'",
    "pyautogui>=0.9.54",
    "pystray>=0.19.5",
    "Pillow>=10.0.0",
    "hf-xet>=1.1.5"
]

[project.scripts]
whisper-key = "whisper-key:main"

[tool.uv]
dev-dependencies = []
```

### Command Updates

#### Old Commands
```bash
# Current workflow
python -m venv venv_new
venv_new\Scripts\activate
pip install -r requirements.txt
python whisper-key.py
```

#### New Commands
```bash
# New uv workflow
uv sync                    # Install all dependencies
uv run whisper-key.py      # Run with uv
# or
uv shell                   # Activate environment
python whisper-key.py      # Run normally
```

## Files to Modify

- **pyproject.toml** - Create new project configuration file
- **requirements.txt** - Keep for pip fallback compatibility
- **tests/run_component_tests.py** - Update to use uv commands if needed
- **tools/*.py** - Update scripts to work with uv environment
- **CLAUDE.md** - Update development commands
- **README.md** - Update installation instructions
- **.gitignore** - Add .venv/ and uv.lock

## Implementation Details

### pyproject.toml Configuration
```toml
[project]
name = "whisper-key-local"
version = "1.0.0"
description = "Local faster-whisper speech-to-text with global hotkey"
requires-python = ">=3.10"
dependencies = [
    "faster-whisper>=1.1.1",
    "numpy>=1.24.0",
    "sounddevice>=0.4.6",
    "global-hotkeys>=0.1.7",
    "pyperclip>=1.8.2",
    "ruamel.yaml>=0.18.14",
    "pywin32>=306; platform_system=='Windows'",
    "pyautogui>=0.9.54",
    "pystray>=0.19.5",
    "Pillow>=10.0.0",
    "hf-xet>=1.1.5"
]

[tool.uv]
dev-dependencies = []
```

### New Command Structure
```bash
# Old pip workflow
python -m venv venv_new
venv_new\Scripts\activate
pip install -r requirements.txt
python whisper-key.py

# New uv workflow
uv sync                    # Install dependencies
uv run python whisper-key.py  # Run application
# or
uv shell                   # Activate environment
python whisper-key.py      # Run normally
```

### Architecture Decisions
- **Parallel Installation**: Keep both pip and uv during transition
- **Fallback Strategy**: Maintain requirements.txt for pip compatibility
- **Environment Location**: Use .venv/ instead of venv_new/ for uv standard
- **Lock File**: Generate uv.lock for reproducible builds