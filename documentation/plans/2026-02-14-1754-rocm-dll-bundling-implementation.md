# Bundle ROCm 7.2 DLLs in Exe Build

As a *user* I want **ROCm DLLs bundled in the exe** so the portable ROCm build works out of the box without installing HIP SDK or pip packages ([#30](https://github.com/PinW/whisper-key-local/issues/30))

## Background

The official CTranslate2 v4.7.1 ROCm wheel dynamically links against `amdhip64_7.dll` + `hipblas.dll`. These DLLs come from two pip packages (`rocm_sdk_core` 607MB, `rocm_sdk_libraries_custom` 469MB) hosted at `repo.radeon.com`. Users can't get them from the HIP SDK installer (only goes to 7.1.1 on Windows).

CTranslate2's own `__init__.py` handles DLL discovery in a normal Python environment:

```python
package_dir = str(files(module_name))  # e.g. site-packages/ctranslate2/
os.add_dll_directory(package_dir)
os.add_dll_directory(f"{package_dir}/../_rocm_sdk_core/bin")
os.add_dll_directory(f"{package_dir}/../_rocm_sdk_libraries_custom/bin")
```

In the frozen exe, `package_dir` resolves to `_internal/ctranslate2/`. So CT2 looks for:
- `_internal/ctranslate2/*.dll` (already has `ctranslate2.dll`, `libiomp5md.dll`)
- `_internal/_rocm_sdk_core/bin/*.dll`
- `_internal/_rocm_sdk_libraries_custom/bin/*.dll`

**Key insight:** If we place the ROCm DLLs at those paths in the bundle, CT2's own `__init__.py` finds them — no runtime hook changes needed.

### Current ROCm exe build flow

1. `build-windows.ps1 -Variant rocm` installs the ROCm CT2 wheel from `py-build/wheels/rocm-rdna2/`
2. `whisper-key.spec` includes runtime hook `rth_rocm_paths.py` for ROCm variant
3. Runtime hook looks for `HIP_PATH` env var → adds HIP SDK bin dir to DLL search path
4. This fails if user doesn't have HIP SDK installed (or has wrong version)

### Target flow

1. Build venv also has `rocm_sdk_core` + `rocm_sdk_libraries_custom` pip packages installed
2. Spec file collects needed DLLs from those packages into the bundle at the right paths
3. CT2's own `__init__.py` finds them at `_internal/_rocm_sdk_core/bin/` etc.
4. Runtime hook becomes a fallback for users who DO have HIP SDK (e.g. your custom build)

## Implementation Plan

### 1. Identify minimum DLL set (on Windows build machine)

- [ ] Install ROCm SDK packages in build venv:
  ```
  pip install rocm_sdk_core rocm_sdk_libraries_custom --index-url https://repo.radeon.com/rocm/windows/rocm-rel-7.2/
  ```
- [ ] Find the package directories:
  ```python
  import _rocm_sdk_core, _rocm_sdk_libraries_custom
  print(_rocm_sdk_core.__path__)
  print(_rocm_sdk_libraries_custom.__path__)
  ```
- [ ] List all DLLs in their `bin/` directories
- [ ] Use `dumpbin /dependents` to trace the full dependency chain starting from `ctranslate2.dll`:
  ```
  dumpbin /dependents ctranslate2.dll   → amdhip64_7.dll, hipblas.dll
  dumpbin /dependents hipblas.dll       → ???
  dumpbin /dependents amdhip64_7.dll    → ???
  ```
- [ ] Document the minimum set of DLLs needed and which package provides each

### 2. Add ROCm SDK packages to build venv setup

- [ ] Update `build-windows.ps1`: after installing the ROCm CT2 wheel, also install the ROCm SDK packages
  ```powershell
  if ($Variant -eq "rocm") {
      # existing wheel install ...
      & $VenvPip install rocm_sdk_core rocm_sdk_libraries_custom --index-url https://repo.radeon.com/rocm/windows/rocm-rel-7.2/
  }
  ```

### 3. Update spec file to collect ROCm DLLs

- [ ] Add ROCm DLL collection to `whisper-key.spec` (ROCm variant only), following the `ten_vad` pattern:
  ```python
  rocm_binaries = []
  if build_variant == 'rocm':
      for site_dir in site.getsitepackages():
          core_bin = pathlib.Path(site_dir) / '_rocm_sdk_core' / 'bin'
          libs_bin = pathlib.Path(site_dir) / '_rocm_sdk_libraries_custom' / 'bin'
          if core_bin.exists():
              # Only collect the DLLs we actually need (from step 1)
              needed_core = ['amdhip64_7.dll', ...]  # TBD from step 1
              for dll in needed_core:
                  dll_path = core_bin / dll
                  if dll_path.exists():
                      rocm_binaries.append((str(dll_path), '_rocm_sdk_core/bin'))
          if libs_bin.exists():
              needed_libs = ['hipblas.dll', ...]  # TBD from step 1
              for dll in needed_libs:
                  dll_path = libs_bin / dll
                  if dll_path.exists():
                      rocm_binaries.append((str(dll_path), '_rocm_sdk_libraries_custom/bin'))
              break
  ```
- [ ] Add `rocm_binaries` to the `binaries` list in `Analysis()`

### 4. Test

- [ ] Build ROCm exe variant: `build-windows.ps1 -Variant rocm`
- [ ] Verify DLLs appear in `_internal/_rocm_sdk_core/bin/` and `_internal/_rocm_sdk_libraries_custom/bin/`
- [ ] Test on machine WITHOUT HIP SDK installed — app should start and load CT2
- [ ] Test GPU transcription works end-to-end
- [ ] Check final exe size increase is reasonable

## Scope

| File | Changes |
|------|---------|
| `py-build/build-windows.ps1` | Add `rocm_sdk_core`/`rocm_sdk_libraries_custom` pip install for ROCm variant |
| `py-build/whisper-key.spec` | Collect ROCm DLLs from SDK packages into bundle |
| `py-build/hooks/rth_rocm_paths.py` | No change needed (keep as HIP SDK fallback) |

## Open Questions

- **What is the minimum DLL set?** Must be determined on the Windows build machine via `dumpbin` dependency tracing. The 1GB+ of SDK packages likely contain many DLLs we don't need.
- **Size impact?** The needed DLLs (HIP runtime + hipblas + transitive deps) will add significant size. Acceptable tradeoff for a working portable build.
- **Does `importlib.resources.files()` resolve correctly in frozen exe?** Should work — PyInstaller supports `importlib.resources` — but needs verification.

## Success Criteria

- [ ] ROCm exe starts and loads CTranslate2 on a machine with NO HIP SDK and NO pip ROCm packages
- [ ] GPU transcription works end-to-end
- [ ] Build script handles missing ROCm SDK packages gracefully (clear error message)
