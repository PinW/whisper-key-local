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
- **Cross-Platform Challenge**: WSL for development, Windows for runtime execution

### Gaps and Issues
- Slow dependency resolution with pip
- No lock file for reproducible builds
- Manual virtual environment management
- No integrated project configuration
- Cross-platform environment inconsistency between WSL dev and Windows runtime
- Missing automated gitignore management for new environment structure

### What's Already Working
- All dependencies install and function correctly
- Application runs successfully on Windows
- Component tests pass
- Development workflow is established

## Implementation Plan

### Phase 1: Cross-Platform Environment Setup and Validation
- [ ] **WSL Development Setup**
  - [ ] Install uv on WSL development system
    ```bash
    curl -LsSf https://astral.sh/uv/install.sh | sh
    ```
  - [ ] Verify uv installation with `uv --version`
  - [ ] Document current package versions with `pip list > current_packages.txt`
- [ ] **Windows Runtime Setup** (User will execute)
  - [ ] Install uv on Windows for user testing
    ```powershell
    powershell -c "irm https://astral.sh/uv/install.ps1 | iex"
    ```
  - [ ] Test current application functionality on Windows before migration
- [ ] **Environment Backup**
  - [ ] Create backup of working `venv_new/` environment
    ```bash
    cp -r venv_new/ venv_new_backup/
    ```

### Phase 2: Project Configuration Migration
- [ ] Initialize uv project structure
  ```bash
  uv init --no-readme --no-gitignore
  ```
- [ ] Create pyproject.toml with project metadata and dependencies
- [ ] Import existing requirements by copying from requirements.txt to pyproject.toml dependencies
  - Note: `uv add --requirements` syntax is incorrect; manual import required
- [ ] Validate pyproject.toml configuration
- [ ] Keep requirements.txt for pip fallback compatibility

### Phase 3: Cross-Platform Virtual Environment Migration
- [ ] **WSL Development Environment**
  - [ ] Create new uv-managed virtual environment
    ```bash
    uv venv .venv --python 3.12
    ```
  - [ ] Generate lock file explicitly
    ```bash
    uv lock
    ```
  - [ ] Sync dependencies with `uv sync`
  - [ ] Test all dependencies load correctly in WSL environment
- [ ] **Windows Runtime Validation** (User will execute)
  - [ ] Create Windows uv environment using same pyproject.toml
    ```powershell
    uv venv .venv --python 3.12
    uv sync
    ```
  - [ ] Verify Windows-specific packages (pywin32, global-hotkeys) function
  - [ ] Run component tests in Windows environment
- [ ] **Cross-Platform Testing**
  - [ ] Document any platform-specific differences
  - [ ] Ensure lock file works consistently across platforms

### Phase 4: Workflow Integration and Documentation
- [ ] **Script Updates**
  - [ ] Update test runner script to use uv commands
  - [ ] Modify utility scripts in tools/ for uv compatibility
- [ ] **Documentation Updates**
  - [ ] Update CLAUDE.md with new cross-platform development commands
  - [ ] Update README.md with separate WSL/Windows installation instructions
  - [ ] Add troubleshooting section for cross-platform issues
- [ ] **Git Configuration**
  - [ ] Update .gitignore to exclude .venv/ and include uv.lock
- [ ] **Final Validation**
  - [ ] Validate complete application workflow on Windows
  - [ ] Document performance improvements vs pip
  - [ ] Create migration rollback procedure if needed

## Implementation Details

### Architecture Decisions
- **Cross-Platform Strategy**: Separate but synchronized environments for WSL dev and Windows runtime
- **Parallel Installation**: Keep both pip and uv during transition
- **Fallback Strategy**: Maintain requirements.txt for pip compatibility
- **Environment Location**: Use .venv/ instead of venv_new/ for uv standard
- **Lock File**: Generate uv.lock for reproducible builds across platforms
- **Development Workflow**: Code in WSL, test in Windows using same pyproject.toml

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

[tool.uv]
dev-dependencies = []
```

### Command Updates

**WSL Development Workflow:**
```bash
# Old pip workflow
python -m venv venv_new
source venv_new/bin/activate
pip install -r requirements.txt

# New uv workflow (WSL)
uv sync                         # Install dependencies
uv run python --version        # Test environment
# Development and testing only - no app execution in WSL
```

**Windows Runtime Workflow:**
```powershell
# Old pip workflow
python -m venv venv_new
venv_new\Scripts\activate
pip install -r requirements.txt
python whisper-key.py

# New uv workflow (Windows)
uv sync                         # Install dependencies
uv run python whisper-key.py   # Run application
# or
uv shell                        # Activate environment
python whisper-key.py           # Run normally
```

## Files to Modify

- **pyproject.toml** - Create new project configuration file with cross-platform dependencies
- **requirements.txt** - Keep for pip fallback compatibility
- **tests/run_component_tests.py** - Update to use uv commands with platform detection
- **tools/*.py** - Update scripts to work with uv environment
- **CLAUDE.md** - Update with separate WSL development and Windows runtime commands
- **README.md** - Update with cross-platform installation instructions
- **.gitignore** - Add .venv/ directory and include uv.lock file
- **uv.lock** - Generated lock file for reproducible builds (auto-created)

### Critical Platform Considerations
- WSL environment for development and code editing
- Windows environment for application runtime and testing
- Shared pyproject.toml and uv.lock for consistency
- Platform-specific activation scripts and paths

