import importlib.metadata
import importlib.util
import logging
import os
import pathlib
import site
import subprocess

logger = logging.getLogger(__name__)

_NO_WINDOW = {'creationflags': 0x08000000}


def detect_and_print(configured_device):
    gpu_vendor, gpu_name = _detect_gpu()
    if not gpu_name:
        return

    _status("🖥️ System check...")
    _status(f"   ✓ Detected {gpu_name}")

    runtime_version = None
    if gpu_vendor == 'nvidia':
        runtime_version = _find_cuda_runtime()
        if runtime_version:
            _status(f"   ✓ NVIDIA CUDA {runtime_version} runtime available")
    elif gpu_vendor == 'amd':
        runtime_version = _find_rocm_runtime()
        if runtime_version:
            _status(f"   ✓ AMD ROCm HIP {runtime_version} runtime available")

    ct2_variant = _detect_ct2_variant()
    if ct2_variant != 'not_installed':
        ct2_version = _detect_ct2_version()[0]
        variant_label = {'cuda': 'CUDA', 'rocm': 'ROCm'}.get(ct2_variant, ct2_variant)
        _status(f"   ✓ CTranslate2 {ct2_version} ({variant_label})")
    else:
        _status("   ✗ CTranslate2 not installed", 'warning')

    if configured_device == 'cuda' and ct2_variant != 'not_installed':
        if ct2_variant == 'rocm' and gpu_vendor == 'nvidia':
            _status("   ✗ ctranslate2 is built for ROCm (AMD)", 'warning')
        elif ct2_variant == 'cuda' and gpu_vendor == 'amd':
            _status("   ✗ ctranslate2 is built for CUDA (NVIDIA)", 'warning')
        elif not _test_ct2_gpu():
            if gpu_vendor == 'nvidia':
                if runtime_version:
                    _status("   ✗ CUDA libraries found but failed to initialize", 'warning')
                else:
                    _status("   ✗ CUDA Toolkit 12 not found", 'warning')
            else:
                if runtime_version:
                    _status("   ✗ ROCm libraries found but failed to initialize", 'warning')
                else:
                    _status("   ✗ ROCm SDK not found", 'warning')
        else:
            _status("   ✓ GPU acceleration available")


def _status(msg, level='info'):
    print(msg)
    getattr(logger, level)(msg.strip())


def _detect_gpu() -> tuple[str | None, str | None]:
    nvidia = _detect_nvidia_gpu()
    if nvidia:
        return 'nvidia', nvidia

    amd = _detect_amd_gpu()
    if amd:
        return 'amd', amd

    return None, None


def _detect_nvidia_gpu() -> str | None:
    try:
        result = subprocess.run(
            ['nvidia-smi', '--query-gpu=name', '--format=csv,noheader'],
            capture_output=True, text=True, timeout=5, **_NO_WINDOW
        )
        if result.returncode == 0 and result.stdout.strip():
            return result.stdout.strip().split('\n')[0].strip()
    except (FileNotFoundError, subprocess.TimeoutExpired):
        pass
    return None


def _detect_amd_gpu() -> str | None:
    try:
        result = subprocess.run(
            ['powershell.exe', '-NoProfile', '-Command',
             "(Get-CimInstance Win32_VideoController"
             " | Where-Object {$_.Name -match 'AMD|Radeon'}).Name"],
            capture_output=True, text=True, timeout=5, **_NO_WINDOW
        )
        if result.returncode == 0 and result.stdout.strip():
            return result.stdout.strip().split('\n')[0].strip()
    except (FileNotFoundError, subprocess.TimeoutExpired):
        pass
    return None


def _find_cuda_runtime() -> str | None:
    cuda_path = os.environ.get('CUDA_PATH')
    if cuda_path and os.path.isfile(os.path.join(cuda_path, 'bin', 'cublas64_12.dll')):
        return '12'

    for sp in site.getsitepackages():
        cublas_bin = os.path.join(sp, 'nvidia', 'cublas', 'bin')
        if os.path.isdir(cublas_bin) and any(pathlib.Path(cublas_bin).glob('cublas64_12*')):
            return '12'

    for d in os.environ.get('PATH', '').split(os.pathsep):
        if os.path.isfile(os.path.join(d, 'cublas64_12.dll')):
            return '12'

    return None


