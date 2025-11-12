# Audio Source Selection Implementation Plan

As a *user*, I want to **select audio source** so I can transcribe from different microphones or system audio ([#12](https://github.com/PinW/whisper-key-local/issues/12))

## Current State Analysis

### Audio Recording (audio_recorder.py)
- AudioRecorder uses sounddevice to capture audio from microphone
- Currently uses system default input device (no device parameter specified)
- `sd.InputStream()` called at line 137 without device parameter
- `_test_microphone()` at line 58 queries default device: `sd.query_devices(kind='input')`
- Sample rate fixed at 16000 Hz (WHISPER_SAMPLE_RATE)
- Supports mono and stereo recording via channels parameter

### System Tray (system_tray.py)
- Menu structure at line 121-138 in `_create_menu()`
- Current top-level items: Auto-paste toggle, Model submenu, Show Console, Exit
- Model submenu pattern: Uses pystray.Menu with radio buttons and checked callbacks
- Menu rebuilds dynamically via `self.icon.menu = self._create_menu()` pattern
- State manager provides callbacks for menu actions

### State Manager (state_manager.py)
- Coordinates all components including audio_recorder, whisper_engine, system_tray
- Provides callback methods for system tray menu actions (e.g., `_select_model`, `update_transcription_mode`)
- AudioRecorder initialized in main.py and passed to StateManager
- No current method for changing audio device at runtime

### Device Enumeration (sounddevice)
- `sd.query_devices()` returns all available audio devices across all host APIs
- Each device appears 2-4 times (MME, DirectSound, WASAPI, WDM-KS on Windows)
- Device info includes: name, hostapi, max_input_channels, max_output_channels, sample_rate
- System default identified by `sd.default.device[0]` for input
- Device selection via `sd.InputStream(device=<id>)` where id can be int or string

### Host API Behavior
- Windows provides 4 audio APIs: MME (default), DirectSound, WASAPI, WDM-KS
- Same physical device appears multiple times (one per API)
- App currently uses MME (system default) successfully
- Latency differences irrelevant for whisper-key's workflow
- **Decision**: Show all devices from all APIs (no filtering) for maximum compatibility

## Implementation Plan

### Phase 1: AudioRecorder Device Support
- [ ] Add `device` parameter to AudioRecorder.__init__() with default None
  - [ ] Store as instance variable: `self.device = device`
  - [ ] Pass through to existing initialization flow
- [ ] Update `_test_microphone()` to test selected device instead of just default
  - [ ] If `self.device` is not None, query specific device
  - [ ] Log selected device name
  - [ ] Validate device settings with `sd.check_input_settings()`
- [ ] Update `_record_audio()` to use selected device
  - [ ] Pass `device=self.device` to `sd.InputStream()` at line 137
- [ ] Add static method `get_available_input_devices()` to enumerate devices
  - [ ] Return list of dicts with device info: id, name, channels, sample_rate, hostapi
  - [ ] Include both input and output devices (output devices can be system audio sources)
  - [ ] Filter to devices with `max_input_channels > 0 OR max_output_channels > 0`
  - [ ] Keep devices from all host APIs (no filtering)
- [ ] Add static method `get_default_device_id()` to identify system default
  - [ ] Return `sd.default.device[0]`

### Phase 2: StateManager Device Management
- [ ] Add `current_audio_device_id` instance variable to track selected device
  - [ ] Initialize to None (system default)
  - [ ] Thread-safe access via `_state_lock` if needed
- [ ] Add `request_audio_device_change(device_id: int)` method
  - [ ] Check if device_id is same as current (no-op if match)
  - [ ] If recording in progress, cancel recording and proceed with change
  - [ ] If processing, defer until processing completes (similar to model change pattern)
  - [ ] If idle, execute change immediately
  - [ ] Return bool indicating success
- [ ] Add `_execute_audio_device_change(device_id: int)` method
  - [ ] Stop audio_recorder if running
  - [ ] Create new AudioRecorder instance with new device parameter
  - [ ] Preserve all other AudioRecorder configuration (channels, max_duration, callbacks)
  - [ ] Update `self.audio_recorder` reference
  - [ ] Update `self.current_audio_device_id`
  - [ ] Log device change
  - [ ] Handle errors gracefully (restore previous device on failure)
- [ ] Add `get_available_audio_devices()` method
  - [ ] Call `AudioRecorder.get_available_input_devices()`
  - [ ] Return device list for system tray menu construction
- [ ] Add `get_current_audio_device_id()` method
  - [ ] Return `self.current_audio_device_id` (None = system default)

### Phase 3: System Tray Menu Integration
- [ ] Update `_create_menu()` to add Audio Source submenu at top
  - [ ] Create audio device submenu items list
  - [ ] Query available devices from state_manager
  - [ ] Build menu items with device names
  - [ ] Add radio button behavior (one selected at a time)
  - [ ] Mark current device as checked
  - [ ] Add separator after device list
  - [ ] Show device count in menu label: "Audio Source (N devices)"
- [ ] Handle device name display formatting
  - [ ] Truncate long device names (max 50 chars)
  - [ ] Show host API in parentheses: "Microphone (WASAPI)"
  - [ ] Mark system default: "Microphone (MME) ⭐ Default"
- [ ] Add `_select_audio_device(device_id: int)` callback method
  - [ ] Call `state_manager.request_audio_device_change(device_id)`
  - [ ] Rebuild menu on success: `self.icon.menu = self._create_menu()`
  - [ ] Log error on failure
- [ ] Handle device enumeration errors
  - [ ] If device list query fails, show "Audio Source (unavailable)" menu item
  - [ ] Log error and continue with system default

### Phase 4: Error Handling & Edge Cases
- [ ] Handle device disconnection during recording
  - [ ] AudioRecorder logs error in audio callback (line 150)
  - [ ] System automatically falls back to recording failure handling
  - [ ] No special handling needed (existing error flow sufficient)
- [ ] Handle invalid device ID selection
  - [ ] Validate device ID exists before passing to AudioRecorder
  - [ ] Fall back to system default on validation failure
  - [ ] Log warning to user
- [ ] Handle device enumeration failure
  - [ ] Wrap `sd.query_devices()` in try-except
  - [ ] Return empty list on failure
  - [ ] System tray shows unavailable state
- [ ] Handle incompatible device settings
  - [ ] `sd.check_input_settings()` validates 16000 Hz, 1 channel, float32
  - [ ] Log warning if device doesn't support required settings
  - [ ] Allow selection anyway (sounddevice may auto-resample)

### Phase 5: Testing & Validation
- [ ] Manual testing with multiple devices
  - [ ] Test with system default (None)
  - [ ] Test with explicit device ID selection
  - [ ] Test with USB microphone
  - [ ] Test device switching while recording (should cancel and switch)
  - [ ] Test device switching while processing (should defer)
  - [ ] Test with disconnected device (should handle gracefully)
- [ ] Test menu behavior
  - [ ] Verify all devices appear in menu
  - [ ] Verify current device marked correctly
  - [ ] Verify device selection changes radio button state
  - [ ] Verify menu rebuilds after device change
- [ ] Test across host APIs
  - [ ] Verify same device appears multiple times (MME, WASAPI, etc.)
  - [ ] Verify all instances are selectable
  - [ ] Verify audio recording works with each API

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
                 device = None):  # NEW PARAMETER

        # ... existing initialization ...
        self.device = device  # Store device selection

        self._test_microphone()

    def _test_microphone(self):
        try:
            if self.device is not None:
                # Test specific device
                device_info = sd.query_devices(self.device, kind='input')
                self.logger.info(f"Selected microphone: {device_info['name']}")

                # Validate device settings
                sd.check_input_settings(
                    device=self.device,
                    channels=self.channels,
                    samplerate=self.sample_rate,
                    dtype=self.STREAM_DTYPE
                )
            else:
                # Test system default
                default_input = sd.query_devices(kind='input')
                self.logger.info(f"Default microphone: {default_input['name']}")
        except Exception as e:
            self.logger.error(f"Microphone test failed: {e}")
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
    def get_available_input_devices():
        """Returns list of available audio devices"""
        devices = []
        all_devices = sd.query_devices()

        for idx, device in enumerate(all_devices):
            # Include devices with input OR output channels
            # (output devices can be system audio sources like Stereo Mix)
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

    @staticmethod
    def get_default_device_id():
        """Returns system default input device ID"""
        return sd.default.device[0]
```

### StateManager Device Management

```python
# state_manager.py

class StateManager:
    def __init__(self, ...):
        # ... existing initialization ...
        self.current_audio_device_id = None  # None = system default
        self._pending_device_change = None  # Store pending device change

    def get_available_audio_devices(self):
        """Get list of available audio devices for menu construction"""
        try:
            return AudioRecorder.get_available_input_devices()
        except Exception as e:
            self.logger.error(f"Failed to enumerate audio devices: {e}")
            return []

    def get_current_audio_device_id(self):
        """Get currently selected device ID (None = system default)"""
        return self.current_audio_device_id

    def request_audio_device_change(self, device_id: int):
        """Request to change audio input device"""
        current_state = self.get_current_state()

        # No-op if already using this device
        if device_id == self.current_audio_device_id:
            return True

        # Cancel recording if in progress
        if current_state == "recording":
            print(f"🎤 Cancelling recording to switch audio device...")
            self.cancel_active_recording()
            self._execute_audio_device_change(device_id)
            return True

        # Defer if processing
        if current_state == "processing":
            print(f"⏳ Queueing audio device change until transcription completes...")
            self._pending_device_change = device_id
            return True

        # Execute immediately if idle
        if current_state == "idle":
            self._execute_audio_device_change(device_id)
            return True

        self.logger.warning(f"Unexpected state for device change: {current_state}")
        return False

    def _execute_audio_device_change(self, device_id: int):
        """Execute audio device change"""
        try:
            # Get device info for logging
            try:
                device_info = sd.query_devices(device_id)
                device_name = device_info['name']
            except:
                device_name = f"Device {device_id}"

            print(f"🎤 Switching to: {device_name}")

            # Stop current recorder if active
            if self.audio_recorder.get_recording_status():
                self.audio_recorder.cancel_recording()

            # Get current recorder configuration
            channels = self.audio_recorder.channels
            dtype = self.audio_recorder.dtype
            max_duration = self.audio_recorder.max_duration
            on_max_duration = self.audio_recorder.on_max_duration_reached
            vad_manager = self.audio_recorder.vad_manager

            # Create new AudioRecorder with new device
            new_recorder = AudioRecorder(
                on_vad_event=self.handle_vad_event,
                channels=channels,
                dtype=dtype,
                max_duration=max_duration,
                on_max_duration_reached=on_max_duration,
                vad_manager=vad_manager,
                device=device_id if device_id != -1 else None  # -1 = system default
            )

            # Replace audio recorder
            old_recorder = self.audio_recorder
            self.audio_recorder = new_recorder
            self.current_audio_device_id = device_id

            print(f"✅ Successfully switched to: {device_name}")

        except Exception as e:
            self.logger.error(f"Failed to change audio device: {e}")
            print(f"❌ Failed to change audio device: {e}")
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

        # Get audio device info
        available_devices = self.state_manager.get_available_audio_devices()
        current_device_id = self.state_manager.get_current_audio_device_id()
        default_device_id = AudioRecorder.get_default_device_id()

        # Build audio source submenu
        audio_device_items = []

        # Add system default option
        def is_system_default_selected():
            return current_device_id is None or current_device_id == -1

        audio_device_items.append(
            pystray.MenuItem(
                "System Default",
                lambda icon, item: self._select_audio_device(-1),
                radio=True,
                checked=lambda item: is_system_default_selected()
            )
        )

        if available_devices:
            audio_device_items.append(pystray.Menu.SEPARATOR)

            for device in available_devices:
                device_id = device['id']
                device_name = device['name']
                hostapi = device['hostapi']

                # Truncate long names
                if len(device_name) > 50:
                    device_name = device_name[:47] + "..."

                # Format display name with host API
                # Extract API name (e.g., "Windows WASAPI" -> "WASAPI")
                api_short = hostapi.split()[-1] if ' ' in hostapi else hostapi
                display_name = f"{device_name} ({api_short})"

                # Mark system default
                if device_id == default_device_id:
                    display_name += " ⭐"

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

        # Get other menu state
        auto_paste_enabled = self.config_manager.get_setting('clipboard', 'auto_paste')
        current_model = self.config_manager.get_setting('whisper', 'model_size')

        # ... existing model submenu code ...

        # Build main menu with Audio Source at top
        device_count = len(available_devices) if available_devices else 0
        menu_items = [
            pystray.MenuItem(
                f"Audio Source ({device_count + 1} devices)",
                pystray.Menu(*audio_device_items)
            ),
            pystray.Menu.SEPARATOR,
            pystray.MenuItem("Auto-paste", lambda icon, item: self._set_transcription_mode(True), radio=True, checked=lambda item: auto_paste_enabled),
            pystray.MenuItem("Copy to clipboard", lambda icon, item: self._set_transcription_mode(False), radio=True, checked=lambda item: not auto_paste_enabled),
            pystray.Menu.SEPARATOR,
            pystray.MenuItem(f"Model: {current_model.title()}", pystray.Menu(*model_sub_menu_items)),
        ]

        # ... rest of menu items (console, exit) ...

        return pystray.Menu(*menu_items)

    except Exception as e:
        self.logger.error(f"Error in _create_menu: {e}")
        raise

def _select_audio_device(self, device_id: int):
    """Callback for audio device selection from system tray"""
    try:
        success = self.state_manager.request_audio_device_change(device_id)

        if success:
            self.icon.menu = self._create_menu()
        else:
            self.logger.warning(f"Request to change audio device to {device_id} was not accepted")

    except Exception as e:
        self.logger.error(f"Error selecting audio device {device_id}: {e}")
```

### Device Change During Recording

The implementation handles device changes during recording by:
1. Cancelling active recording
2. Discarding audio buffer
3. Creating new AudioRecorder with new device
4. Ready for new recording

This is the simplest and safest approach - no partial recordings, no state corruption.

### System Default Device Handling

- `device_id = -1` represents "System Default" in menu
- Internally stored as `None` in AudioRecorder (sounddevice convention)
- System default identified by `sd.default.device[0]`
- Marked with ⭐ in device list for easy identification

## Files to Modify

1. **`src/whisper_key/audio_recorder.py`**
   - Add `device` parameter to `__init__()`
   - Update `_test_microphone()` to validate selected device
   - Update `_record_audio()` to pass device to InputStream
   - Add `get_available_input_devices()` static method
   - Add `get_default_device_id()` static method

2. **`src/whisper_key/state_manager.py`**
   - Add `current_audio_device_id` instance variable
   - Add `_pending_device_change` instance variable
   - Add `get_available_audio_devices()` method
   - Add `get_current_audio_device_id()` method
   - Add `request_audio_device_change()` method
   - Add `_execute_audio_device_change()` method
   - Update `_transcription_pipeline()` to handle pending device changes

3. **`src/whisper_key/system_tray.py`**
   - Update `_create_menu()` to add Audio Source submenu at top
   - Add `_select_audio_device()` callback method
   - Handle device name formatting and truncation
   - Add import for AudioRecorder (for get_default_device_id)

4. **`src/whisper_key/main.py`**
   - No changes needed (AudioRecorder initialized with default device=None)

## Success Criteria

- [ ] System tray shows "Audio Source" menu at the top with device count
- [ ] Audio Source menu expands to show all available devices (all host APIs)
- [ ] Each device shows name and host API in format: "Device Name (API)"
- [ ] System default device marked with ⭐
- [ ] "System Default" option at top of device list
- [ ] Currently selected device shows radio button checked
- [ ] Selecting different device switches audio input
- [ ] Device selection works during idle state
- [ ] Device selection cancels active recording and switches
- [ ] Device selection defers during processing and executes after
- [ ] Audio recording works with selected device
- [ ] Invalid device selection handled gracefully (falls back to default)
- [ ] Device disconnection during recording handled gracefully (existing error flow)
- [ ] Device enumeration errors handled gracefully (menu shows unavailable)
- [ ] No persistent device selection (resets to system default on app restart)
- [ ] Menu shows same physical device multiple times (different host APIs)
- [ ] All device instances are selectable and functional
