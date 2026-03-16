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
    v
onboarding.check_gpu()      ← NEW, reads detection results, decides whether to prompt
    |
    v
prompt_choice()             ← terminal_ui prompt if action needed
    |
    v
pip install ...             ← install packages, configure app, restart
```

### Detection API changes

`detect_and_print()` currently prints and returns nothing. It needs to return structured results so the onboarding module can consume them:

```python
@dataclass
class GpuDetectionResult:
    vendor: str | None        # "nvidia", "amd"
    name: str | None          # "NVIDIA GeForce RTX 4080"
    gpu_class: str | None     # "nvidia", "amd_rdna2+", "amd_rdna1"
    runtime_found: bool
    runtime_version: str | None
    ct2_variant: str | None   # "cuda", "rocm", "not_installed"
    ct2_works: bool           # _test_ct2_gpu() result
```

### Config state

```yaml
gpu_onboarding:
  status: pending       # pending | no_gpu_found | complete | skipped
  gpu_class: null       # nvidia | amd_rdna2+ | amd_rdna1 (set after install)
```

Status values:
- `pending` — default, run the check
- `no_gpu_found` — no discrete GPU detected. Re-check when we add Apple Metal / iGPU support.
- `complete` — GPU acceleration fully configured and working
- `skipped` — user explicitly said "don't ask again"

### Update integration

For AMD users, `pip install --upgrade whisper-key-local` (from auto-update) replaces the ROCm CT2 wheel with the standard CUDA build from PyPI. The `update_checker.py` module reads `gpu_onboarding.gpu_class` from config and re-installs the correct CT2 wheel after upgrading.

```python
# In update_checker.py, after pip upgrade
gpu_class = config_manager.get_setting('gpu_onboarding', 'gpu_class')
if gpu_class and gpu_class.startswith('amd'):
    reinstall_rocm_ct2(gpu_class)
```

## Onboarding Flow

### Decision tree

```
App starts → detect_and_print() → onboarding.check_gpu()

1. status == "complete"?
   → Verify still working (_test_ct2_gpu + device:cuda)
   → If broken: reset status to "pending", continue below
   → If working: skip

2. status == "skipped"?
   → Skip

3. status == "no_gpu_found"?
   → Skip (until we add Metal/iGPU support)

4. status == "pending"?
   → Run detection
   → No GPU found? → Set status: "no_gpu_found", skip
   → GPU found + everything working? → Set status: "complete", skip
   → GPU found + not fully set up? → Show prompt
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
6. Set config: gpu_onboarding.status: complete, gpu_onboarding.gpu_class: <class>
7. Print "   GPU acceleration installed. Please restart Whisper Key."
8. sys.exit(0)
```

User relaunches → detection confirms everything works → `complete` status → skips onboarding.

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
- [ ] Add `GpuDetectionResult` dataclass to `platform/windows/gpu.py`
- [ ] Make `detect_and_print()` return `GpuDetectionResult`
- [ ] Update `hardware_detection.py` wrapper to pass through the return value
- [ ] Update `main.py` to capture the result

2. Add onboarding config
- [ ] Add `gpu_onboarding` section to `config.defaults.yaml`
- [ ] Add `get_gpu_onboarding_config()` to `ConfigManager`

3. Create GPU onboarding module
- [ ] Create `src/whisper_key/onboarding.py`
- [ ] Implement decision tree (check status, detection results)
- [ ] Implement prompt using `terminal_ui.prompt_choice`
- [ ] Implement pip install flow per GPU class
- [ ] Implement config updates (device, compute_type, onboarding status)

4. Define GPU package lists
- [ ] Research and pin exact NVIDIA CUDA pip packages + versions
- [ ] Research and pin exact AMD ROCm pip packages + versions + URLs
- [ ] Research and pin CT2 ROCm wheel URLs for RDNA2+ and RDNA1
- [ ] Verify all wheels exist for Python 3.12 (pyapp's Python version)
- [ ] Document download and installed sizes per GPU class

5. Wire into main.py
- [ ] Call `onboarding.check_gpu()` after `detect_and_print()`, before component setup
- [ ] Pass `GpuDetectionResult` and `config_manager`

6. Update auto-update flow
- [ ] After pip upgrade in `update_checker.py`, check `gpu_onboarding.gpu_class`
- [ ] If AMD: re-install correct CT2 ROCm wheel

7. Test
- [ ] NVIDIA: install flow end-to-end
- [ ] AMD RDNA2+: install flow end-to-end (primary PC, RX 9070 XT)
- [ ] AMD RDNA1: install flow end-to-end (secondary PC, RX 5700 XT)
- [ ] No GPU: auto-skips, sets no_gpu_found
- [ ] Already working: auto-skips, sets complete
- [ ] "Don't use GPU" persists skip
- [ ] "Use CPU for now" prompts again next launch
- [ ] After self update: AMD CT2 wheel re-installed automatically
- [ ] macOS: skips entirely (no-op stub)

## Scope

| File | Changes |
|------|---------|
| `platform/windows/gpu.py` | Add `GpuDetectionResult`, return from `detect_and_print()` |
| `platform/macos/gpu.py` | Return `None` or empty result from `detect_and_print()` |
| `hardware_detection.py` | Pass through return value |
| `config.defaults.yaml` | Add `gpu_onboarding` section |
| `config_manager.py` | Add `get_gpu_onboarding_config()` |
| `onboarding.py` | New module — decision tree, prompt, install, config |
| `main.py` | Capture detection result, call `onboarding.check_gpu()` |
| `update_checker.py` | Re-install AMD CT2 wheel after upgrade |

## Success Criteria

- [ ] Non-technical user can get GPU acceleration with one keypress
- [ ] NVIDIA: runtime packages installed, device:cuda set, transcription works on GPU
- [ ] AMD RDNA2+: ROCm packages + CT2 wheel installed, transcription works on GPU
- [ ] AMD RDNA1: ROCm 6.2 packages + custom CT2 wheel installed, transcription works on GPU
- [ ] No GPU detected → never prompted
- [ ] Already working → never prompted
- [ ] "Don't use GPU" → never prompted again
- [ ] "Use CPU for now" → prompted again next launch
- [ ] pip progress visible during download
- [ ] Auto-update preserves GPU setup for AMD users
- [ ] macOS: no errors, no prompts
