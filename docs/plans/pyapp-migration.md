# PyApp Migration Plan

Replace PyInstaller with [pyapp](https://github.com/ofek/pyapp) for Windows distribution.

## Why

- Eliminates PyInstaller maintenance (hidden imports, DLL hacks, MSVCP140 force-replace)
- Built-in `self update` command — users get auto-updates for free
- Tiny initial download (~10MB) vs 110MB+ zips
- No antivirus false positives
- Same install path as pip/pipx users — one distribution method instead of three
- Internet requirement is a non-issue (users already download 3GB+ models)

## What pyapp does

Produces a small Rust binary that on first run:
1. Downloads and installs Python
2. Pip-installs the package (from PyPI or embedded wheel)
3. Runs the app entry point
4. Subsequent launches skip steps 1-2

## Migration Steps

### Phase 1: Proof of concept
- [x] Install Rust toolchain on build PC
- [x] Build a basic pyapp binary pointing at `whisper-key-local` on PyPI
- [x] Test first-run experience: Python bootstrap + pip install + app launch
- [ ] Verify custom PortAudio DLL loads correctly via `resolve_asset_path`
- [ ] Verify audio feedback sounds load correctly
- [ ] Test GPU detection (CUDA) with user-installed drivers

### Phase 2: Build & release integration
- [x] Create pyapp build script (`pyapp-build/build-pyapp.ps1`)
- [ ] Update release skill to build pyapp binaries instead of PyInstaller
- [ ] Test auto-update flow (`self update`)
- [ ] Update README with new install instructions

### Phase 3: Ship & deprecate PyInstaller
- [ ] Release pyapp builds alongside PyInstaller for one version (beta)
- [ ] Gather user feedback
- [ ] Remove PyInstaller build infrastructure

## Open Questions

- Can we embed the wheel in the binary instead of fetching from PyPI? (faster first run)
- What does the update UX look like? Does `self update` run automatically or does the user trigger it?
- How do we handle breaking config changes across updates?
- Cross-compilation: can we build Windows binaries from WSL/Linux?

## Follow-up

- GPU variants plan: `docs/plans/pyapp-gpu-variants.md`
