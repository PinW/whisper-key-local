import importlib.metadata
import importlib.util
import logging
import os
import pathlib
import site
import subprocess
import sys

from dataclasses import dataclass

logger = logging.getLogger(__name__)

_NO_WINDOW = {'creationflags': 0x08000000} if sys.platform == 'win32' else {}


@dataclass
class Ct2Info:
    version: str
    variant: str            # "cuda", "rocm", "not_installed"
    is_custom: bool
    runtime_available: bool


@dataclass
class GpuInfo:
    vendor: str | None
    name: str | None
    ct2: Ct2Info


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
    if sys.platform != 'win32':
        return None
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


def _read_pe_imports(dll_path: pathlib.Path) -> list[str]:
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
                if va <= rva < va + rs:
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


def _check_cuda_runtime() -> bool:
    try:
        import ctranslate2
        supported = ctranslate2.get_supported_compute_types('cuda')
        return len(supported) > 0
    except Exception:
        return False


def _find_cuda_runtime() -> bool:
    cuda_path = os.environ.get('CUDA_PATH')
    if cuda_path and os.path.isfile(os.path.join(cuda_path, 'bin', 'cublas64_12.dll')):
        return True

    for sp in site.getsitepackages():
        cublas_bin = os.path.join(sp, 'nvidia', 'cublas', 'bin')
        if os.path.isdir(cublas_bin) and any(pathlib.Path(cublas_bin).glob('cublas64_12*')):
            return True

    for d in os.environ.get('PATH', '').split(os.pathsep):
        if os.path.isfile(os.path.join(d, 'cublas64_12.dll')):
            return True

    return False


def _find_rocm_runtime() -> bool:
    for var in ('HIP_PATH', 'HIP_DIR'):
        hip_path = os.environ.get(var)
        if hip_path and os.path.isfile(os.path.join(hip_path, 'bin', 'amdhip64_7.dll')):
            return True

    spec = importlib.util.find_spec('_rocm_sdk_core')
    if spec and spec.submodule_search_locations:
        core_bin = os.path.join(spec.submodule_search_locations[0], 'bin')
        if os.path.isfile(os.path.join(core_bin, 'amdhip64_7.dll')):
            return True

    for d in os.environ.get('PATH', '').split(os.pathsep):
        if os.path.isfile(os.path.join(d, 'amdhip64_7.dll')):
            return True

    return False


def _detect_ct2() -> Ct2Info:
    variant = _detect_ct2_variant()
    version, is_custom = _detect_ct2_version()
    runtime_available = _check_cuda_runtime() if variant != 'not_installed' else False
    return Ct2Info(version=version, variant=variant, is_custom=is_custom, runtime_available=runtime_available)


def detect_gpu() -> GpuInfo:
    ct2 = _detect_ct2()

    nvidia_name = _detect_nvidia_gpu()
    if nvidia_name:
        return GpuInfo(vendor="nvidia", name=nvidia_name, ct2=ct2)

    amd_name = _detect_amd_gpu()
    if amd_name:
        return GpuInfo(vendor="amd", name=amd_name, ct2=ct2)

    return GpuInfo(vendor=None, name=None, ct2=ct2)


def _gpu_status(msg, level='info'):
    print(msg)
    getattr(logger, level)(msg.strip())


def print_gpu_status(gpu_info: GpuInfo, configured_device: str):
    ct2 = gpu_info.ct2

    if gpu_info.name:
        _gpu_status(f"   ✓ Detected {gpu_info.name}")

    if configured_device == 'cuda':
        if not gpu_info.name:
            _gpu_status("   ⚠ device: cuda but no GPU detected — transcription may fail", 'warning')
        elif ct2.variant == 'not_installed':
            _gpu_status("   ⚠ ctranslate2 not found", 'warning')
        elif ct2.variant == 'rocm' and gpu_info.vendor == 'nvidia':
            _gpu_status("   ⚠ ctranslate2 is built for ROCm — install the standard wheel (see docs/gpu-setup.md)", 'warning')
        elif ct2.variant == 'cuda' and gpu_info.vendor == 'amd':
            _gpu_status("   ⚠ ctranslate2 is built for CUDA — install the ROCm wheel (see docs/gpu-setup.md)", 'warning')
        elif not ct2.runtime_available:
            if gpu_info.vendor == 'nvidia':
                if _find_cuda_runtime():
                    _gpu_status("   ⚠ CUDA libraries found but failed to initialize — see docs/gpu-setup.md", 'warning')
                else:
                    _gpu_status("   ⚠ CUDA Toolkit 12 not found — see docs/gpu-setup.md", 'warning')
            else:
                if _find_rocm_runtime():
                    _gpu_status("   ⚠ ROCm libraries found but failed to initialize — see docs/gpu-setup.md", 'warning')
                else:
                    _gpu_status("   ⚠ ROCm SDK not found — see docs/gpu-setup.md", 'warning')
    elif gpu_info.name and ct2.runtime_available:
        _gpu_status("   ℹ GPU ready — set device: cuda in settings for faster transcription")
