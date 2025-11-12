# Audio Device Selection Research

## Overview

This document explains how to enumerate and select audio input devices for transcription in whisper-key using the sounddevice library.

## Key Concepts

### Input vs Output Devices

**Input devices** are what we primarily need for transcription:
- Physical microphones (USB, built-in, etc.)
- Virtual audio cables (VB-Audio, etc.)
- **System audio capture** (Stereo Mix, What U Hear, etc.) - These are technically "output" devices that can be used as input sources to capture system audio

**Output devices** are for playback but can be relevant:
- Some Windows systems have virtual devices like "Stereo Mix" that capture system output as an input source
- These allow transcribing audio from applications, videos, music, etc.

## How sounddevice Works

### Device Enumeration

The `sd.query_devices()` function returns information about all available audio devices:

```python
import sounddevice as sd

# Get all devices
all_devices = sd.query_devices()

# Get only input devices
input_devices = sd.query_devices(kind='input')

# Get specific device info
device_info = sd.query_devices(device_id)
```

### Device Information

Each device dictionary contains:
- `name`: Device identifier string
- `hostapi`: Associated host API ID (MME, DirectSound, WASAPI on Windows)
- `max_input_channels`: Number of input channels (0 if not an input device)
- `max_output_channels`: Number of output channels (0 if not an output device)
- `default_samplerate`: Native sampling frequency
- `default_low_input_latency`: Low latency setting
- `default_high_input_latency`: High latency setting

### Device Selection Methods

#### Method 1: Device ID (Numeric Index)
```python
sd.InputStream(device=3, samplerate=16000, channels=1)
```

#### Method 2: Device Name Substring (Case-insensitive)
```python
sd.InputStream(device='microphone', samplerate=16000, channels=1)
```

#### Method 3: Set Global Default
```python
sd.default.device = 3  # or 'microphone'
sd.InputStream(samplerate=16000, channels=1)  # Uses default
```

#### Method 4: Separate Input/Output Defaults
```python
sd.default.device = (3, 5)  # (input_device_id, output_device_id)
```

## Integration into audio_recorder.py

### Current Implementation

Currently, `audio_recorder.py` uses the system default input device:

```python
with sd.InputStream(samplerate=self.sample_rate,
                    channels=self.channels,
                    callback=audio_callback,
                    dtype=self.STREAM_DTYPE,
                    blocksize=blocksize):
```

### Proposed Changes

#### 1. Add device parameter to __init__

```python
def __init__(self,
             on_vad_event: Callable[[VadEvent], None],
             channels: int = 1,
             dtype: str = "float32",
             max_duration: int = 30,
             on_max_duration_reached: callable = None,
             vad_manager = None,
             device = None):  # NEW PARAMETER

    self.device = device  # Can be int (ID), str (name), or None (default)
```

#### 2. Add device enumeration method

```python
@staticmethod
def get_available_input_devices():
    """Returns list of available input devices with their details"""
    devices = []
    all_devices = sd.query_devices()

    for idx, device in enumerate(all_devices):
        if device['max_input_channels'] > 0:
            devices.append({
                'id': idx,
                'name': device['name'],
                'channels': device['max_input_channels'],
                'sample_rate': device['default_samplerate'],
                'hostapi': sd.query_hostapis(device['hostapi'])['name']
            })

    return devices

@staticmethod
def get_default_input_device():
    """Returns the default input device info"""
    return sd.query_devices(kind='input')
```

#### 3. Update _test_microphone to test selected device

```python
def _test_microphone(self):
    try:
        if self.device is not None:
            device_info = sd.query_devices(self.device, kind='input')
            self.logger.info(f"Selected microphone: {device_info['name']}")

            # Verify device settings are compatible
            sd.check_input_settings(
                device=self.device,
                channels=self.channels,
                samplerate=self.sample_rate,
                dtype=self.STREAM_DTYPE
            )
        else:
            default_input = sd.query_devices(kind='input')
            self.logger.info(f"Default microphone: {default_input['name']}")
    except Exception as e:
        self.logger.error(f"Microphone test failed: {e}")
        raise
```

#### 4. Update InputStream to use selected device

```python
with sd.InputStream(samplerate=self.sample_rate,
                    channels=self.channels,
                    callback=audio_callback,
                    dtype=self.STREAM_DTYPE,
                    blocksize=blocksize,
                    device=self.device):  # NEW PARAMETER
```

## Configuration Changes

### Add to config.defaults.yaml

