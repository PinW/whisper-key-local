# WASAPI Resampling Implementation Plan

As a *user* I want **WASAPI audio recording to work with custom PortAudio DLLs** so I can use loopback devices for system audio capture

## Current State Analysis

- WASAPI devices work at native sample rate (48000 Hz) with custom PortAudio DLL
- sounddevice's `WasapiSettings(auto_convert=True)` fails with custom DLL due to struct incompatibility
- Whisper requires 16000 Hz audio
- VAD (Voice Activity Detection) also expects 16000 Hz with 256-sample chunks
- Non-WASAPI devices (MME, DirectSound) work fine at 16000 Hz

## Implementation Plan

### Phase 1: Add Resampling Utility
- [ ] Add scipy to dependencies in pyproject.toml
- [ ] Create `_resample_audio()` method in AudioRecorder
  - Use `scipy.signal.resample_poly` for efficient integer-ratio resampling (48000→16000 = 3:1)
  - Handle edge cases (empty audio, already correct rate)

### Phase 2: Store Device Native Sample Rate
- [ ] Update `_resolve_hostapi()` to also store device's native sample rate
- [ ] Add `self.device_sample_rate` to track the recording sample rate
- [ ] Add `self.needs_resampling` flag for WASAPI devices

### Phase 3: Modify Recording Logic for WASAPI
- [ ] Update `_record_audio()` to use device native sample rate for WASAPI
- [ ] Remove WasapiSettings usage (incompatible with custom DLL)
- [ ] Adjust blocksize calculation for different sample rates (to keep VAD working)
- [ ] Resample VAD chunks in real-time before passing to VAD processor

### Phase 4: Resample Final Audio
- [ ] Update `_process_audio_data()` to resample if needed
- [ ] Ensure `get_audio_duration()` uses correct sample rate
- [ ] Update logging to show both recording rate and output rate

## Implementation Details

### Resampling Function
```python
from scipy.signal import resample_poly

def _resample_audio(self, audio: np.ndarray, orig_rate: int, target_rate: int) -> np.ndarray:
    if orig_rate == target_rate:
        return audio

    # Find GCD for efficient resampling ratio
    from math import gcd
    g = gcd(orig_rate, target_rate)
    up = target_rate // g    # e.g., 1 for 48000→16000
    down = orig_rate // g    # e.g., 3 for 48000→16000

    return resample_poly(audio.flatten(), up, down).astype(np.float32)
```

### Recording Sample Rate Logic
```python
def _get_recording_sample_rate(self) -> int:
    is_wasapi = self.device_hostapi and 'wasapi' in self.device_hostapi.lower()
    if is_wasapi:
        # Use device native rate, resample later
        device_id = self.get_device_id()
        device_info = sd.query_devices(device_id)
        return int(device_info['default_samplerate'])
    else:
        # Non-WASAPI can record at Whisper rate directly
        return self.WHISPER_SAMPLE_RATE
```

### VAD Chunk Handling for Different Sample Rates
```python
# When recording at 48000 Hz but VAD expects 16000 Hz chunks of 256 samples:
# - Record with blocksize = VAD_CHUNK_SIZE * (recording_rate / 16000)
# - e.g., 256 * 3 = 768 samples at 48000 Hz
# - Resample each chunk to 256 samples at 16000 Hz before VAD
```

## Files to Modify

1. **pyproject.toml** - Add scipy dependency
2. **src/whisper_key/audio_recorder.py** - Main changes:
   - Add `_resample_audio()` method
   - Add `device_sample_rate` and `needs_resampling` attributes
   - Update `_record_audio()` for WASAPI sample rate handling
   - Update `_process_audio_data()` to resample final audio
   - Update VAD chunk processing for different sample rates

## Success Criteria

- [ ] WASAPI devices record without errors using custom PortAudio DLL
- [ ] Audio is correctly resampled from 48000 Hz to 16000 Hz
- [ ] Whisper transcription works correctly with resampled audio
- [ ] VAD continues to function during recording (real-time chunk resampling)
- [ ] Non-WASAPI devices (MME, DirectSound) continue working unchanged
- [ ] No regression in existing functionality

## Design Decisions

1. **scipy for resampling**: Using `resample_poly` for quality and efficiency with integer ratios
2. **Real-time VAD resampling**: Keep VAD functional by resampling chunks during recording rather than disabling VAD for WASAPI
3. **Conditional logic**: Only use resampling path for WASAPI devices to avoid unnecessary processing for other host APIs
4. **Remove WasapiSettings**: Since the struct is incompatible with custom DLLs, remove it entirely rather than trying to monkey-patch
