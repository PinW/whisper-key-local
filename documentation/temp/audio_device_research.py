import sounddevice as sd
import json

print("=" * 80)
print("AUDIO DEVICE ENUMERATION RESEARCH")
print("=" * 80)

print("\n1. ALL AVAILABLE DEVICES:")
print("-" * 80)
all_devices = sd.query_devices()
print(all_devices)

print("\n2. DEVICE DETAILS (Structured):")
print("-" * 80)
for idx, device in enumerate(sd.query_devices()):
    print(f"\nDevice {idx}:")
    print(f"  Name: {device['name']}")
    print(f"  Host API: {device['hostapi']} ({sd.query_hostapis(device['hostapi'])['name']})")
    print(f"  Max Input Channels: {device['max_input_channels']}")
    print(f"  Max Output Channels: {device['max_output_channels']}")
    print(f"  Default Sample Rate: {device['default_samplerate']}")

    device_type = []
    if device['max_input_channels'] > 0:
        device_type.append("INPUT")
    if device['max_output_channels'] > 0:
        device_type.append("OUTPUT")
    print(f"  Type: {' + '.join(device_type)}")

print("\n3. INPUT DEVICES ONLY:")
print("-" * 80)
input_devices = sd.query_devices(kind='input')
if isinstance(input_devices, dict):
    print(f"Default input device: {input_devices['name']}")
else:
    for idx, device in enumerate(input_devices):
        if device['max_input_channels'] > 0:
            is_default = " (DEFAULT)" if idx == sd.default.device[0] else ""
            print(f"  [{idx}] {device['name']}{is_default}")

print("\n4. OUTPUT DEVICES ONLY:")
print("-" * 80)
output_devices = sd.query_devices(kind='output')
if isinstance(output_devices, dict):
    print(f"Default output device: {output_devices['name']}")
else:
    for idx, device in enumerate(output_devices):
        if device['max_output_channels'] > 0:
            is_default = " (DEFAULT)" if idx == sd.default.device[1] else ""
            print(f"  [{idx}] {device['name']}{is_default}")

print("\n5. DEFAULT DEVICES:")
print("-" * 80)
print(f"Default input device ID: {sd.default.device[0]}")
print(f"Default output device ID: {sd.default.device[1]}")
default_input = sd.query_devices(sd.default.device[0])
default_output = sd.query_devices(sd.default.device[1])
print(f"Default input: {default_input['name']}")
print(f"Default output: {default_output['name']}")

print("\n6. HOST APIs:")
print("-" * 80)
for idx, api in enumerate(sd.query_hostapis()):
    print(f"  [{idx}] {api['name']}")
    print(f"      Default Input Device: {api['default_input_device']}")
    print(f"      Default Output Device: {api['default_output_device']}")
    print(f"      Device Count: {api['device_count']}")

print("\n7. CHECKING INPUT SETTINGS COMPATIBILITY:")
print("-" * 80)
test_device = sd.default.device[0]
print(f"Testing device: {sd.query_devices(test_device)['name']}")
try:
    sd.check_input_settings(
        device=test_device,
        channels=1,
        samplerate=16000,
        dtype='float32'
    )
    print("✓ Settings compatible: 16000 Hz, 1 channel, float32")
except Exception as e:
    print(f"✗ Settings incompatible: {e}")

print("\n8. DEVICE SELECTION METHODS:")
print("-" * 80)
print("Method 1: By device ID")
print("  sd.InputStream(device=3, ...)")
print()
print("Method 2: By device name substring")
print("  sd.InputStream(device='microphone', ...)")
print()
print("Method 3: By setting default")
print("  sd.default.device = 3")
print("  sd.InputStream(...)")
print()
print("Method 4: Tuple for input/output")
print("  sd.default.device = (3, 5)  # (input_device, output_device)")

print("\n" + "=" * 80)
print("RESEARCH COMPLETE")
print("=" * 80)
