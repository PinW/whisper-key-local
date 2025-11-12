import subprocess
import sys
from pathlib import Path

print("=" * 80)
print("PyAudioWPatch Structure Inspector")
print("=" * 80)

print("\n[Step 1] Installing PyAudioWPatch...")
try:
    subprocess.run([sys.executable, "-m", "pip", "install", "pyaudiowpatch"],
                   check=True, capture_output=True)
    print("✓ Installed")
except subprocess.CalledProcessError:
    print("✓ Already installed or installation failed (continuing anyway)")

print("\n[Step 2] Locating PyAudioWPatch installation...")
try:
    result = subprocess.run([sys.executable, "-c",
                           "import pyaudiowpatch; print(pyaudiowpatch.__path__[0])"],
                          check=True, capture_output=True, text=True)
    package_dir = Path(result.stdout.strip())
    print(f"✓ Package location: {package_dir}")
except Exception as e:
    print(f"✗ Failed: {e}")
    sys.exit(1)

print("\n[Step 3] Listing all files in PyAudioWPatch directory:")
print("-" * 80)
for item in sorted(package_dir.rglob("*")):
    if item.is_file():
        size_kb = item.stat().st_size / 1024
        print(f"  {item.relative_to(package_dir)} ({size_kb:.1f} KB)")

print("\n" + "=" * 80)
print("Looking for PortAudio-related files:")
print("=" * 80)
portaudio_files = []
for item in package_dir.rglob("*"):
    if item.is_file():
        name_lower = item.name.lower()
        if 'portaudio' in name_lower or item.suffix in ['.dll', '.pyd', '.so']:
            size_kb = item.stat().st_size / 1024
            portaudio_files.append((item, size_kb))
            print(f"  ✓ {item.relative_to(package_dir)} ({size_kb:.1f} KB)")

if not portaudio_files:
    print("  ✗ No PortAudio-related files found")

print("\n" + "=" * 80)
print("Analysis:")
print("=" * 80)

pyd_files = [f for f, s in portaudio_files if f.suffix == '.pyd']
dll_files = [f for f, s in portaudio_files if f.suffix == '.dll']

if dll_files:
    print("✓ Found standalone DLL files:")
    for dll in dll_files:
        print(f"    - {dll.name}")
    print("\n  These can potentially be copied and renamed to portaudio.dll for sounddevice")
elif pyd_files:
    print("✓ Found .pyd extension module:")
    for pyd in pyd_files:
        print(f"    - {pyd.name}")
    print("\n  ⚠ .pyd files are Python extensions, not standalone DLLs")
    print("  ⚠ They have PortAudio compiled into them")
    print("  ⚠ We may need to extract the DLL or build PortAudio from source")
else:
    print("✗ No suitable files found")

print("\n" + "=" * 80)
print("Testing PyAudioWPatch for WASAPI loopback:")
print("=" * 80)

test_code = """
import pyaudiowpatch as pyaudio

p = pyaudio.PyAudio()
print(f"Total devices: {p.get_device_count()}")

loopback_devices = []
for i in range(p.get_device_count()):
    device_info = p.get_device_info_by_index(i)
    if device_info.get('maxInputChannels') > 0:
        is_loopback = p.get_loopback_device_info_generator(device_info)
        if is_loopback is not None:
            loopback_devices.append(device_info)
            print(f"  Loopback device found: {device_info['name']}")

p.terminate()

if loopback_devices:
    print(f"\\n✓ Found {len(loopback_devices)} WASAPI loopback device(s)")
else:
    print("\\n✗ No WASAPI loopback devices found")
"""

try:
    result = subprocess.run([sys.executable, "-c", test_code],
                          capture_output=True, text=True, timeout=10)
    print(result.stdout)
    if result.stderr:
        print("Errors:")
        print(result.stderr)
except Exception as e:
    print(f"✗ Test failed: {e}")