```yaml
# =============================================================================
# AUDIO RECORDING SETTINGS
# =============================================================================
audio:
  # Sample rate is fixed at 16000 Hz for optimal Whisper and TEN VAD performance

  # Audio input device selection
  # Options:
  #   - null or "default": Use system default microphone
  #   - <device_id>: Numeric device ID from device list (e.g., 3)
  #   - "<device_name>": Case-insensitive substring of device name (e.g., "USB Microphone")
  #
  # Use tools/list_audio_devices.py to see available devices
  input_device: null

  # Audio channels
  # 1 = mono (recommended for speech)
  # 2 = stereo
  channels: 1

  # Recording format
  # Options: "float32", "int16", "int24", "int32"
  # float32 recommended for best quality
  dtype: float32

  # Maximum recording duration (seconds)
  # Set to 0 for unlimited recording
  max_duration: 900
```

## Utility Tool: List Audio Devices

Create `tools/list_audio_devices.py` to help users identify their devices:

```python
#!/usr/bin/env python3
import sounddevice as sd

def list_audio_devices():
    print("=" * 80)
    print("AVAILABLE AUDIO INPUT DEVICES")
    print("=" * 80)
    print()

    all_devices = sd.query_devices()
    default_input_id = sd.default.device[0]

    print("INPUT DEVICES (for recording/transcription):")
    print("-" * 80)

    for idx, device in enumerate(all_devices):
        if device['max_input_channels'] > 0:
            is_default = " ⭐ DEFAULT" if idx == default_input_id else ""
            hostapi = sd.query_hostapis(device['hostapi'])['name']

            print(f"[{idx}] {device['name']}{is_default}")
            print(f"    Channels: {device['max_input_channels']}")
            print(f"    Sample Rate: {device['default_samplerate']} Hz")
            print(f"    Host API: {hostapi}")
            print()

    print("=" * 80)
    print("USAGE:")
    print("=" * 80)
    print("1. Copy the device ID [number] or part of the device name")
    print("2. Edit your user settings (tools/open_user_settings.py)")
    print("3. Set audio.input_device to the device ID or name")
    print()
    print("Examples:")
    print("  input_device: 3          # Use device ID 3")
    print("  input_device: \"USB Mic\"   # Use device with 'USB Mic' in name")
    print("  input_device: null       # Use system default")
    print()

if __name__ == "__main__":
    list_audio_devices()
```

## Use Cases

### 1. Multiple Microphones
Users with multiple microphones can select which one to use:
- Built-in laptop mic
- External USB microphone
- Headset microphone
- Professional audio interface

### 2. System Audio Capture
On Windows, users can select "Stereo Mix" or similar devices to transcribe:
- Audio from videos/music
- Application audio
- System sounds
- Online meeting audio (check legal requirements)

### 3. Virtual Audio Cables
Power users can route audio through virtual cables for advanced setups:
- VB-Audio Virtual Cable
- OBS Virtual Camera audio
- Discord audio routing
- Application-specific audio capture

## Technical Considerations

### Sample Rate Compatibility
Whisper and TEN VAD require 16000 Hz. Some devices may not support this natively, requiring resampling.

### Host API on Windows
Windows has multiple audio APIs:
- **MME** (Multimedia Extensions): Older, higher latency
- **DirectSound**: Gaming-focused
- **WASAPI**: Modern, low latency (recommended)
- **WDM-KS**: Kernel streaming, very low latency

sounddevice will typically default to the best available API.

### Device Validation
Always validate device settings before recording:
```python
sd.check_input_settings(device=device_id, channels=1, samplerate=16000, dtype='float32')
```

## Testing Strategy

1. Test with default device (current behavior)
2. Test with explicit device ID selection
3. Test with device name substring selection
4. Test invalid device handling
5. Test device disconnection during recording
6. Test with multiple device types (USB, built-in, virtual)

## Error Handling

Handle common errors:
- Device not found (invalid ID or name)
- Device disconnected during recording
- Incompatible device settings
- Permissions issues
- Device already in use by another application

## Summary

The sounddevice library provides robust device enumeration and selection capabilities:

1. **Enumerate devices** with `sd.query_devices()`
2. **Select by ID** (numeric index) or **name** (substring matching)
3. **Pass device parameter** to `sd.InputStream(device=...)`
4. **Validate settings** with `sd.check_input_settings()`

Integration requires:
- Adding device parameter to AudioRecorder.__init__
- Updating InputStream creation
- Adding configuration option
- Creating utility tool for device listing
- Updating documentation
