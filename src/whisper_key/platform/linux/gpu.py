import subprocess
import logging

logger = logging.getLogger(__name__)

def detect_gpu():
    gpu_class = None
    gpu_name = None
    rocm_works = False
    cuda_works = False

    try:
        result = subprocess.run(['lspci', '-nn'], capture_output=True, text=True)
        output = result.stdout.lower()

        if 'amd' in output or 'advanced micro devices' in output:
            if 'rdna' in output or 'navi' in output or 'radeon rx 6' in output or 'radeon rx 7' in output:
                gpu_class = 'amd_rdna2+'
            elif 'radeon' in output:
                gpu_class = 'amd_rdna1'
            gpu_name = 'AMD GPU'
        elif 'nvidia' in output:
            gpu_class = 'nvidia'
            gpu_name = 'NVIDIA GPU'
    except Exception as e:
        logger.debug(f"lspci failed: {e}")

    try:
        result = subprocess.run(['rocminfo'], capture_output=True, text=True, timeout=5)
        if result.returncode == 0:
            rocm_works = True
            if not gpu_class:
                gpu_class = 'amd_rdna2+'
    except Exception:
        pass

    try:
        result = subprocess.run(['nvidia-smi'], capture_output=True, text=True, timeout=5)
        if result.returncode == 0:
            cuda_works = True
            if not gpu_class:
                gpu_class = 'nvidia'
    except Exception:
        pass

    return gpu_class, gpu_name, rocm_works or cuda_works


def detect_and_print(configured_device):
    gpu_class, gpu_name, ct2_works = detect_gpu()
    if gpu_class:
        print(f"   GPU detected: {gpu_name} ({gpu_class})")
        if ct2_works:
            print("   ✓ GPU acceleration available")
        else:
            print("   ✗ GPU acceleration not available")
    else:
        print("   No GPU detected")
    return gpu_class, gpu_name, ct2_works