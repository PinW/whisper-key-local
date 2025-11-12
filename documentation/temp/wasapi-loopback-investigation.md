# WASAPI Loopback Investigation & Solution

## Problem Statement

We need to enable WASAPI loopback recording in sounddevice to capture system audio (output devices like speakers). Currently:

- Output devices have `max_input_channels = 0`
- Cannot open `sd.InputStream()` on output devices
- Error: "Invalid number of channels" or "Not an input device"

## Root Cause

sounddevice's bundled PortAudio DLL does not have WASAPI loopback support compiled in, even though:
- WASAPI loopback was merged into official PortAudio in 2021/2022
- PyAudioWPatch fork includes PortAudio with WASAPI loopback enabled
- Audacity uses a patched PortAudio with WASAPI loopback

## Proposed Solution

Replace sounddevice's bundled PortAudio DLL with PyAudioWPatch's WASAPI loopback-enabled version.

### How sounddevice finds PortAudio DLL

From sounddevice documentation:
> "On Windows, you can rename the library to portaudio.dll and move it to any directory in your %PATH%"

sounddevice uses CFFI to load PortAudio and searches:
1. Directories in Windows PATH environment variable
2. Its own bundled DLL (fallback)

### Investigation Steps

Run these two scripts to understand what's available:

#### Script 1: Inspect PyAudioWPatch Structure

```bash
python documentation/temp/inspect_pyaudiowpatch.py
```

This will:
- Install PyAudioWPatch
- Show all files in its package directory
- Identify if there's a standalone portaudio.dll or just a .pyd extension
- Test if PyAudioWPatch can detect loopback devices

#### Script 2: Extract PortAudio DLL (if available)

```bash
python documentation/temp/extract_portaudio_dll.py
```

This will:
- Install PyAudioWPatch
- Search for PortAudio DLL files
- Copy to `~/whisper-key-portaudio/portaudio.dll`
- Provide instructions to add to PATH

### Expected Outcomes

#### Best Case: Standalone DLL Available
If PyAudioWPatch includes a standalone `portaudio.dll`:
1. Copy it to a dedicated directory
2. Add that directory to Windows PATH
3. Restart terminal
4. sounddevice will automatically use the new DLL
5. Loopback devices will appear in `sd.query_devices()`

#### Likely Case: Only .pyd Extension Available
If PyAudioWPatch only has `_portaudio.pyd`:
- This is a Python extension module with PortAudio compiled into it
- Cannot be used directly by sounddevice
- Need alternative approach:
  - Build PortAudio from source with WASAPI loopback enabled
  - Or extract DLL from .pyd using DLL extraction tools
  - Or use Stereo Mix (Device 21) as workaround

### Testing Plan

After DLL replacement, run:

```bash
python documentation/temp/check_loopback_devices.py
```

Look for:
- Devices with `[Loopback]` or `(Loopback)` in the name
- Output devices that now show `max_input_channels > 0`
- PaWasapi_IsLoopback function availability

### Implementation After Success

Once loopback devices are accessible:

1. **Multi-channel support in AudioRecorder**:
   ```python
   # Detect device's native channel count
   device_info = sd.query_devices(self.device)
   device_channels = device_info['max_input_channels']

   # Open stream with device's native channels
   with sd.InputStream(
       samplerate=self.sample_rate,
       channels=device_channels,  # Use device's channels, not config
       device=self.device,
       callback=audio_callback
   ):
   ```

2. **Convert stereo to mono in callback**:
   ```python
   def audio_callback(audio_data, frames, _time, status):
       # audio_data shape: (frames, channels)
       if audio_data.shape[1] > 1:
           # Convert stereo to mono by averaging channels
           mono_data = np.mean(audio_data, axis=1, keepdims=True)
       else:
           mono_data = audio_data

       # Process mono_data as usual
       self.audio_data.append(mono_data.copy())
   ```

3. **Update device filter** (optional):
   ```python
   # In get_available_audio_devices(), include output devices:
   # Currently: if device['max_input_channels'] > 0 or device['max_output_channels'] > 0
   # After WASAPI: Output devices will have input channels via loopback
   ```

## Fallback: Stereo Mix

If DLL replacement fails, we already have "Stereo Mix" (Device 21):
- Built-in Windows loopback device (WDM-KS)
- Shows as 2-channel input device
- User must enable it in Windows Sound settings
- Works with current implementation after multi-channel support added

## Next Steps

1. Run `inspect_pyaudiowpatch.py` to see what's available
2. Based on results, either:
   - Run `extract_portaudio_dll.py` if standalone DLL found
   - Research building PortAudio from source
   - Implement Stereo Mix workaround
3. Test with `check_loopback_devices.py`
4. Implement multi-channel support if loopback works
