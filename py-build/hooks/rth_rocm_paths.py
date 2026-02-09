import os
import sys
import ctypes

if sys.platform == "win32":
    hip_path = os.environ.get("HIP_PATH")
    if hip_path:
        hip_bin = os.path.join(hip_path, "bin")
        if os.path.isdir(hip_bin):
            os.add_dll_directory(hip_bin)
            os.environ["PATH"] = hip_bin + ";" + os.environ.get("PATH", "")

            for dll_name in ("amdhip64_6.dll", "amdhip64_7.dll", "rocblas.dll"):
                dll_path = os.path.join(hip_bin, dll_name)
                if os.path.isfile(dll_path):
                    try:
                        ctypes.WinDLL(dll_path)
                    except OSError:
                        pass
