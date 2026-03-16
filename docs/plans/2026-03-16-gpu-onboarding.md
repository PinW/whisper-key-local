# GPU Onboarding

As a *non-technical user* I want **the app to set up GPU acceleration for me** so I get faster transcription without needing to understand CUDA, ROCm, or CT2 wheels.

## Background

GPU acceleration makes transcription dramatically faster and enables larger, more accurate models. The app already detects GPU hardware, runtimes, and CT2 variants on startup (`platform/windows/gpu.py`). But detection only *reports* — it doesn't *act*. Users must manually install runtime libraries, swap CT2 wheels, and edit config. This plan adds an onboarding flow that does it all for them.

### GPU classes

| GPU class | Runtime needed | CT2 wheel | Pip-installable? |
|-----------|---------------|-----------|-----------------|
| NVIDIA | CUDA Toolkit 12 | Standard PyPI (already installed) | Yes |
| AMD RDNA2+ (RX 6000+, RX 7000+, RX 9000+) | ROCm/HIP 7.2 | ROCm wheel from custom repo | Yes |
| AMD RDNA1 (RX 5000) | ROCm/HIP 6.2 | Custom ROCm wheel from custom repo | Yes |

### What needs installing per GPU class

**NVIDIA:** Runtime libraries only. The standard CT2 wheel from PyPI is already the CUDA build.
- `nvidia-cuda-runtime-cu12`, `nvidia-cublas-cu12`, `nvidia-cudnn-cu12`, etc.
- TODO: Research exact packages and sizes

**AMD RDNA2+:** Runtime libraries + replace CT2 wheel.
- ROCm SDK pip packages from `repo.radeon.com`
- CT2 ROCm wheel from custom GitHub repo
- TODO: Research exact packages and sizes

**AMD RDNA1:** Same as RDNA2+ but different ROCm version and different CT2 wheel.
- ROCm 6.2 SDK pip packages
- Custom CT2 wheel from custom GitHub repo
- TODO: Research exact packages and sizes

## Architecture

### Two separate components

```
detect_and_print()          ← already exists, runs on startup, prints status
    |
    v  returns (gpu_class, gpu_name, ct2_works)
    |
onboarding.check_gpu()      ← NEW, reads detection results, decides whether to prompt
    |
    v
prompt_choice()             ← terminal_ui prompt if action needed
    |
    v
pip install ...             ← install packages, configure app, exit
```

### Detection API changes

`detect_and_print()` currently prints and returns nothing. It needs to return a tuple so the onboarding module can consume the results:

```python
def detect_and_print(configured_device) -> tuple[str | None, str | None, bool]:
    # ... existing detection and printing logic ...
    return (gpu_class, gpu_name, ct2_works)
```

Returns `(None, None, False)` when no GPU detected. macOS stub returns the same.

### Config

```yaml
onboarding:
  gpu: pending          # pending | complete | skipped
  gpu_class: null       # nvidia | amd_rdna2+ | amd_rdna1 | integrated_cpu | null
```

- `gpu: pending` — default, run the check
- `gpu: complete` — GPU acceleration configured and working
- `gpu: skipped` — user explicitly said "don't ask again"
- `gpu_class` — records what hardware was found. Used by `update_checker.py` to restore AMD CT2 wheels after upgrade. Extensible to `apple_silicon`, etc. when we add more engines.

When no GPU is detected, set `gpu_class: integrated_cpu` and `gpu: skipped`. Later when we add Metal/iGPU engine support, we can reset `gpu: pending` for `integrated_cpu` users.

### Update integration

For AMD users, `pip install --upgrade whisper-key-local` (from auto-update) replaces the ROCm CT2 wheel with the standard CUDA build from PyPI. The `update_checker.py` module reads `onboarding.gpu_class` from config and re-installs the correct CT2 wheel after upgrading.

The CT2 wheel URL mapping lives in `onboarding.py` and is imported by `update_checker.py`:

```python
# In update_checker.py, after pip upgrade
from .onboarding import get_ct2_wheel_url

gpu_class = config_manager.get_setting('onboarding', 'gpu_class')
if gpu_class and gpu_class.startswith('amd'):
    ct2_url = get_ct2_wheel_url(gpu_class)
    print("   Restoring GPU packages...")
    result = subprocess.run([sys.executable, "-m", "pip", "install", "--force-reinstall", "--no-deps", ct2_url])
    if result.returncode != 0:
        print("   ✗ Failed to restore GPU packages. GPU acceleration may need to be re-installed.")
```

## Onboarding Flow

### Decision tree

```
App starts → detect_and_print() → onboarding.check_gpu()

gpu_class, gpu_name, ct2_works = detection result

1. config gpu == "complete" or "skipped"?
   → Skip (no detection cost)

2. gpu_class is None? (no discrete GPU)
   → Set gpu_class: integrated_cpu, gpu: skipped
   → Skip

3. ct2_works and device == "cuda"?
   → Set gpu: complete, gpu_class: <detected>
   → Skip (already working, auto-configure)

4. GPU found + not fully set up
   → Show prompt
```

### The prompt

One prompt. Non-technical. Shows what they have, what's needed, and why.

