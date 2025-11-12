# Audio Source Selection Implementation Plan

As a *user*, I want to **select audio source** so I can transcribe from different microphones or system audio ([#12](https://github.com/PinW/whisper-key-local/issues/12))

## Current State Analysis

- AudioRecorder uses system default device (no device parameter)
- System tray has model submenu with radio buttons - same pattern works for devices
- StateManager coordinates components but can't change device at runtime
- `sd.query_devices()` enumerates devices, `sd.InputStream(device=<id>)` selects one
- Windows shows same device 2-4x (MME, WASAPI, etc.) - filter to default host API only

## Implementation Plan

### Phase 1: AudioRecorder Device Support
- [ ] Add `device` parameter to AudioRecorder.__init__() with default None
  - [ ] Call `self.resolve_device(device)` to process device parameter
  - [ ] Replace `self._test_microphone()` call with `self._test_audio_source()`
- [ ] Rename `_test_microphone()` to `_test_audio_source()`
- [ ] Update `_record_audio()` to use selected device
  - [ ] Pass `device=self.device` to `sd.InputStream()` at line 137
- [ ] Add static method `get_available_input_devices()` to enumerate devices

### Phase 2: StateManager Device Management
- [ ] Add `_pending_device_change` instance variable
- [ ] Add `get_available_audio_devices()` method (calls AudioRecorder static method)
- [ ] Add `get_current_audio_device_id()` method (returns audio_recorder.device)
- [ ] Add `request_audio_device_change(device_id)` method (state-aware: cancel/defer/execute)
- [ ] Add `_execute_audio_device_change(device_id)` method (recreates AudioRecorder)
- [ ] Update `_transcription_pipeline()` to handle pending device changes

### Phase 3: System Tray Menu Integration
- [ ] Update `_create_menu()` to add Audio Source submenu at top
- [ ] Add `_select_audio_device(device_id)` callback (saves to config AND calls StateManager)

### Phase 4: Config Persistence
- [ ] Update `config.defaults.yaml` to add `input_device: "default"` to audio section
- [ ] Update main.py to read `audio.input_device` and pass to AudioRecorder
- [ ] SystemTray `_select_audio_device()` saves to config after successful change

## Implementation Details

### AudioRecorder Device Support

```python
# audio_recorder.py

class AudioRecorder:
    def __init__(self,
                 on_vad_event: Callable[[VadEvent], None],
                 channels: int = 1,
                 dtype: str = "float32",
                 max_duration: int = 30,
                 on_max_duration_reached: callable = None,
                 vad_manager = None,
                 device = None):

        # ... existing initialization ...

        self.resolve_device(device)
        self._test_audio_source()

    def resolve_device(self, device):
        if device == "default" or device is None:
            self.device = None  # Use system default
        elif isinstance(device, int):
            self.device = device
        else:
            self.logger.warning(f"Invalid device parameter: {device}, using default")
            self.device = None

    def _test_audio_source(self):
        try:
            if self.device is not None:
                device_info = sd.query_devices(self.device, kind='input')
                self.logger.info(f"Selected source: {device_info['name']}")

                sd.check_input_settings(
                    device=self.device,
                    channels=self.channels,
                    samplerate=self.sample_rate,
                    dtype=self.STREAM_DTYPE
                )
            else:
                default_input = sd.query_devices(kind='input')
                self.logger.info(f"Default source: {default_input['name']}")
        except Exception as e:
            self.logger.error(f"Audio source test failed: {e}")
            raise

    def _record_audio(self):
        try:
            def audio_callback(audio_data, frames, _time, status):
                # ... existing callback code ...

            blocksize = VAD_CHUNK_SIZE if self.continuous_vad else None

            with sd.InputStream(samplerate=self.sample_rate,
                                channels=self.channels,
                                callback=audio_callback,
                                dtype=self.STREAM_DTYPE,
                                blocksize=blocksize,
                                device=self.device):  # NEW PARAMETER

                # ... existing recording loop ...

    @staticmethod
    def get_available_audio_devices():
        devices = []
        all_devices = sd.query_devices()

        default_device = sd.query_devices(kind='input')
        default_hostapi = default_device['hostapi']

        for idx, device in enumerate(all_devices):
            if device['hostapi'] != default_hostapi:
                continue

            # Include devices with input OR output channels
            if device['max_input_channels'] > 0 or device['max_output_channels'] > 0:
                hostapi_name = sd.query_hostapis(device['hostapi'])['name']

                devices.append({
                    'id': idx,
                    'name': device['name'],
                    'input_channels': device['max_input_channels'],
                    'output_channels': device['max_output_channels'],
                    'sample_rate': device['default_samplerate'],
                    'hostapi': hostapi_name
                })

        return devices
```

### Configuration Schema

```yaml
# config.defaults.yaml

audio:
  # Audio input device selection
  # "default" = Use system default microphone (default behavior)
  # <device_id> = Specific device ID number (set automatically when changed via system tray)
  #
  # Note: Device IDs are assigned by the operating system and may change if devices
  # are plugged/unplugged. Use system tray to select device - it will save the ID here.
  input_device: "default"
```

### StateManager Device Management

```python
# state_manager.py

class StateManager:
    def __init__(self, audio_recorder, ...):
        # ... existing initialization ...
        self.audio_recorder = audio_recorder
        self._pending_device_change = None

    def get_available_audio_devices(self):
        return AudioRecorder.get_available_audio_devices()

    def get_current_audio_device_id(self):
        return self.audio_recorder.device

    def request_audio_device_change(self, device_id: int):
        current_state = self.get_current_state()

        if device_id == self.audio_recorder.device:
            return True

        if current_state == "recording":
            print(f"🎤 Cancelling recording to switch audio device...")
            self.cancel_active_recording()
            self._execute_audio_device_change(device_id)
            return True

        if current_state == "processing":
            print(f"⏳ Queueing audio device change until transcription completes...")
            self._pending_device_change = device_id
            return True

        if current_state == "idle":
            self._execute_audio_device_change(device_id)
            return True

        self.logger.warning(f"Unexpected state for device change: {current_state}")
        return False

    def _execute_audio_device_change(self, device_id: int):
        try:
            # Get device info for logging
            try:
                device_info = sd.query_devices(device_id)
                device_name = device_info['name']
            except:
                device_name = f"Device {device_id}"

            print(f"🎤 Switching to: {device_name}")

            # Get current recorder configuration
            channels = self.audio_recorder.channels
            dtype = self.audio_recorder.dtype
            max_duration = self.audio_recorder.max_duration
            on_max_duration = self.audio_recorder.on_max_duration_reached
            vad_manager = self.audio_recorder.vad_manager

            new_recorder = AudioRecorder(
                on_vad_event=self.handle_vad_event,
                channels=channels,
                dtype=dtype,
                max_duration=max_duration,
                on_max_duration_reached=on_max_duration,
                vad_manager=vad_manager,
                device=device_id if device_id != -1 else None  # -1 = system default
            )

            self.audio_recorder = new_recorder

            print(f"✅ Successfully switched audio device to: {device_name}")

        except Exception as e:
            self.logger.error(f"❌ Failed to change audio device: {e}")
            # Keep existing audio_recorder on failure

    def _transcription_pipeline(self, audio_data, use_auto_enter: bool = False):
        try:
            # ... existing pipeline code ...

        finally:
            with self._state_lock:
                self.is_processing = False
                pending_model = self._pending_model_change
                pending_device = self._pending_device_change

            # Execute pending changes outside lock
            if pending_device:
                self.logger.info(f"Executing pending device change")
                self._execute_audio_device_change(pending_device)
                self._pending_device_change = None

            if pending_model:
                self.logger.info(f"Executing pending model change to: {pending_model}")
                self._execute_model_change(pending_model)
                self._pending_model_change = None

            if not (pending_device or pending_model):
                self.system_tray.update_state("idle")
```

### System Tray Menu Integration

```python
# system_tray.py

def _create_menu(self):
    try:
        app_state = self.state_manager.get_application_state()
        is_model_loading = app_state.get('model_loading', False)

        available_devices = self.state_manager.get_available_audio_devices()
        current_device_id = self.state_manager.get_current_audio_device_id()

        audio_device_items = []

        if available_devices:
            for device in available_devices:
                device_id = device['id']
                device_name = device['name']

                if len(device_name) > 32:
                    device_name = device_name[:29] + "..."

                def make_checker(dev_id):
                    return lambda item: self.state_manager.get_current_audio_device_id() == dev_id

                audio_device_items.append(
                    pystray.MenuItem(
                        display_name,
                        lambda icon, item, dev_id=device_id: self._select_audio_device(dev_id),
                        radio=True,
                        checked=make_checker(device_id)
                    )
                )

        # ... existing code ...

        menu_items = [
            pystray.MenuItem(
                f"Audio Source ({device_count} devices)",
                pystray.Menu(*audio_device_items)
            ),
            
        # ... existing code ...

def _select_audio_device(self, device_id: int):
    success = self.state_manager.request_audio_device_change(device_id)

    if success:
        self.config_manager.update_user_setting('audio', 'input_device', device_id)
        self.icon.menu = self._create_menu()
    else:
        self.logger.warning(f"Request to change audio device to {device_id} was not accepted")
```

### Main.py Initialization

```python
# main.py

def setup_audio_recorder(config_manager, vad_manager, ...):
    # Get audio config
    channels = config_manager.get_setting('audio', 'channels')
    dtype = config_manager.get_setting('audio', 'dtype')
    max_duration = config_manager.get_setting('audio', 'max_duration')
    input_device = config_manager.get_setting('audio', 'input_device')  # NEW

    # Create AudioRecorder
    audio_recorder = AudioRecorder(
        on_vad_event=on_vad_event,
        channels=channels,
        dtype=dtype,
        max_duration=max_duration,
        on_max_duration_reached=on_max_duration,
        vad_manager=vad_manager,
        device=input_device  # NEW: Pass "default" or device ID from config
    )

    return audio_recorder
```

## Files to Modify

1. `src/whisper_key/audio_recorder.py`
2. `src/whisper_key/state_manager.py`
3. `src/whisper_key/system_tray.py`
4. `src/whisper_key/main.py`
5. `src/whisper_key/config.defaults.yaml`

## Success Criteria

- [ ] System tray shows "Audio Source" menu at the top with device count
- [ ] Audio Source menu expands to show devices from default host API only
- [ ] Each device shows name (no duplicates per physical device)
- [ ] Currently selected device shows radio button checked
- [ ] Selecting different device switches audio input
- [ ] Audio recording works with selected device
- [ ] Device selection persisted to config ("default" or device ID number)
- [ ] Saved device loaded on app restart
