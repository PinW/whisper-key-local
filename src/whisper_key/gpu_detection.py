import logging
import subprocess
import sys

from dataclasses import dataclass

logger = logging.getLogger(__name__)

_NO_WINDOW = {'creationflags': 0x08000000} if sys.platform == 'win32' else {}


@dataclass
class GpuInfo:
    vendor: str | None
    name: str | None
    cuda_available: bool


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


def _check_cuda_runtime() -> bool:
    try:
        import ctranslate2
        supported = ctranslate2.get_supported_compute_types('cuda')
        return len(supported) > 0
    except Exception:
        return False


def detect_gpu() -> GpuInfo:
    nvidia_name = _detect_nvidia_gpu()
    if nvidia_name:
        return GpuInfo(vendor="nvidia", name=nvidia_name, cuda_available=_check_cuda_runtime())

    amd_name = _detect_amd_gpu()
    if amd_name:
        return GpuInfo(vendor="amd", name=amd_name, cuda_available=_check_cuda_runtime())

    return GpuInfo(vendor=None, name=None, cuda_available=False)


def print_gpu_status(gpu_info: GpuInfo, configured_device: str):
    if gpu_info.name:
        print(f"   ✓ Detected {gpu_info.name}")
        if configured_device == 'cuda' and not gpu_info.cuda_available:
            print("   ⚠ CUDA/ROCm runtime not available — see docs/gpu-setup.md")
        elif configured_device != 'cuda' and gpu_info.cuda_available:
            print("   ℹ GPU ready — set device: cuda in settings for faster transcription")
    elif configured_device == 'cuda':
        print("   ⚠ device: cuda but no GPU detected — transcription may fail")
