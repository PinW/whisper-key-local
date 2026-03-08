# PyApp Packaging Research

Research date: 2026-03-08
Repository: https://github.com/ofek/pyapp (v0.29.0, 1.9k stars)
Docs: https://ofek.dev/pyapp/latest/

---

## 1. What PyApp Is and How It Works

PyApp is a **Rust-based wrapper** that creates self-bootstrapping executables for Python applications. Unlike PyInstaller (which bundles Python + dependencies into a single artifact), pyapp produces a small native binary that **downloads and installs Python + your packages at runtime** on the end user's machine.

### Architecture

The binary is compiled from Rust source using `cargo build`. At build time, you configure it via environment variables (project name, version, Python version, execution mode, etc.). The compiled binary contains:

- The Rust bootstrapping runtime (~5-15 MB)
- Optionally, an embedded Python distribution and/or wheel file
- Configuration baked into the binary

### Bootstrap Process (First Run)

1. Binary checks if installation directory exists (`~/.local/share/pyapp/<project>/...`)
2. If not: downloads Python from [python-build-standalone](https://github.com/indygreg/python-build-standalone) (or unpacks embedded distribution)
3. Creates a virtual environment (unless `PYAPP_FULL_ISOLATION` is set)
4. Installs the project via pip or UV (from PyPI, embedded wheel, or dependency file)
5. Launches the application via `execvp` (Unix) or process replacement (Windows)

Subsequent runs skip all of this — it only checks if the install directory exists, so startup is fast after first run.

### Key Configuration Variables

| Variable | Purpose |
|----------|---------|
| `PYAPP_PROJECT_NAME` | Package name (PEP 508) |
| `PYAPP_PROJECT_VERSION` | Package version |
| `PYAPP_PROJECT_PATH` | Embed a wheel or sdist directly |
| `PYAPP_PROJECT_DEPENDENCY_FILE` | Use requirements.txt instead of PyPI |
| `PYAPP_PYTHON_VERSION` | Target Python version (3.7-3.14, PyPy) |
| `PYAPP_DISTRIBUTION_EMBED` | Bundle Python distribution in binary |
| `PYAPP_EXEC_MODULE` | Run via `python -m <module>` |
| `PYAPP_EXEC_SPEC` | Run via object reference (e.g., `pkg.cli:main`) |
| `PYAPP_IS_GUI` | Use `pythonw.exe` on Windows (no console) |
| `PYAPP_PIP_EXTRA_ARGS` | Extra pip flags (e.g., `--extra-index-url`) |
| `PYAPP_UV_ENABLED` | Use UV instead of pip for installation |
| `PYAPP_SKIP_INSTALL` | Skip dependency installation at runtime |

---

## 2. Comparison with PyInstaller

### PyInstaller (Current Approach)

| Aspect | PyInstaller |
|--------|------------|
| **Output** | Single exe/folder with Python + all deps bundled |
| **First run** | Instant (everything included) |
| **Binary size** | Large (280MB CUDA, 500MB ROCm for whisper-key) |
| **Build process** | `pyinstaller spec` — well-documented, mature |
| **Native deps** | Bundles .dll/.so files automatically via hooks |
| **Offline** | Fully offline — no network needed ever |
| **GPU libs** | Can bundle CUDA/ROCm libraries directly |
| **Updates** | Manual — user downloads new exe |
| **Antivirus** | Frequent false positives |
| **Cross-compile** | No — must build on target OS |
| **Maturity** | Very mature, huge ecosystem |

### PyApp

| Aspect | PyApp |
|--------|-------|
| **Output** | Small native binary (~5-15 MB without embedding) |
| **First run** | Slow — downloads Python + installs packages |
| **Binary size** | Tiny if not embedding; large if embedding everything |
| **Build process** | Requires Rust toolchain + env vars |
| **Native deps** | Relies on pip/wheel availability on target platform |
| **Offline** | Requires workarounds (custom pre-built distribution) |
| **GPU libs** | No special support — depends on pip resolving correct wheels |
| **Updates** | Built-in `self update` command |
| **Antivirus** | Fewer false positives (Rust binary, not packed Python) |
| **Cross-compile** | Supported via `cross` (Rust cross-compilation) |
| **Maturity** | Young (v0.29.0), smaller community |

### Verdict for whisper-key-local

PyInstaller is significantly better suited for this project. PyApp's strengths (small binary, auto-updates) don't outweigh its weaknesses for our use case (complex native dependencies, GPU support, offline capability).

---

## 3. End User Experience

### Without Embedding (Default)

1. User downloads a small exe (~5-15 MB)
2. First launch: progress bar shows while Python (~40-80 MB compressed) downloads
3. Dependencies install from PyPI (duration depends on package count/size)
4. Application launches
5. Subsequent launches are fast (directory existence check only)

### With Full Embedding

1. User downloads a larger exe (size depends on embedded Python + wheel)
2. First launch: Python unpacks from binary, dependencies still install from network
3. Application launches after installation completes

### Management Commands

Users get built-in self-management via `app self <command>`:
- `self update` — update to latest version
- `self restore` — reinstall from scratch
- `self remove` — clean uninstall
- `self python` — access the managed Python interpreter
- `self pip` — access pip directly

The `PYAPP` environment variable is set to `1` during execution so the app can detect it's running inside pyapp.

---

## 4. Native/Compiled Dependencies

This is pyapp's weakest area for our use case.

### How It Works

PyApp delegates all dependency installation to pip (or UV). It does not bundle `.dll`, `.so`, or `.dylib` files itself. Native packages must be available as pre-built wheels on PyPI (or a custom index) for the target platform.

### Implications for whisper-key Dependencies

| Dependency | Wheel Available? | Notes |
|------------|-----------------|-------|
| **ctranslate2** | Yes (PyPI) | Standard CPU wheels available; GPU variants require specific index URLs |
| **faster-whisper** | Yes | Pure Python, depends on ctranslate2 |
| **numpy** | Yes | Well-supported wheels on PyPI |
| **sounddevice** | Yes | Wraps PortAudio; wheel includes the native lib |
| **pystray** | Yes | Pure Python with Pillow dependency |
| **pyperclip** | Yes | Pure Python |
| **ten-vad** | Unclear | May need source compilation |
| **pywin32** | Yes | Windows-only wheels on PyPI |

### The Problem

The standard pip install from PyPI gets you CPU-only ctranslate2. GPU-accelerated builds require either:
- A custom package index (`--extra-index-url`)
- Pre-built wheels manually hosted somewhere
- A custom Python distribution with everything pre-installed

You can pass `PYAPP_PIP_EXTRA_ARGS="--extra-index-url https://custom-index.example.com"` at build time, but this means:
- The user needs network access to that index on first run
- You need to host and maintain that custom index
- Different GPU variants (CUDA 11 vs 12, ROCm) require different index URLs or separate builds

### Offline / Air-Gapped

There is no built-in way to create a fully self-contained offline binary like PyInstaller. The documented workaround is:

1. Download a python-build-standalone distribution
2. Install all dependencies into it manually
3. Re-archive it
4. Set `PYAPP_DISTRIBUTION_PATH` to embed the whole thing
5. Set `PYAPP_SKIP_INSTALL` to skip pip at runtime

This negates most of pyapp's advantages and results in a binary comparable in size to PyInstaller output, but with more manual build steps.

---

## 5. GPU Support Considerations

### CUDA

ctranslate2 GPU wheels are published to PyPI but require matching CUDA runtime libraries. With PyInstaller, we bundle the exact CUDA libraries needed. With pyapp:

- pip would install the ctranslate2 wheel, but CUDA runtime libraries must already be on the user's system OR bundled in a custom distribution
- No mechanism to embed arbitrary native libraries alongside the Python environment
- Feature request for `--add-binary` equivalent ([#203](https://github.com/ofek/pyapp/issues/203)) is still open with no implementation planned
- Would likely need users to install CUDA Toolkit separately, which defeats the "just works" experience

### ROCm

Even more problematic:
- ROCm wheels for ctranslate2 are not on standard PyPI
- Would require a custom index URL
- ROCm runtime libraries are large (~200MB+) and cannot be embedded
- Users would need ROCm installed separately

### Verdict

PyApp has no GPU support story. It fundamentally relies on pip being able to install everything, and GPU dependencies require more than just pip. For a project that bundles GPU runtime libraries as a core feature, pyapp is not viable without massive workarounds that would be harder to maintain than PyInstaller.

---

## 6. Auto-Update Capabilities

This is pyapp's strongest feature compared to PyInstaller.

- Built-in `self update` command checks for newer versions and upgrades in-place
- `self restore` reinstalls the current version (useful for corruption)
- Version metadata available via `self metadata` command
- The update mechanism pulls from PyPI (or configured index) — no separate update server needed

However, the update mechanism re-runs pip, so all the GPU/native dependency concerns from sections 4-5 apply equally to updates.

---

## 7. Binary Size

### Without Embedding

The pyapp binary itself is ~5-15 MB (Rust binary). Python and packages are downloaded at runtime, stored in `~/.local/share/pyapp/`.

Total disk usage after first run:
- Python distribution: ~80-150 MB (uncompressed)
- Virtual environment + packages: depends on project (for whisper-key, probably ~200-400 MB for CPU, much more for GPU)

### With Full Embedding

If you embed the Python distribution (`PYAPP_DISTRIBUTION_EMBED=1`) and the project wheel (`PYAPP_PROJECT_PATH`), the binary grows significantly. Dependencies still install from network unless you pre-install them into the distribution.

For a fully offline build (custom distribution with all deps pre-installed), the binary would be comparable to or larger than the PyInstaller exe because you're embedding the same content plus the Rust wrapper overhead.

### Comparison for whisper-key

| Scenario | PyInstaller | PyApp |
|----------|------------|-------|
| Download size | 280 MB (CUDA) | ~10 MB (no embed) or ~300+ MB (full embed) |
| Disk after install | 280 MB | ~400+ MB (Python + venv + packages) |
| Network on first run | None | Required (without full embed) |

---

## 8. Gotchas, Limitations, and Known Issues

### Build Requirements
- **Rust toolchain required** — adds build complexity vs. PyInstaller's pure-Python build
- File paths in env vars must be **absolute** ([#75](https://github.com/ofek/pyapp/issues/75))
- Cross-compilation requires the `cross` tool and local repository method

### Runtime Issues
- **Corporate proxies** cause SSL errors — pyapp doesn't use system certificates by default ([#200](https://github.com/ofek/pyapp/issues/200), [#224](https://github.com/ofek/pyapp/issues/224))
- **First-run latency** can be significant (downloading Python + installing packages)
- No way to show a splash screen during bootstrap ([#140](https://github.com/ofek/pyapp/issues/140))
- Multi-module projects with local imports can fail if not properly packaged as wheels ([#148](https://github.com/ofek/pyapp/issues/148))

### Design Limitations
- No equivalent to PyInstaller's `--add-binary` or `--add-data` ([#203](https://github.com/ofek/pyapp/issues/203))
- No source code protection (all Python source is visible in the installed venv)
- No built-in offline/air-gapped mode without manual distribution preparation ([#117](https://github.com/ofek/pyapp/issues/117))
- Name confusion with unrelated `pyapp` package on PyPI ([#208](https://github.com/ofek/pyapp/issues/208))
- Cowsay example in docs reported broken by multiple users ([#182](https://github.com/ofek/pyapp/issues/182), [#191](https://github.com/ofek/pyapp/issues/191))

### Maturity
- v0.29.0 — still pre-1.0
- Small contributor base (14 contributors, ~184 commits)
- Limited real-world adoption for complex desktop applications
- Most usage appears to be CLI tools, not GUI applications with native dependencies

---

## 9. Example Projects and Tooling

### Projects Using PyApp
- **Hatch** (by the same author) — uses pyapp via its [binary builder plugin](https://hatch.pypa.io/latest/plugins/builder/binary/) to produce standalone executables
- **[Box](https://github.com/trappitsch/box)** (9 stars) — CLI wrapper that automates pyapp builds from pyproject.toml, early development
- **[hatch-build-isolated-binary](https://github.com/hobbsd/hatch-build-isolated-binary)** — script for building offline-capable pyapp binaries via Hatch

### Hatch Integration

If using Hatch as a build system, pyapp integration is streamlined:

```toml
[tool.hatch.build.targets.binary]
python-version = "3.12"
scripts = ["whisper-key"]
```

Build with `hatch build -t binary`. Requires Rust toolchain installed.

### Notable Absence

No examples found of pyapp being used for:
- Desktop GUI applications with complex native dependencies
- Applications requiring GPU runtime libraries
- Applications comparable in complexity to whisper-key-local

---

## 10. Recommendation for whisper-key-local

**Do not switch to pyapp.** The project's dependency profile makes it a poor fit:

1. **GPU libraries cannot be bundled** — CUDA/ROCm runtime libs need `--add-binary` equivalent which doesn't exist
2. **Offline-first is important** — users expect a download-and-run experience, not a download-then-wait-for-more-downloads experience
3. **Native dependency complexity** — ctranslate2 GPU wheels, custom ROCm builds, and platform-specific audio libraries make pip-at-runtime fragile
4. **No real-world precedent** — no comparable projects (GUI + GPU + native deps) use pyapp successfully

PyApp is well-suited for **CLI tools and simple applications** that have pure-Python or well-packaged PyPI dependencies. For whisper-key-local's use case, PyInstaller remains the better choice despite its larger output size and antivirus false positives.

### If Reconsidering Later

PyApp could become viable if:
- Feature [#203](https://github.com/ofek/pyapp/issues/203) (binary embedding) is implemented
- A reliable GPU wheel index is established for ctranslate2
- Built-in offline bundling is added
- The project reaches 1.0 maturity