```
  ┌──────────────────────────────────────────────────────────────┐
  │ GPU acceleration available                                   │
  │                                                              │
  │ Your NVIDIA GeForce RTX 4080 can speed up transcription      │
  │ significantly and unlock larger, more accurate models.       │
  │                                                              │
  │ Requires a one-time download (~X GB, ~Y GB disk space).      │
  │                                                              │
  │ [1] Install GPU acceleration                                 │
  │     Downloads and installs required packages                 │
  │                                                              │
  │ [2] Use CPU for now                                          │
  │     Continue without GPU (asked again next launch)           │
  │                                                              │
  │ [3] Don't use GPU acceleration                               │
  │     Never ask again                                          │
  └──────────────────────────────────────────────────────────────┘

  Press a number to choose:
```

### Installation flow (option 1)

```
1. Print "Installing GPU acceleration..."
2. Print "   Downloading runtime libraries... (this may take a few minutes)"
3. pip install runtime packages (CUDA or ROCm depending on gpu_class)
4. If AMD: pip install --force-reinstall CT2 ROCm wheel
5. Set config: device: cuda, compute_type: float16
6. Set config: onboarding.gpu: complete, onboarding.gpu_class: <class>
7. Print "   GPU acceleration installed. Please restart Whisper Key."
8. sys.exit(0)
```

User relaunches → detection confirms everything works → skips onboarding.

### "Use CPU for now" (option 2)

If config already has `device: cuda` from a previous broken setup, reset to `device: cpu` to prevent crash. Leave `onboarding.gpu` as `pending` so user is prompted again next launch.

### Progress display

Large downloads need feedback. pip itself prints progress bars. We let pip output directly to the terminal (don't capture stdout):

```python
subprocess.run(
    [sys.executable, "-m", "pip", "install", *packages],
    # Don't capture output — let pip show its progress
)
```

## Implementation Plan

1. Refactor detection to return results
- [ ] Make `detect_and_print()` return `(gpu_class, gpu_name, ct2_works)` tuple
- [ ] Update `hardware_detection.py` wrapper to pass through the return value
- [ ] macOS stub returns `(None, None, False)`
- [ ] Update `main.py` to capture the result

2. Add onboarding config
- [ ] Add `onboarding` section to `config.defaults.yaml`

3. Create onboarding module
- [ ] Create `src/whisper_key/onboarding.py`
- [ ] Implement decision tree
- [ ] Implement prompt using `terminal_ui.prompt_choice`
- [ ] Implement pip install flow per GPU class
- [ ] Implement config updates (device, compute_type, onboarding status)
- [ ] Define `get_ct2_wheel_url(gpu_class)` for use by both onboarding and update_checker

4. Define GPU package lists
- [ ] Research and pin exact NVIDIA CUDA pip packages + versions
- [ ] Research and pin exact AMD ROCm pip packages + versions + URLs
- [ ] Research and pin CT2 ROCm wheel URLs for RDNA2+ and RDNA1
- [ ] Verify all wheels exist for Python 3.12 (pyapp's Python version)
- [ ] Document download and installed sizes per GPU class

5. Wire into main.py
- [ ] Call `onboarding.check_gpu()` after `detect_and_print()`, before component setup
- [ ] Pass detection tuple and `config_manager`

6. Test
- [ ] NVIDIA: install flow end-to-end
- [ ] AMD RDNA2+: install flow end-to-end (primary PC, RX 9070 XT)
- [ ] AMD RDNA1: install flow end-to-end (secondary PC, RX 5700 XT)
- [ ] No GPU: auto-skips, sets integrated_cpu
- [ ] Already working: auto-skips, sets complete
- [ ] "Don't use GPU" persists skip
- [ ] "Use CPU for now" prompts again next launch, resets device to cpu if needed
- [ ] After app update: AMD CT2 wheel re-installed automatically
- [ ] macOS: skips entirely (no-op stub)
- [ ] pip install failure: clear error message, user re-prompted next launch

## Scope

| File | Changes |
|------|---------|
| `platform/windows/gpu.py` | Return `(gpu_class, gpu_name, ct2_works)` from `detect_and_print()` |
| `onboarding.py` | New module — decision tree, prompt, install, config, `get_ct2_wheel_url()` |
| `main.py` | Capture detection result, call `onboarding.check_gpu()` |
| `config.defaults.yaml` | Add `onboarding` section |

## Success Criteria

- [ ] Non-technical user can get GPU acceleration with one keypress
- [ ] NVIDIA: runtime packages installed, device:cuda set, transcription works on GPU
- [ ] AMD RDNA2+: ROCm packages + CT2 wheel installed, transcription works on GPU
- [ ] AMD RDNA1: ROCm 6.2 packages + custom CT2 wheel installed, transcription works on GPU
- [ ] No GPU detected → never prompted, gpu_class set to integrated_cpu
- [ ] Already working → never prompted, auto-configured as complete
- [ ] "Don't use GPU" → never prompted again
- [ ] "Use CPU for now" → prompted again next launch, device reset to cpu
- [ ] pip progress visible during download
- [ ] pip install failure shows clear error, re-prompts next launch
- [ ] Auto-update preserves GPU setup for AMD users
- [ ] macOS: no errors, no prompts
