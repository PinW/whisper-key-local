import os
import shutil
import subprocess
import sys
from pathlib import Path

print("=" * 80)
print("PyAudioWPatch PortAudio DLL Extractor")
print("=" * 80)

print("\n[1/5] Installing PyAudioWPatch to get WASAPI loopback-enabled PortAudio DLL...")
try:
    subprocess.run([sys.executable, "-m", "pip", "install", "pyaudiowpatch"],
                   check=True, capture_output=True)
    print("✓ PyAudioWPatch installed successfully")
except subprocess.CalledProcessError as e:
    print(f"✗ Failed to install PyAudioWPatch: {e}")
    sys.exit(1)

print("\n[2/5] Locating PyAudioWPatch installation directory...")
try:
    result = subprocess.run([sys.executable, "-c",
                           "import pyaudiowpatch; print(pyaudiowpatch.__path__[0])"],
                          check=True, capture_output=True, text=True)
    pyaudiowpatch_dir = Path(result.stdout.strip())
    print(f"✓ Found PyAudioWPatch at: {pyaudiowpatch_dir}")
except subprocess.CalledProcessError as e:
    print(f"✗ Failed to locate PyAudioWPatch: {e}")
    sys.exit(1)

print("\n[3/5] Searching for PortAudio DLL in PyAudioWPatch directory...")
possible_dll_names = ["_portaudio.pyd", "portaudio.dll", "_portaudio.dll"]
dll_path = None

for dll_name in possible_dll_names:
    candidate = pyaudiowpatch_dir / dll_name
    if candidate.exists():
        dll_path = candidate
        print(f"✓ Found DLL: {dll_path}")
        break

if dll_path is None:
    print("✗ Could not find PortAudio DLL in PyAudioWPatch directory")
    print(f"   Searched for: {possible_dll_names}")
    print(f"   Directory contents:")
    for item in pyaudiowpatch_dir.iterdir():
        print(f"     - {item.name}")
    sys.exit(1)

print("\n[4/5] Creating dedicated directory for custom PortAudio DLL...")
custom_dll_dir = Path.home() / "whisper-key-portaudio"
custom_dll_dir.mkdir(exist_ok=True)
print(f"✓ Created directory: {custom_dll_dir}")

target_dll = custom_dll_dir / "portaudio.dll"
shutil.copy2(dll_path, target_dll)
print(f"✓ Copied DLL to: {target_dll}")

print("\n[5/5] PATH configuration required:")
print(f"\n    You need to add this directory to your Windows PATH:")
print(f"    {custom_dll_dir}")
print(f"\n    PowerShell command to add to PATH (run as Administrator):")
print(f'    $env:Path += ";{custom_dll_dir}"')
print(f'\n    Or add permanently via System Properties > Environment Variables')

print("\n" + "=" * 80)
print("NEXT STEPS:")
print("=" * 80)
print("1. Add the directory to your Windows PATH (see above)")
print("2. RESTART your terminal/IDE to pick up PATH changes")
print("3. Run: python documentation/temp/check_loopback_devices.py")
print("4. Look for devices with '[Loopback]' in the output")
print("\nIf loopback devices appear, the custom PortAudio DLL is working!")
