import threading
import unittest
from unittest.mock import Mock, patch

from src.whisper_key.utils import setup_portaudio_path

setup_portaudio_path()

from src.whisper_key.audio_devices import AudioDeviceManager
from src.whisper_key.audio_recorder import AudioRecorder
from src.whisper_key.config_manager import ConfigManager
from src.whisper_key.state_manager import StateManager
from src.whisper_key.system_tray import SystemTray
from src.whisper_key.terminal_ui import BOLD_RED, RESET


def input_device(name, host=1, rate=48000, channels=1):
    return {
        'name': name, 'hostapi': host, 'max_input_channels': channels,
        'default_samplerate': rate,
    }


class AudioDevicesTests(unittest.TestCase):
    def setUp(self):
        self.devices = [input_device('Yeti', 0), input_device('Yeti'), input_device('Webcam')]
        self.hosts = [
            {'name': 'MME', 'default_input_device': 0},
            {'name': 'Windows WASAPI', 'default_input_device': 2},
        ]
        patches = (
            patch('src.whisper_key.audio_devices.platform_audio_devices.DEFAULT_HOST', 'Windows WASAPI'),
            patch('src.whisper_key.audio_devices.platform_audio_devices.DEFAULT_SOURCES', {
                'default_input': 'System default input', 'default_output': 'System default output',
            }),
            patch('src.whisper_key.audio_devices.platform_audio_devices.resolve_default_device',
                  side_effect=lambda mode, devices, hosts: hosts[1]['default_input_device'] if mode == 'default_input' else -1),
            patch('src.whisper_key.audio_devices.sd.query_devices', side_effect=self.query_devices),
            patch('src.whisper_key.audio_devices.sd.query_hostapis', side_effect=self.query_hosts),
            patch('src.whisper_key.audio_devices.sd._initialized', 1),
            patch('src.whisper_key.audio_devices.sd._terminate'),
            patch('src.whisper_key.audio_devices.sd._initialize'),
        )
        self.audio_mocks = [item.start() for item in patches]
        for item in patches:
            self.addCleanup(item.stop)
        self.settings = {'source': 'device', 'host': 'Windows WASAPI', 'input_device': 'Yeti'}
        self.config = Mock()
        self.config.get_setting.side_effect = lambda section, key: self.settings[key]
        self.config.update_audio_source.side_effect = self.save_selection
        self.play_ready_sound = Mock()
        self.audio_devices = AudioDeviceManager(
            self.settings['host'], self.settings['input_device'], self.config.update_audio_source,
            self.play_ready_sound,
            source_mode=self.settings['source'],
        )
        self.recorder = AudioRecorder(on_vad_event=Mock(), vad_manager=Mock(is_available=lambda: False), device=1)
        self.manager = StateManager(
            audio_recorder=self.recorder, whisper_engine=Mock(), clipboard_manager=Mock(),
            config_manager=self.config, vad_manager=Mock(), text_postprocessor=Mock(), system_tray=Mock(),
            audio_devices=self.audio_devices,
        )

    def query_devices(self, index=None):
        return self.devices if index is None else self.devices[index]

    def query_hosts(self, index=None):
        return self.hosts if index is None else self.hosts[index]

    def save_selection(self, source, host, name):
        self.settings.update(source=source, host=host, input_device=name)

    def refresh(self):
        self.audio_devices.observe_changes()
        self.audio_devices._refresh_deadline = 0
        self.manager.refresh_audio_devices()

    def test_name_matches_only_selected_host_after_reordering(self):
        self.devices[1], self.devices[2] = self.devices[2], self.devices[1]
        self.refresh()
        self.assertEqual(self.recorder.device, 2)
        self.assertEqual(self.settings['input_device'], 'Yeti')

    def test_disconnection_stops_selection_and_reconnection_restores_preference(self):
        self.devices[1] = input_device('Other microphone')
        with self.assertLogs('src.whisper_key.audio_devices', level='WARNING'):
            self.refresh()
        self.assertEqual(self.recorder.device, -1)
        self.assertEqual(self.settings['input_device'], 'Yeti')
        self.devices.append(input_device('Yeti'))
        self.refresh()
        self.assertEqual(self.recorder.device, 3)
        self.config.update_audio_source.assert_not_called()

    def test_duplicate_names_never_choose_arbitrary_match(self):
        self.devices.append(input_device('Yeti'))
        with self.assertLogs('src.whisper_key.audio_devices', level='WARNING'):
            self.refresh()
        self.assertEqual(self.recorder.device, -1)
        self.assertFalse(self.recorder.start_recording())
        self.assertFalse(self.manager.request_audio_device_change('Yeti', 'Windows WASAPI'))

    def test_startup_missing_source_prints_error_once_and_logs_warning(self):
        with patch('builtins.print') as output:
            with self.assertLogs('src.whisper_key.audio_devices', level='WARNING') as logs:
                audio_devices = AudioDeviceManager('Windows WASAPI', 'Missing microphone', Mock(), self.play_ready_sound, 'device')
                output.assert_not_called()
                audio_devices.print_startup_status()
                output.assert_not_called()
                audio_devices.print_startup_warning()
                audio_devices.resolve('Missing microphone', 'Windows WASAPI')
        output.assert_called_once_with(
            f'\n{BOLD_RED}❌ Missing microphone [WASAPI] is unavailable; reconnect it or select another source.{RESET}',
            flush=True,
        )
        self.assertEqual(len(logs.records), 1)
        self.assertTrue(logs.records[0].console_handled)
        self.play_ready_sound.assert_not_called()

    def test_disconnect_and_reconnect_play_ready_sound_once_each(self):
        self.play_ready_sound.assert_not_called()
        self.devices[1] = input_device('Other microphone')
        with self.assertLogs('src.whisper_key.audio_devices', level='WARNING'):
            self.refresh()
            self.refresh()
        self.play_ready_sound.assert_called_once_with()
        self.devices[1] = input_device('Yeti')
        self.refresh()
        self.refresh()
        self.assertEqual(self.play_ready_sound.call_count, 2)

    def test_startup_available_source_prints_indented_status(self):
        with patch('builtins.print') as output:
            self.audio_devices.print_startup_status()
            self.audio_devices.print_startup_warning()
        output.assert_called_once_with('   ✓ Audio source [Yeti] [WASAPI]')

    def test_runtime_missing_source_prints_after_blank_line_without_indentation(self):
        self.devices[1] = input_device('Other microphone')
        with patch('builtins.print') as output:
            with self.assertLogs('src.whisper_key.audio_devices', level='WARNING'):
                self.refresh()
        output.assert_called_once_with(
            f"\n{BOLD_RED}❌ Yeti [WASAPI] is unavailable; reconnect it or select another source.{RESET}",
            flush=True,
        )

    def test_reconnection_prints_recovery_once(self):
        self.devices[1] = input_device('Other microphone')
        with self.assertLogs('src.whisper_key.audio_devices', level='WARNING'):
            self.refresh()
        self.devices[1] = input_device('Yeti')
        with patch('builtins.print') as output:
            self.refresh()
            self.refresh()
        output.assert_called_once_with('\n✅ Audio source reconnected: [Yeti] [WASAPI].')

    def test_loopback_name_is_matched_exactly_and_outputs_are_excluded(self):
        name = 'Speakers (A very long audio device name) [Loopback]'
        self.devices.extend([input_device(name, channels=0), input_device(name)])
        self.audio_devices.load()
        self.assertEqual(self.audio_devices.resolve(name, 'Windows WASAPI'), 4)
        self.assertNotIn(3, [item['id'] for item in self.audio_devices.input_devices('Windows WASAPI')])
        with self.assertLogs('src.whisper_key.audio_devices', level='WARNING'):
            self.assertEqual(self.audio_devices.resolve('Speakers (A very long', 'Windows WASAPI'), -1)

    def test_numeric_setting_does_not_silently_select_reused_index(self):
        with self.assertNoLogs('src.whisper_key.audio_devices', level='WARNING'):
            self.assertEqual(self.audio_devices.resolve(1, 'Windows WASAPI'), -1)

    def test_system_default_changes_do_not_change_selected_source(self):
        self.hosts[1]['default_input_device'] = 2
        self.refresh()
        self.assertEqual(self.recorder.device, 1)
        self.hosts[1]['default_input_device'] = -1
        self.refresh()
        self.assertEqual(self.recorder.device, 1)

    def test_missing_host_does_not_fall_back_to_another_host(self):
        self.settings['host'] = 'Disconnected host'
        self.audio_devices.selected_host = 'Disconnected host'
        with self.assertLogs('src.whisper_key.audio_devices', level='WARNING'):
            self.refresh()
        self.assertEqual(self.recorder.device, -1)
        self.assertEqual(self.settings['host'], 'Disconnected host')

    def test_host_matching_ignores_case(self):
        self.settings['host'] = 'windows wasapi'
        self.audio_devices.selected_host = 'windows wasapi'
        self.audio_devices._initialize_selection()
        self.assertEqual(self.manager.get_current_audio_host(), 'Windows WASAPI')
        self.assertEqual(self.audio_devices.resolve('Yeti', 'WINDOWS WASAPI'), 1)
        self.assertTrue(self.manager.request_audio_device_change('Webcam', 'windows wasapi'))
        self.assertEqual(self.settings['host'], 'Windows WASAPI')
        self.assertEqual(self.recorder.device, 2)

    def test_hosts_without_inputs_are_hidden_and_cannot_be_selected(self):
        self.hosts.append({'name': 'Empty host', 'default_input_device': -1})
        self.devices.append(input_device('Output only', host=2, channels=0))
        self.audio_devices.load()
        self.assertNotIn('Empty host', [host['name'] for host in self.manager.get_available_audio_hosts()])
        self.assertFalse(self.manager.set_audio_host('Empty host'))
        self.assertEqual(self.settings['host'], 'Windows WASAPI')

    def test_missing_named_selection_uses_default_input_without_pinning_it(self):
        self.settings['input_device'] = None
        self.audio_devices.selected_name = None
        self.refresh()
        self.assertEqual(self.audio_devices.device_id, 2)
        self.assertEqual(self.settings, {'source': 'default_input', 'host': None, 'input_device': None})
        self.hosts[1]['default_input_device'] = 1
        self.refresh()
        self.assertEqual(self.recorder.device, 1)
        self.assertIsNone(self.settings['input_device'])

    def use_default_input(self):
        self.assertTrue(self.manager.request_default_audio_source('default_input'))
        self.refresh()
        self.play_ready_sound.reset_mock()

    def test_default_input_startup_uses_system_default_and_does_not_save_name(self):
        save = Mock()
        audio_devices = AudioDeviceManager(None, None, save, self.play_ready_sound, 'default_input')
        self.assertEqual(audio_devices.device_id, 2)
        save.assert_not_called()
        with patch('builtins.print') as output:
            audio_devices.print_startup_status()
        output.assert_called_once_with('   ✓ Audio source using System default input [WASAPI]')

    def test_default_mode_ignores_previously_selected_host(self):
        self.assertTrue(self.manager.set_audio_host('MME'))
        self.use_default_input()
        self.assertEqual(self.recorder.device, 2)
        self.assertEqual(self.settings, {'source': 'default_input', 'host': None, 'input_device': None})

    def test_default_input_changes_without_saving_resolved_device(self):
        self.use_default_input()
        self.config.update_audio_source.reset_mock()
        self.hosts[1]['default_input_device'] = 1
        self.audio_devices.request_default_refresh('default_input')
        with patch('builtins.print') as output:
            self.refresh()
            self.refresh()
        self.assertEqual(self.recorder.device, 1)
        self.config.update_audio_source.assert_not_called()
        output.assert_called_once_with('✅ System default input source changed: Yeti [WASAPI].')
        self.play_ready_sound.assert_not_called()

    def test_default_output_follows_loopback_and_waits_until_recording_finishes(self):
        self.devices.extend([input_device('Speakers [Loopback]'), input_device('Headphones [Loopback]')])
        with patch('src.whisper_key.audio_devices.platform_audio_devices.resolve_default_device', side_effect=[3, 4]):
            self.assertTrue(self.manager.request_default_audio_source('default_output'))
            self.refresh()
            self.assertEqual(self.recorder.device, 3)
            self.assertEqual(self.settings, {'source': 'default_output', 'host': None, 'input_device': None})
            self.audio_devices.request_default_refresh('default_input')
            self.assertFalse(self.audio_devices.refresh_pending)
            self.recorder.is_recording = True
            self.audio_devices.request_default_refresh('default_output')
            self.refresh()
            self.assertEqual(self.recorder.device, 3)
            self.recorder.is_recording = False
            with patch('builtins.print') as output:
                self.refresh()
        self.assertEqual(self.recorder.device, 4)
        output.assert_called_once_with('✅ System default output source changed: Headphones [Loopback] [WASAPI].')
        self.play_ready_sound.assert_not_called()

    def test_unrelated_default_events_do_not_request_refresh(self):
        self.audio_devices.request_default_refresh('default_input')
        self.assertFalse(self.audio_devices.refresh_pending)
        self.use_default_input()
        self.audio_devices.request_default_refresh('default_output')
        self.assertFalse(self.audio_devices.refresh_pending)

    def test_default_change_waits_for_recording_and_processing(self):
        self.use_default_input()
        self.recorder.is_recording = True
        self.hosts[1]['default_input_device'] = 1
        self.audio_devices.request_default_refresh('default_input')
        with patch.object(self.recorder, 'cancel_recording') as cancel:
            with patch('builtins.print') as output:
                self.refresh()
                self.manager.refresh_audio_devices()
            cancel.assert_not_called()
        output.assert_called_once_with(
            '🎤 System default input changed; will switch after the current recording and transcription finish.'
        )
        self.assertTrue(self.recorder.is_recording)
        self.assertEqual(self.recorder.device, 2)
        self.recorder.is_recording = False
        self.manager.is_processing = True
        self.refresh()
        self.assertEqual(self.recorder.device, 2)
        self.manager.is_processing = False
        self.refresh()
        self.assertEqual(self.recorder.device, 1)
        self.play_ready_sound.assert_not_called()

    def test_latest_default_wins_after_recording(self):
        self.use_default_input()
        self.recorder.is_recording = True
        self.hosts[1]['default_input_device'] = 1
        self.audio_devices.request_default_refresh('default_input')
        self.refresh()
        self.hosts[1]['default_input_device'] = 2
        self.audio_devices.request_default_refresh('default_input')
        self.refresh()
        self.recorder.is_recording = False
        self.refresh()
        self.assertEqual(self.recorder.device, 2)
        self.play_ready_sound.assert_not_called()

    def test_missing_default_does_not_fall_back_to_first_input(self):
        self.use_default_input()
        self.hosts[1]['default_input_device'] = -1
        with self.assertLogs('src.whisper_key.audio_devices', level='WARNING'):
            self.refresh()
        self.assertEqual(self.recorder.device, -1)
        self.assertFalse(self.manager._start_audio_recording())
        self.hosts[1]['default_input_device'] = 1
        self.refresh()
        self.assertEqual(self.recorder.device, 1)
        self.assertEqual(self.audio_devices.source_mode, 'default_input')
        self.assertEqual(self.play_ready_sound.call_count, 2)

    def test_default_reordering_does_not_announce_a_device_change(self):
        self.use_default_input()
        self.devices[1], self.devices[2] = self.devices[2], self.devices[1]
        self.hosts[1]['default_input_device'] = 1
        with patch('builtins.print') as output:
            self.refresh()
        output.assert_not_called()
        self.play_ready_sound.assert_not_called()
        self.assertEqual(self.recorder.device, 1)

    def test_selecting_named_device_exits_default_mode(self):
        self.use_default_input()
        self.assertTrue(self.manager.request_audio_device_change('Yeti', 'MME'))
        self.assertEqual(self.settings, {'source': 'device', 'host': 'MME', 'input_device': 'Yeti'})
        self.hosts[1]['default_input_device'] = 1
        self.audio_devices.request_default_refresh('default_input')
        self.assertFalse(self.audio_devices.refresh_pending)
        self.assertEqual(self.recorder.device, 0)

    def test_default_notification_waits_until_recorder_accepts_device(self):
        self.use_default_input()
        self.hosts[1]['default_input_device'] = 1
        original_resolve = self.recorder.resolve_device

        def resolve_device(device_id):
            if device_id == 1:
                raise OSError('device unavailable')
            return original_resolve(device_id)

        with patch.object(self.recorder, 'resolve_device', side_effect=resolve_device):
            with self.assertLogs('src.whisper_key.audio_devices', level='WARNING'):
                self.refresh()
        self.play_ready_sound.assert_not_called()
        self.assertEqual(self.recorder.device, -1)
        self.refresh()
        self.play_ready_sound.assert_called_once_with()

    def test_failed_default_mode_save_preserves_named_selection(self):
        self.config.update_audio_source.side_effect = OSError('disk full')
        with self.assertRaises(OSError):
            self.manager.request_default_audio_source('default_input')
        self.assertEqual(self.audio_devices.source_mode, 'device')
        self.assertEqual(self.audio_devices.selected_name, 'Yeti')
        self.assertFalse(self.audio_devices.refresh_pending)

    def test_tray_default_selection_does_not_check_named_device(self):
        self.use_default_input()
        tray = SystemTray.__new__(SystemTray)
        tray.state_manager = self.manager
        items = list(tray._build_audio_source_menu())
        self.assertEqual([item.text for item in items[:2]], ['System default input', 'System default output'])
        self.assertTrue(items[0].checked)
        self.assertFalse(items[1].checked)
        self.assertEqual(tray._audio_source_label(), 'Source: System input')
        self.assertNotIn('Specific device', [item.text for item in items])
        wasapi = next(item for item in items if item.text == 'WASAPI')
        self.assertFalse(wasapi.checked)
        self.assertFalse(any(item.checked for item in wasapi.submenu))
        tray._select_audio_device = Mock()
        list(wasapi.submenu)[1](None)
        tray._select_audio_device.assert_called_once_with('Webcam', 'Windows WASAPI')

    def test_tray_marks_named_device_host_and_shortens_only_parent_label(self):
        name = 'Microphone (A very long microphone device name)'
        self.devices[1]['name'] = name
        self.audio_devices.load()
        self.assertTrue(self.manager.request_audio_device_change(name, 'Windows WASAPI'))
        tray = SystemTray.__new__(SystemTray)
        tray.state_manager = self.manager
        items = list(tray._build_audio_source_menu())
        wasapi = next(item for item in items if item.text == 'WASAPI')
        mme = next(item for item in items if item.text == 'MME')
        self.assertTrue(wasapi.checked)
        self.assertTrue(wasapi.radio)
        self.assertFalse(mme.checked)
        self.assertFalse(items[0].checked)
        self.assertEqual(tray._audio_source_label(), f'Source: {name[:23].rstrip()}…')
        self.assertTrue(next(item for item in wasapi.submenu if item.text == name).checked)

    def test_tray_keeps_defaults_selectable_without_devices(self):
        self.use_default_input()
        self.devices.clear()
        self.hosts[1]['default_input_device'] = -1
        with self.assertLogs('src.whisper_key.audio_devices', level='WARNING'):
            self.refresh()
        tray = SystemTray.__new__(SystemTray)
        tray.state_manager = self.manager
        items = list(tray._build_audio_source_menu())
        self.assertTrue(items[0].enabled)
        self.assertTrue(items[1].enabled)
        self.assertFalse(items[-1].enabled)

    def test_manual_switch_cancels_recording_before_changing_source(self):
        self.recorder.is_recording = True
        with patch.object(self.recorder, 'cancel_recording', wraps=self.recorder.cancel_recording) as cancel:
            self.assertTrue(self.manager.request_audio_device_change('Webcam', 'Windows WASAPI'))
            cancel.assert_called_once()
        self.assertFalse(self.recorder.is_recording)
        self.assertEqual(self.recorder.device, 2)
        self.assertFalse(self.audio_devices.selection_pending)

    def test_cancelled_stream_must_close_before_selection_changes(self):
        self.recorder.is_recording = True
        self.recorder.recording_thread = Mock(is_alive=Mock(return_value=True))
        with self.assertLogs('src.whisper_key.audio_recorder', level='WARNING'):
            self.assertTrue(self.manager.request_audio_device_change('Webcam', 'Windows WASAPI'))
        self.assertEqual(self.recorder.device, 1)
        self.assertTrue(self.audio_devices.selection_pending)
        self.recorder.recording_thread.is_alive.return_value = False
        self.manager.refresh_audio_devices()
        self.assertEqual(self.recorder.device, 2)

    def test_no_devices_can_recover_when_microphone_appears(self):
        self.devices.clear()
        with self.assertLogs('src.whisper_key.audio_devices', level='WARNING'):
            self.refresh()
        self.assertEqual(self.recorder.device, -1)
        self.devices.append(input_device('Yeti'))
        self.refresh()
        self.assertEqual(self.recorder.device, 0)

    def test_refresh_waits_for_recording_transcription_and_stream_cleanup(self):
        for busy_state in ('recording', 'processing', 'closing_stream', 'transition'):
            with self.subTest(state=busy_state):
                self.recorder.is_recording = busy_state == 'recording'
                self.manager.is_processing = busy_state == 'processing'
                self.manager._audio_transition = busy_state == 'transition'
                self.recorder.recording_thread = Mock(is_alive=lambda: busy_state == 'closing_stream')
                with patch.object(self.audio_devices, 'refresh') as refresh:
                    self.refresh()
                    refresh.assert_not_called()
        self.recorder.is_recording = False
        self.recorder.recording_thread = None
        self.manager.is_processing = False
        self.manager._audio_transition = False
        with patch.object(self.audio_devices, 'refresh', wraps=self.audio_devices.refresh) as refresh:
            self.refresh()
            refresh.assert_called_once()

    def test_queued_selection_resolves_name_after_device_numbers_change(self):
        self.manager.is_processing = True
        self.assertTrue(self.manager.request_audio_device_change('Webcam', 'Windows WASAPI'))
        self.assertEqual(self.recorder.device, 1)
        self.assertEqual(self.settings['input_device'], 'Webcam')
        self.devices[1], self.devices[2] = self.devices[2], self.devices[1]
        self.manager.is_processing = False
        self.refresh()
        self.assertEqual(self.recorder.device, 1)
        self.assertEqual(self.devices[self.recorder.device]['name'], 'Webcam')

    def test_host_change_selects_first_input_on_that_host(self):
        self.assertTrue(self.manager.set_audio_host('MME'))
        self.config.update_audio_source.assert_called_once_with('device', 'MME', 'Yeti')
        self.assertEqual(self.recorder.device, 0)

    def test_reselecting_current_host_preserves_named_device(self):
        self.assertTrue(self.manager.set_audio_host('Windows WASAPI'))
        self.assertEqual(self.settings['input_device'], 'Yeti')
        self.config.update_audio_source.assert_not_called()

    def test_failed_config_write_restores_both_preferences(self):
        config = ConfigManager.__new__(ConfigManager)
        config.config = {'audio': self.settings.copy()}
        with patch.object(config, '_save_user_overrides', side_effect=OSError('disk full')):
            with self.assertRaises(OSError):
                config.update_audio_source('default_input', None, None)
        self.assertEqual(config.config['audio'], self.settings)

    def test_stale_menu_selection_cannot_select_replacement_device(self):
        self.devices[1] = input_device('Different microphone')
        self.audio_devices.load()
        self.assertFalse(self.manager.request_audio_device_change('Yeti', 'Windows WASAPI'))
        self.config.update_audio_source.assert_not_called()

    def test_notification_burst_is_debounced(self):
        with patch('src.whisper_key.audio_devices.time.monotonic') as clock:
            clock.return_value = 10
            self.audio_devices.request_refresh()
            self.manager.refresh_audio_devices()
            self.assertEqual(self.audio_devices._refresh_deadline, 10.5)
            clock.return_value = 10.3
            self.audio_devices.request_refresh()
            self.manager.refresh_audio_devices()
            self.assertEqual(self.audio_devices._refresh_deadline, 10.8)
            self.audio_mocks[-2].assert_not_called()
            clock.return_value = 10.9
            self.manager.refresh_audio_devices()
            self.audio_mocks[-2].assert_called_once()

    def test_new_recording_is_blocked_until_refresh_finishes(self):
        self.audio_devices.request_refresh()
        with patch.object(self.recorder, 'start_recording') as start:
            self.assertFalse(self.manager._start_audio_recording())
            start.assert_not_called()

    def test_refresh_failure_discards_old_indices_and_retries(self):
        with patch('src.whisper_key.audio_devices.sd._initialize', side_effect=RuntimeError('unavailable')):
            with self.assertLogs('src.whisper_key.audio_devices', level='WARNING'):
                self.refresh()
        self.assertEqual(self.recorder.device, -1)
        self.assertEqual(self.audio_devices.devices, [])
        self.assertIsNotNone(self.audio_devices._refresh_deadline)
        self.refresh()
        self.assertEqual(self.recorder.device, 1)

    def test_refresh_updates_sample_rate_for_streaming(self):
        self.recorder.continuous_streaming = Mock()
        self.devices[1]['default_samplerate'] = 44100
        self.refresh()
        self.assertEqual(self.recorder.device_native_rate, 44100)
        self.recorder.continuous_streaming.set_recording_rate.assert_called_once_with(44100)

    def test_failed_command_start_does_not_leave_command_mode_enabled(self):
        self.recorder.resolve_device(-1)
        self.assertFalse(self.manager._start_audio_recording(command_mode=True))
        self.assertFalse(self.manager._command_mode)

    def test_command_start_is_atomic_to_state_readers(self):
        start_entered = threading.Event()
        finish_start = threading.Event()
        reader_entered = threading.Event()
        reader_finished = threading.Event()
        observed = []

        def start_recording():
            start_entered.set()
            if not finish_start.wait(2):
                return False
            self.recorder.is_recording = True
            return True

        def read_state():
            reader_entered.set()
            observed.append((self.manager.get_application_state(), self.manager.is_transcription_recording()))
            reader_finished.set()

        with patch.object(self.recorder, 'start_recording', side_effect=start_recording):
            start_thread = threading.Thread(target=self.manager._start_audio_recording, kwargs={'command_mode': True}, daemon=True)
            reader_thread = threading.Thread(target=read_state, daemon=True)
            start_thread.start()
            try:
                self.assertTrue(start_entered.wait(2))
                reader_thread.start()
                self.assertTrue(reader_entered.wait(2))
                self.assertFalse(reader_finished.wait(0.05))
            finally:
                finish_start.set()
                start_thread.join(2)
                if reader_thread.ident is not None:
                    reader_thread.join(2)
            self.assertFalse(start_thread.is_alive())
            self.assertFalse(reader_thread.is_alive())
        self.assertTrue(observed[0][0]['recording'])
        self.assertFalse(observed[0][1])

    def test_model_loading_releases_state_lock_before_tray_accesses_audio(self):
        ui_entered = threading.Event()

        def update_tray(state):
            ui_entered.set()
            self.manager.get_available_audio_hosts()
            self.manager.get_application_state()

        with patch.object(self.manager.system_tray, 'update_state', side_effect=update_tray):
            model_thread = threading.Thread(target=self.manager.set_model_loading, args=(True,), daemon=True)
            try:
                with self.manager._audio_lock:
                    model_thread.start()
                    self.assertTrue(ui_entered.wait(2))
                    acquired = self.manager._state_lock.acquire(timeout=0.5)
                    if acquired:
                        self.manager._state_lock.release()
                    self.assertTrue(acquired)
            finally:
                model_thread.join(2)
            self.assertFalse(model_thread.is_alive())

    def test_disconnect_error_returns_ui_to_idle_and_requests_refresh(self):
        self.manager._command_mode = True
        self.manager.handle_recording_error()
        self.manager.refresh_audio_devices()
        self.assertFalse(self.manager._command_mode)
        self.manager.system_tray.update_state.assert_called_with('idle')
        self.assertIsNotNone(self.audio_devices._refresh_deadline)

    def test_shutdown_ignores_device_events_and_new_recordings(self):
        self.manager.shutdown()
        self.audio_devices.request_refresh()
        with patch.object(self.audio_devices, 'refresh') as refresh:
            self.manager.refresh_audio_devices()
            refresh.assert_not_called()
        self.assertFalse(self.manager._start_audio_recording())
        self.assertFalse(self.manager.request_audio_device_change('Yeti', 'Windows WASAPI'))

    def test_monitor_lifecycle_belongs_to_audio_devices(self):
        with patch('src.whisper_key.audio_devices.platform_audio_devices.DeviceChangeMonitor') as monitor_type:
            self.audio_devices.start()
            self.audio_devices.start()
            monitor_type.return_value.start.assert_called_once()
            self.assertTrue(self.audio_devices.refresh_pending)
            on_change = monitor_type.call_args.args[0]
            self.audio_devices.stop()
            monitor_type.return_value.stop.assert_called_once()
            on_change()
            self.assertFalse(self.audio_devices.refresh_pending)
            self.assertFalse(self.audio_devices.select_host('MME'))

    def test_monitor_failure_uses_periodic_refresh(self):
        with patch('src.whisper_key.audio_devices.platform_audio_devices.DeviceChangeMonitor') as monitor_type:
            monitor_type.return_value.start.side_effect = OSError('notifications unavailable')
            with self.assertLogs('src.whisper_key.audio_devices', level='WARNING'):
                self.audio_devices.start()
            with patch('src.whisper_key.audio_devices.time.monotonic') as clock:
                clock.return_value = 10
                self.manager.refresh_audio_devices()
                clock.return_value = 11
                self.manager.refresh_audio_devices()
                self.assertFalse(self.audio_devices.refresh_pending)
                self.assertTrue(self.audio_devices.ready_to_record())
                clock.return_value = 16
                with patch.object(self.audio_devices, 'refresh', wraps=self.audio_devices.refresh) as refresh:
                    self.manager.refresh_audio_devices()
                    refresh.assert_called_once()
            self.audio_devices.stop()

    def test_hotkey_cannot_reinitialize_portaudio_when_refresh_is_due(self):
        self.audio_devices._refresh_deadline = 0
        with patch.object(self.audio_devices, 'refresh') as refresh:
            self.assertFalse(self.manager._start_audio_recording())
            refresh.assert_not_called()

    def test_failed_persistence_does_not_change_selection_or_cancel_recording(self):
        self.recorder.is_recording = True
        self.config.update_audio_source.side_effect = OSError('disk full')
        with self.assertRaises(OSError):
            self.manager.request_audio_device_change('Webcam', 'Windows WASAPI')
        self.assertEqual(self.audio_devices.selected_name, 'Yeti')
        self.assertEqual(self.audio_devices.selected_host, 'Windows WASAPI')
        self.assertTrue(self.recorder.is_recording)

    def test_recording_cannot_start_during_portaudio_reinitialization(self):
        refresh_entered = threading.Event()
        finish_refresh = threading.Event()
        start_entered = threading.Event()

        def blocked_refresh():
            refresh_entered.set()
            self.assertTrue(finish_refresh.wait(2))
            self.devices[1], self.devices[2] = self.devices[2], self.devices[1]
            self.audio_devices.load()

        def start_recording():
            start_entered.set()
            self.manager._start_audio_recording()

        with patch.object(self.audio_devices, 'refresh', side_effect=blocked_refresh):
            with patch.object(self.recorder, 'start_recording', return_value=True) as start:
                refresh_thread = threading.Thread(target=self.refresh)
                start_thread = threading.Thread(target=start_recording)
                refresh_thread.start()
                try:
                    self.assertTrue(refresh_entered.wait(2))
                    start_thread.start()
                    self.assertTrue(start_entered.wait(2))
                    start.assert_not_called()
                finally:
                    finish_refresh.set()
                    refresh_thread.join(2)
                    if start_thread.ident is not None:
                        start_thread.join(2)
                self.assertFalse(refresh_thread.is_alive())
                self.assertFalse(start_thread.is_alive())
                start.assert_called_once()
                self.assertEqual(self.recorder.device, 2)


if __name__ == '__main__':
    unittest.main()
