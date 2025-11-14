import sounddevice as sd

print("Checking for WASAPI loopback devices...\n")
print("=" * 80)

devices = sd.query_devices()

print(f"\nTotal devices found: {len(devices)}\n")

for idx, device in enumerate(devices):
    print(f"Device {idx}:")
    print(f"  Name: {device['name']}")
    print(f"  Input channels: {device['max_input_channels']}")
    print(f"  Output channels: {device['max_output_channels']}")
    print(f"  Host API: {sd.query_hostapis(device['hostapi'])['name']}")

    name_lower = device['name'].lower()
    is_loopback = "[loopback]" in name_lower or "(loopback)" in name_lower
    if is_loopback:
        print(f"  >>> LOOPBACK DEVICE FOUND! <<<")

    print()

print("=" * 80)
print("\nLooking for devices with '[Loopback]' or '(Loopback)' in name...")

loopback_devices = [
    d for d in devices
    if "[loopback]" in d['name'].lower() or "(loopback)" in d['name'].lower()
]

if loopback_devices:
    print(f"\n✓ Found {len(loopback_devices)} loopback device(s)!")
    for d in loopback_devices:
        print(f"  - {d['name']}")
else:
    print("\n✗ No loopback devices found in device list.")
    print("   This means sounddevice's PortAudio doesn't have WASAPI loopback support.")
