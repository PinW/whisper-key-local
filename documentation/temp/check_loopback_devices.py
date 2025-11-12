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

    is_loopback = "[Loopback]" in device['name'] or "(Loopback)" in device['name']
    if is_loopback:
        print(f"  >>> LOOPBACK DEVICE FOUND! <<<")

    print()

print("=" * 80)
print("\nLooking for devices with '[Loopback]' or '(Loopback)' in name...")

loopback_devices = [d for d in devices if "[Loopback]" in d['name'] or "(Loopback)" in d['name']]

if loopback_devices:
    print(f"\n✓ Found {len(loopback_devices)} loopback device(s)!")
    for d in loopback_devices:
        print(f"  - {d['name']}")
else:
    print("\n✗ No loopback devices found in device list.")
    print("   This means sounddevice's PortAudio doesn't have WASAPI loopback support.")

print("\n" + "=" * 80)
print("\nChecking if PaWasapi_IsLoopback function is available...")
try:
    # Try to access the loopback detection function added in PR #392
    sd._lib.PaWasapi_IsLoopback
    print("✓ PaWasapi_IsLoopback function is available!")

    print("\nTesting loopback detection on output devices:")
    for idx, device in enumerate(devices):
        if device['max_output_channels'] > 0:
            try:
                is_loopback = sd._lib.PaWasapi_IsLoopback(idx)
                print(f"  Device {idx} ({device['name'][:50]}...): {'LOOPBACK' if is_loopback else 'NOT loopback'}")
            except:
                pass

except AttributeError:
    print("✗ PaWasapi_IsLoopback function not available.")
    print("   sounddevice version may be too old (need >= 0.4.5)")
