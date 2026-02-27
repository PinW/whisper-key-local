import os
import shutil
import sys

if sys.platform == "win32":
    rocm_dirs = []

    hip_path = os.environ.get("HIP_PATH")
    if hip_path:
        hip_bin = os.path.join(hip_path, "bin")
        if os.path.isdir(hip_bin):
            rocm_dirs.append(hip_bin)

    python_exe = shutil.which("python")
    if python_exe:
        site_packages = os.path.join(os.path.dirname(python_exe), "Lib", "site-packages")
        for pkg in ("_rocm_sdk_core", "_rocm_sdk_libraries_custom"):
            bin_dir = os.path.join(site_packages, pkg, "bin")
            if os.path.isdir(bin_dir):
                rocm_dirs.append(bin_dir)

    for d in rocm_dirs:
        os.add_dll_directory(d)
        os.environ["PATH"] = d + ";" + os.environ.get("PATH", "")
