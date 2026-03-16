from .platform import gpu as _platform_gpu


def detect_and_print(configured_device):
    _platform_gpu.detect_and_print(configured_device)
