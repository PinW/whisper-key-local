import importlib.util
import tempfile
import unittest
from pathlib import Path
from unittest.mock import Mock, patch

from src.whisper_key.utils import setup_portaudio_path

setup_portaudio_path()

from src.whisper_key.config_manager import ConfigManager


def load_platform_audio(name):
    path = Path(__file__).parents[1] / 'src' / 'whisper_key' / 'platform' / name / 'audio_devices.py'
    spec = importlib.util.spec_from_file_location(f'{name}_audio_devices', path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


windows_audio = load_platform_audio('windows')
macos_audio = load_platform_audio('macos')


class DefaultAudioSourcesTests(unittest.TestCase):
    def test_windows_default_input_ignores_other_hosts(self):
        hosts = [
            {'name': 'MME', 'default_input_device': 1},
            {'name': 'Windows WASAPI', 'default_input_device': 5},
        ]
        self.assertEqual(windows_audio.resolve_default_device('default_input', [], hosts), 5)

    def test_windows_default_output_matches_endpoint_not_name(self):
        devices = [
            {'name': 'Speakers', 'hostapi': 0, 'max_input_channels': 0},
            {'name': 'Speakers [Loopback]', 'hostapi': 0, 'max_input_channels': 2},
            {'name': 'Speakers [Loopback]', 'hostapi': 0, 'max_input_channels': 2},
        ]
        hosts = [{'name': 'Windows WASAPI', 'default_input_device': -1, 'default_output_device': 0}]
        library = Mock()
        library.PaWasapi_IsLoopback.return_value = 1
        with patch.object(windows_audio.ctypes, 'CDLL', return_value=library):
            with patch.object(windows_audio, '_device_endpoint_id', side_effect=lambda library, index: ['A', 'B', 'A'][index]):
                self.assertEqual(windows_audio.resolve_default_device('default_output', devices, hosts), 2)

    def test_windows_missing_output_does_not_use_microphone(self):
        hosts = [{'name': 'Windows WASAPI', 'default_input_device': 0, 'default_output_device': -1}]
        self.assertEqual(windows_audio.resolve_default_device('default_output', [], hosts), -1)

    def test_windows_missing_loopback_does_not_use_other_endpoint(self):
        devices = [{'name': 'Speakers', 'hostapi': 0, 'max_input_channels': 0}]
        hosts = [{'name': 'Windows WASAPI', 'default_output_device': 0}]
        with patch.object(windows_audio.ctypes, 'CDLL', return_value=Mock()):
            with patch.object(windows_audio, '_device_endpoint_id', return_value='A'):
                self.assertEqual(windows_audio.resolve_default_device('default_output', devices, hosts), -1)

    def test_windows_default_notifications_distinguish_input_output_and_role(self):
        monitor = windows_audio.DeviceChangeMonitor.__new__(windows_audio.DeviceChangeMonitor)
        monitor.on_default_change = Mock()
        monitor._default_changed(None, 1, 1, 'input')
        monitor.on_default_change.assert_called_once_with('default_input')
        monitor.on_default_change.reset_mock()
        monitor._default_changed(None, 0, 1, None)
        monitor.on_default_change.assert_called_once_with('default_output')
        monitor.on_default_change.reset_mock()
        monitor._default_changed(None, 1, 2, 'communications')
        monitor._default_changed(None, 1, 0, 'console')
        monitor.on_default_change.assert_not_called()

    def test_macos_default_input_uses_core_audio_and_excludes_default_output(self):
        hosts = [{'name': 'Core Audio', 'default_input_device': 3}]
        self.assertEqual(macos_audio.resolve_default_device('default_input', [], hosts), 3)
        self.assertEqual(macos_audio.resolve_default_device('default_output', [], hosts), -1)
        self.assertEqual(macos_audio.DEFAULT_SOURCES, {'default_input': 'System default input'})

    def test_macos_listener_reports_default_input_changes(self):
        monitor = macos_audio.DeviceChangeMonitor.__new__(macos_audio.DeviceChangeMonitor)
        monitor.on_change = Mock()
        monitor.on_default_change = Mock()
        addresses = (macos_audio.PropertyAddress * 2)(
            macos_audio.PropertyAddress(int.from_bytes(b'dIn ', 'big'), 0, 0),
            macos_audio.PropertyAddress(int.from_bytes(b'dev#', 'big'), 0, 0),
        )
        monitor._changed(1, 2, addresses, None)
        monitor.on_default_change.assert_called_once_with('default_input')
        monitor.on_change.assert_called_once_with()


class AudioSourceConfigTests(unittest.TestCase):
    def setUp(self):
        directory = tempfile.TemporaryDirectory()
        self.addCleanup(directory.cleanup)
        self.settings_path = Path(directory.name) / 'user_settings.yaml'
        directory_patch = patch('src.whisper_key.config_manager.get_user_app_data_path', return_value=directory.name)
        directory_patch.start()
        self.addCleanup(directory_patch.stop)

    def test_fresh_config_uses_default_input(self):
        config = ConfigManager()
        audio = config.get_audio_config()
        self.assertEqual(audio['source'], 'default_input')
        self.assertIsNone(audio['input_device'])
        self.assertIsNone(audio['host'])

    def test_existing_named_selection_remains_pinned(self):
        self.settings_path.write_text('audio:\n  host: Windows WASAPI\n  input_device: Yeti\n', encoding='utf-8')
        self.assertEqual(ConfigManager().get_audio_config()['source'], 'device')

    def test_explicit_default_mode_takes_precedence_over_saved_device(self):
        self.settings_path.write_text(
            'audio:\n  source: default_input\n  host: MME\n  input_device: Yeti\n', encoding='utf-8'
        )
        self.assertEqual(ConfigManager().get_audio_config()['source'], 'default_input')

    def test_source_modes_persist_without_saving_resolved_name(self):
        config = ConfigManager()
        config.update_audio_source('default_output', None, None)
        audio = ConfigManager().get_audio_config()
        self.assertEqual(audio['source'], 'default_output')
        self.assertIsNone(audio['input_device'])
        config.update_audio_source('device', 'Windows WASAPI', 'Yeti')
        audio = ConfigManager().get_audio_config()
        self.assertEqual((audio['source'], audio['host'], audio['input_device']), ('device', 'Windows WASAPI', 'Yeti'))
        config.update_audio_source('default_input', None, None)
        audio = ConfigManager().get_audio_config()
        self.assertEqual((audio['source'], audio['host'], audio['input_device']), ('default_input', None, None))


if __name__ == '__main__':
    unittest.main()
