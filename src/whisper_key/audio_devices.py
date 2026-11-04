import logging
import platform
import threading
import time

import sounddevice as sd

from .platform import audio_devices as platform_audio_devices
from .terminal_ui import print_error


class AudioDeviceManager:
    def __init__(self, host_name, device_name, on_selection_changed, on_source_status_changed):
        self.devices = []
        self.hosts = []
        self.selected_host = host_name
        self.selected_name = device_name
        self.device_id = -1
        self.selection_pending = False
        self._on_selection_changed = on_selection_changed
        self._on_source_status_changed = on_source_status_changed
        self._last_warning = None
        self._refresh_requested = threading.Event()
        self._refresh_deadline = None
        self._next_poll_at = None
        self._polling = False
        self._monitor = None
        self._started = False
        self._stopped = False
        self.logger = logging.getLogger(__name__)
        self.load()
        self._initialize_selection()
        self.device_id = self.resolve(self.selected_name, self.selected_host, report=False)

    def print_startup_status(self):
        if self.device_id >= 0:
            print(f'   ✓ Audio source {self._format_audio_source(self.selected_name, self.selected_host)}')

    def print_startup_warning(self):
        if self.device_id < 0:
            message = self._last_warning or 'Audio source unavailable; select a source in the tray.'
            print_error(message)

    def load(self):
        devices = list(sd.query_devices())
        hosts = list(sd.query_hostapis())
        self.devices = devices
        self.hosts = hosts

    def refresh(self):
        self.devices = []
        self.hosts = []
        if sd._initialized:
            sd._terminate()
        sd._initialize()
        self.load()

    def start(self):
        if self._started:
            return
        self._stopped = False
        self._started = True
        self._polling = False
        try:
            self._monitor = platform_audio_devices.DeviceChangeMonitor(self.request_refresh)
            self._monitor.start()
        except Exception as error:
            self.logger.warning(f"Audio device notifications unavailable; checking periodically: {error}")
            self._polling = True
        self.request_refresh()

    def stop(self):
        self._stopped = True
        self._refresh_requested.clear()
        self._refresh_deadline = None
        self._next_poll_at = None
        if self._monitor:
            try:
                self._monitor.stop()
            except Exception as error:
                self.logger.warning(f"Could not stop audio device notifications: {error}")
                return
            self._monitor = None
        self._started = False

    def request_refresh(self):
        if not self._stopped:
            self._refresh_requested.set()

    @property
    def refresh_pending(self):
        return self._refresh_requested.is_set() or self._refresh_deadline is not None

    def observe_changes(self):
        if self._refresh_requested.is_set():
            self._refresh_requested.clear()
            self._refresh_deadline = time.monotonic() + 0.5

    def update(self, allow_refresh=True):
        if self._stopped:
            return False
        self.observe_changes()
        now = time.monotonic()
        refresh_due = (
            self._refresh_deadline is not None and now >= self._refresh_deadline
        ) or (
            self._refresh_deadline is None and self._next_poll_at is not None and now >= self._next_poll_at
        )
        try:
            if refresh_due and allow_refresh:
                self.refresh()
                self._initialize_selection()
                self.device_id = self.resolve(self.selected_name, self.selected_host)
                self._refresh_deadline = None
                self._next_poll_at = now + 5.0 if self._polling else None
                return True
            if not self.refresh_pending and self.selection_pending:
                self.device_id = self.resolve(self.selected_name, self.selected_host)
                return True
        except Exception as error:
            self.change_failed(error)
            return True
        return False

    def ready_to_record(self):
        if self.refresh_pending:
            print('🎤 Audio devices are updating; try recording again in a moment.')
            return False
        return not self._stopped

    def selection_applied(self):
        if self.refresh_pending:
            return
        if self.selection_pending and self.device_id >= 0:
            device = self.devices[self.device_id]
            host_name = self.hosts[device['hostapi']]['name']
            message = f"Successfully switched audio device to: {self._format_audio_source(device['name'], host_name)}"
            self.logger.info(message)
            print(f'✅ {message}')
        self.selection_pending = False

    def change_failed(self, error):
        self.device_id = -1
        self._refresh_deadline = time.monotonic() + 5.0
        self._next_poll_at = None
        self.logger.warning(f"Could not update audio source; retrying automatically: {error}")
        if self.selection_pending:
            print(f'❌ Failed to switch audio device: {error}')

    def _initialize_selection(self):
        host_name = self.canonical_host(self.selected_host)
        if not host_name:
            preferred_host = 'Windows WASAPI' if platform.system() == 'Windows' else 'Core Audio'
            host_names = [host['name'] for host in self.available_hosts()]
            host_name = preferred_host if preferred_host in host_names else next(iter(host_names), None)
        device_name = self.selected_name
        if device_name is None:
            devices = self.input_devices(host_name)
            if devices:
                device_name = devices[0]['name']
        if (host_name, device_name) != (self.selected_host, self.selected_name):
            self._on_selection_changed(host_name, device_name)
            self.selected_host = host_name
            self.selected_name = device_name

    def select_host(self, host_name):
        if self._stopped:
            return False
        host_name = self.canonical_host(host_name)
        if host_name == self.selected_host:
            return True
        devices = self.input_devices(host_name)
        if not devices:
            return False
        return self.select_device(devices[0]['name'], host_name)

    def select_device(self, device_name, host_name):
        if self._stopped:
            return False
        host_name = self.canonical_host(host_name)
        matches = [device for device in self.input_devices(host_name) if device['name'] == device_name]
        if len(matches) != 1:
            self.logger.warning(f"Cannot select unavailable or ambiguous audio source {self._format_audio_source(device_name, host_name)}")
            return False
        if (host_name, device_name) == (self.selected_host, self.selected_name) and matches[0]['id'] == self.device_id:
            return True
        self._on_selection_changed(host_name, device_name)
        self.selected_host = host_name
        self.selected_name = device_name
        self.selection_pending = True
        return True

    def available_hosts(self):
        return [
            {'name': host['name'], 'index': index}
            for index, host in enumerate(self.hosts)
            if any(device['hostapi'] == index and device['max_input_channels'] > 0 for device in self.devices)
        ]

    def canonical_host(self, host_name):
        if not host_name:
            return None
        return next((host['name'] for host in self.hosts if host['name'].casefold() == host_name.casefold()), host_name)

    def input_devices(self, host_name=None):
        host_name = self.canonical_host(host_name if host_name is not None else self.selected_host)
        return [
            {
                'id': index,
                'name': device['name'],
                'hostapi': self.hosts[device['hostapi']]['name'],
            }
            for index, device in enumerate(self.devices)
            if device['max_input_channels'] > 0
            and self.hosts[device['hostapi']]['name'] == host_name
        ]

    def resolve(self, device_name, host_name, *, report=True):
        if isinstance(device_name, (int, float)):
            return -1
        matches = [
            device['id'] for device in self.input_devices(host_name)
            if device['name'] == device_name
        ]
        if len(matches) == 1:
            if self._last_warning:
                message = f"Audio source reconnected: {self._format_audio_source(device_name, host_name)}."
                self.logger.info(message, extra={'console_handled': True})
                print(f'\n✅ {message}')
                self._on_source_status_changed()
            self._last_warning = None
            return matches[0]
        if len(matches) > 1:
            warning = f"Multiple audio sources match {self._format_audio_source(device_name, host_name)}; select another source."
        else:
            warning = f"{self._format_audio_source(device_name, host_name, bracket_device=False)} is unavailable; reconnect it or select another source."
        self._warn(warning, report=report)
        return -1

    def _format_audio_source(self, device_name, host_name, *, bracket_device=True):
        host_name = self.canonical_host(host_name)
        display_host = 'WASAPI' if host_name == 'Windows WASAPI' else host_name
        display_device = f'[{device_name}]' if bracket_device else device_name
        return f'{display_device} [{display_host}]'

    def _warn(self, message, *, report=True):
        if message and message != self._last_warning:
            self.logger.warning(message, extra={'console_handled': True})
            if report:
                print_error(message)
                self._on_source_status_changed()
        self._last_warning = message
