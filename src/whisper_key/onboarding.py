import subprocess
import sys
import webbrowser

from .platform import app
from .terminal_ui import prompt_choice

INSTALL_GPU = 1
USE_CPU = 2
NEVER_ASK = 3

BOLD_GREEN = "\x1b[1;32m"
BOLD_RED = "\x1b[1;31m"
RESET = "\x1b[0m"

_PY_TAG = f"cp{sys.version_info.major}{sys.version_info.minor}"

NVIDIA_PACKAGES = [
    "nvidia-cuda-runtime-cu12",
    "nvidia-cublas-cu12",
    "nvidia-cudnn-cu12",
]

_ROCM_72_BASE = "https://repo.radeon.com/rocm/windows/rocm-rel-7.2"
_CT2_RDNA2_BASE = "https://github.com/PinW/ctranslate2-rocm-wheels/releases/download/v4.7.1-rocm72"

ROCM_72_PACKAGES = [
    f"{_ROCM_72_BASE}/rocm_sdk_core-7.2.0.dev0-py3-none-win_amd64.whl",
    f"{_ROCM_72_BASE}/rocm_sdk_libraries_custom-7.2.0.dev0-py3-none-win_amd64.whl",
    f"{_ROCM_72_BASE}/rocm-7.2.0.dev0.tar.gz",
]

CT2_WHEEL_URLS = {
    'amd_rdna2+': f"{_CT2_RDNA2_BASE}/ctranslate2-4.7.1-{_PY_TAG}-{_PY_TAG}-win_amd64.whl",
}

RDNA1_SETUP_URL = "https://github.com/PinW/ctranslate2-rocm-rdna1"

GPU_SIZES = {
    'nvidia': {'download': '1.2 GB', 'disk': '1.8 GB'},
    'amd_rdna2+': {'download': '1.1 GB', 'disk': '3.3 GB'},
}


def check_gpu(gpu_class, gpu_name, ct2_works, configured_device, config_manager):
    onboarding_config = config_manager.config.get('onboarding', {})
    gpu_status = onboarding_config.get('gpu', 'pending')

    if gpu_status in ('complete', 'skipped'):
        return

    if not gpu_class:
        config_manager.update_user_setting('onboarding', 'gpu_class', 'integrated_cpu')
        config_manager.update_user_setting('onboarding', 'gpu', 'skipped')
        return

    if ct2_works and configured_device == 'cuda':
        config_manager.update_user_setting('onboarding', 'gpu_class', gpu_class)
        config_manager.update_user_setting('onboarding', 'gpu', 'complete')
        return

    if gpu_class == 'amd_rdna1':
        _prompt_rdna1(gpu_name, config_manager)
        return

    _prompt_and_install(gpu_class, gpu_name, config_manager)


RUNTIME_LABELS = {
    'nvidia': 'CUDA',
    'amd_rdna2+': 'ROCm 7.2',
}


def _prompt_and_install(gpu_class, gpu_name, config_manager):
    sizes = GPU_SIZES.get(gpu_class, {'download': '1 GB', 'disk': '1 GB'})
    runtime = RUNTIME_LABELS.get(gpu_class, 'GPU')

    choice = prompt_choice(
        "GPU acceleration available",
        [
            (
                f"Setup GPU, install {runtime}",
                f"{sizes['download']} download, {sizes['disk']} disk space"
            ),
            (
                "Skip for now",
                "Use CPU this session"
            ),
            (
                "Use CPU only",
                "Don't ask again"
            ),
        ],
        subtitle=f"Use {gpu_name} for fast transcription?",
    )

    print()

    if choice == INSTALL_GPU:
        _install_gpu_packages(gpu_class, gpu_name, config_manager)
    elif choice == NEVER_ASK:
        _ensure_cpu_config(config_manager)
        config_manager.update_user_setting('onboarding', 'gpu_class', gpu_class)
        config_manager.update_user_setting('onboarding', 'gpu', 'skipped')
    else:
        _ensure_cpu_config(config_manager)


def _ensure_cpu_config(config_manager):
    config_manager.update_user_setting('whisper', 'device', 'cpu')
    config_manager.update_user_setting('whisper', 'compute_type', 'int8')


def _install_gpu_packages(gpu_class, gpu_name, config_manager):
    runtime = RUNTIME_LABELS.get(gpu_class, 'GPU')
    print(f"{BOLD_GREEN}Installing {runtime} to enable GPU acceleration for {gpu_name}...{RESET}\n")

    success = True

    if gpu_class == 'nvidia':
        success = _pip_install(NVIDIA_PACKAGES)
    elif gpu_class == 'amd_rdna2+':
        success = _pip_install(ROCM_72_PACKAGES)
        if success:
            ct2_url = get_ct2_wheel_url(gpu_class)
            if ct2_url:
                success = _pip_install_wheel(ct2_url)
            else:
                print(f"\n{BOLD_RED}No CTranslate2 ROCm wheel available for Python {_PY_TAG}.{RESET}")
                success = False

    if not success:
        print(f"\n{BOLD_RED}GPU setup failed. You'll be prompted again next launch.{RESET}\n")
        return

    config_manager.update_user_setting('whisper', 'device', 'cuda')
    config_manager.update_user_setting('whisper', 'compute_type', 'float16')

    print(f"\n{BOLD_GREEN}GPU acceleration installed. Please restart Whisper Key.{RESET}\n")
    sys.exit(0)


def _prompt_rdna1(gpu_name, config_manager):
    choice = prompt_choice(
        "GPU acceleration available",
        [
            (
                "Open setup guide in browser",
                "RDNA 1 GPUs require manual setup"
            ),
            (
                "Skip for now",
                "Use CPU transcription for this session"
            ),
            (
                "Use CPU only",
                "Don't ask again"
            ),
        ],
        subtitle=f"Use {gpu_name} for fast transcription?",
    )

    print()

    if choice == INSTALL_GPU:
        webbrowser.open(RDNA1_SETUP_URL)
        print(f"   Setup guide: {RDNA1_SETUP_URL}")
        print()
        print("   Press any key to exit...", end="", flush=True)
        app.getch()
        sys.exit(0)
    elif choice == NEVER_ASK:
        _ensure_cpu_config(config_manager)
        config_manager.update_user_setting('onboarding', 'gpu_class', 'amd_rdna1')
        config_manager.update_user_setting('onboarding', 'gpu', 'skipped')
    else:
        _ensure_cpu_config(config_manager)


def _pip_install(packages):
    cmd = [sys.executable, "-m", "pip", "install", "--no-cache-dir"] + packages
    print("   Downloading runtime libraries... (this may take a few minutes)")
    result = subprocess.run(cmd)
    return result.returncode == 0


def _pip_install_wheel(url):
    print("   Installing GPU-optimized CTranslate2...")
    result = subprocess.run(
        [sys.executable, "-m", "pip", "install", "--force-reinstall", "--no-deps", url]
    )
    return result.returncode == 0


def get_ct2_wheel_url(gpu_class):
    return CT2_WHEEL_URLS.get(gpu_class)


def restore_gpu_packages(config_manager):
    gpu_class = config_manager.config.get('onboarding', {}).get('gpu_class')
    if not gpu_class or not gpu_class.startswith('amd'):
        return

    ct2_url = get_ct2_wheel_url(gpu_class)
    if not ct2_url:
        return

    print("   Restoring GPU packages...")
    result = subprocess.run(
        [sys.executable, "-m", "pip", "install", "--force-reinstall", "--no-deps", ct2_url]
    )
    if result.returncode != 0:
        print("   Failed to restore GPU packages. GPU acceleration may need to be re-installed.")