def _find_rocm_runtime() -> str | None:
    def _hip_version() -> str:
        try:
            version = importlib.metadata.version('rocm-sdk-core')
            return '.'.join(version.split('.')[:2])
        except importlib.metadata.PackageNotFoundError:
            return '7'

    for var in ('HIP_PATH', 'HIP_DIR'):
        hip_path = os.environ.get(var)
        if hip_path and os.path.isfile(os.path.join(hip_path, 'bin', 'amdhip64_7.dll')):
            return _hip_version()

    spec = importlib.util.find_spec('_rocm_sdk_core')
    if spec and spec.submodule_search_locations:
        core_bin = os.path.join(spec.submodule_search_locations[0], 'bin')
        if os.path.isfile(os.path.join(core_bin, 'amdhip64_7.dll')):
            return _hip_version()

    for d in os.environ.get('PATH', '').split(os.pathsep):
        if os.path.isfile(os.path.join(d, 'amdhip64_7.dll')):
            return _hip_version()

    return None


def _read_pe_imports(dll_path: pathlib.Path) -> list[str]:
    try:
        return _parse_pe_imports(dll_path)
    except Exception:
        return []


def _parse_pe_imports(dll_path: pathlib.Path) -> list[str]:
    with open(dll_path, 'rb') as f:
        f.seek(0x3C)
        pe_offset = int.from_bytes(f.read(4), 'little')

        f.seek(pe_offset + 4)
        f.read(2)
        num_sections = int.from_bytes(f.read(2), 'little')
        f.read(12)
        optional_header_size = int.from_bytes(f.read(2), 'little')
        f.read(2)

        opt_start = f.tell()
        magic = int.from_bytes(f.read(2), 'little')
        is_pe32_plus = magic == 0x20B

        data_dir_offset = opt_start + (112 if is_pe32_plus else 96)
        f.seek(data_dir_offset + 8)
        import_rva = int.from_bytes(f.read(4), 'little')
        if import_rva == 0:
            return []

        sections_offset = opt_start + optional_header_size
        sections = []
        for i in range(num_sections):
            f.seek(sections_offset + i * 40)
            f.read(8)
            virtual_size = int.from_bytes(f.read(4), 'little')
            virtual_addr = int.from_bytes(f.read(4), 'little')
            raw_size = int.from_bytes(f.read(4), 'little')
            raw_offset = int.from_bytes(f.read(4), 'little')
            sections.append((virtual_addr, virtual_size, raw_offset, raw_size))

        def rva_to_offset(rva):
            for va, vs, ro, rs in sections:
                if va <= rva < va + vs:
                    return ro + (rva - va)
            return None

        entry_offset = rva_to_offset(import_rva)
        if entry_offset is None:
            return []

        imports = []
        while True:
            f.seek(entry_offset)
            entry = f.read(20)
            if len(entry) < 20:
                break
            name_rva = int.from_bytes(entry[12:16], 'little')
            if name_rva == 0:
                break
            name_offset = rva_to_offset(name_rva)
            if name_offset:
                f.seek(name_offset)
                dll_name = b''
                while True:
                    ch = f.read(1)
                    if not ch or ch == b'\x00':
                        break
                    dll_name += ch
                if dll_name:
                    imports.append(dll_name.decode('ascii', errors='ignore').lower())
            entry_offset += 20

        return imports


def _detect_ct2_variant() -> str:
    try:
        import ctranslate2
    except ImportError:
        return 'not_installed'

    dll_path = pathlib.Path(ctranslate2.__file__).parent / 'ctranslate2.dll'
    if not dll_path.exists():
        return 'cuda'

    imports = _read_pe_imports(dll_path)
    if any('amdhip' in name or 'hipblas' in name for name in imports):
        return 'rocm'
    return 'cuda'


def _detect_ct2_version() -> tuple[str, bool]:
    try:
        version = importlib.metadata.version('ctranslate2')
        return version, '+' in version
    except importlib.metadata.PackageNotFoundError:
        return 'unknown', False


def _test_ct2_gpu() -> bool:
    try:
        import ctranslate2
        supported = ctranslate2.get_supported_compute_types('cuda')
        return len(supported) > 0
    except Exception:
        return False
