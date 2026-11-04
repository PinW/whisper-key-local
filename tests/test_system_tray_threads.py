import importlib.util
import queue
import sys
import threading
import types
import unittest
from pathlib import Path
from unittest.mock import Mock, patch

from src.whisper_key.utils import setup_portaudio_path

setup_portaudio_path()

from src.whisper_key.system_tray import SystemTray


class ThreadCheckingIcon:
    def __init__(self):
        self.mutations = []

    def record(self, operation, value=None):
        if threading.current_thread() is not threading.main_thread():
            raise AssertionError(f'{operation} executed off the main thread')
        self.mutations.append((operation, value))

    @property
    def icon(self):
        return None

    @icon.setter
    def icon(self, value):
        self.record('icon', value)

    @property
    def menu(self):
        return None

    @menu.setter
    def menu(self, value):
        self.record('menu', value)

    @property
    def visible(self):
        return False

    @visible.setter
    def visible(self, value):
        self.record('visible', value)

    def run_detached(self, setup):
        worker = threading.Thread(target=setup, args=(self,))
        worker.start()
        worker.join(2)
        if worker.is_alive():
            raise AssertionError('Tray setup blocked waiting for the main thread')

    def stop(self):
        self.record('stop')


class SystemTrayThreadTests(unittest.TestCase):
    def setUp(self):
        self.callbacks = queue.Queue()
        appkit = types.ModuleType('AppKit')
        for name in ('NSApplication', 'NSApplicationActivationPolicyAccessory', 'NSEventMaskAny', 'NSDefaultRunLoopMode'):
            setattr(appkit, name, Mock())
        foundation = types.ModuleType('Foundation')
        foundation.NSDate = Mock()
        foundation.NSObject = object
        foundation.NSThread = Mock()
        foundation.NSThread.isMainThread.side_effect = lambda: threading.current_thread() is threading.main_thread()
        pyobjc_tools = types.ModuleType('PyObjCTools')
        pyobjc_tools.AppHelper = types.SimpleNamespace(callAfter=self.callbacks.put)
        path = Path(__file__).parents[1] / 'src' / 'whisper_key' / 'platform' / 'macos' / 'app.py'
        spec = importlib.util.spec_from_file_location('macos_tray_test_app', path)
        macos_app = importlib.util.module_from_spec(spec)
        with patch.dict(sys.modules, {'AppKit': appkit, 'Foundation': foundation, 'PyObjCTools': pyobjc_tools}):
            spec.loader.exec_module(macos_app)
        dispatch_patch = patch('src.whisper_key.system_tray.app.dispatch_ui', macos_app.dispatch_ui)
        dispatch_patch.start()
        self.addCleanup(dispatch_patch.stop)
        available_patch = patch('src.whisper_key.system_tray.TRAY_AVAILABLE', True)
        available_patch.start()
        self.addCleanup(available_patch.stop)
        self.tray = SystemTray.__new__(SystemTray)
        self.tray.icon = ThreadCheckingIcon()
        self.tray.is_running = True
        self.tray.available = True
        self.tray.current_state = 'idle'
        self.tray.icons = {'idle': 'idle-image', 'recording': 'recording-image', 'processing': 'processing-image'}
        self.tray.logger = Mock()
        self.tray.state_manager = Mock()
        self.tray.config_manager = Mock()
        self.tray._create_menu = Mock(return_value='menu')

    def run_worker(self, callback):
        failures = []

        def run():
            try:
                callback()
            except Exception as error:
                failures.append(error)

        worker = threading.Thread(target=run)
        worker.start()
        worker.join(2)
        self.assertFalse(worker.is_alive())
        self.assertEqual(failures, [])

    def drain_callbacks(self):
        while not self.callbacks.empty():
            self.callbacks.get_nowait()()

    def test_worker_state_change_updates_icon_and_menu_on_main_thread(self):
        self.run_worker(lambda: self.tray.update_state('recording'))
        self.assertEqual(self.tray.icon.mutations, [])
        self.tray._create_menu.assert_not_called()
        self.drain_callbacks()
        self.assertEqual(self.tray.icon.mutations, [('icon', 'recording-image'), ('menu', 'menu')])
        self.tray.logger.error.assert_not_called()

    def test_main_thread_update_runs_immediately(self):
        self.tray.update_state('processing')
        self.assertTrue(self.callbacks.empty())
        self.assertEqual(self.tray.icon.mutations, [('icon', 'processing-image'), ('menu', 'menu')])

    def test_queued_updates_use_latest_state(self):
        self.run_worker(lambda: self.tray.update_state('recording'))
        self.run_worker(lambda: self.tray.update_state('idle'))
        self.drain_callbacks()
        self.assertEqual([value for operation, value in self.tray.icon.mutations if operation == 'icon'], ['idle-image', 'idle-image'])

    def test_all_selection_actions_defer_menu_updates(self):
        actions = (
            lambda: self.tray._set_transcription_mode(False),
            lambda: self.tray._select_model('test-model'),
            lambda: self.tray._select_audio_host('Core Audio'),
            lambda: self.tray._select_audio_device('Microphone', 'Core Audio'),
            lambda: self.tray._select_default_audio_source('default_input'),
        )
        for action in actions:
            with self.subTest(action=action):
                self.tray.icon.mutations.clear()
                self.run_worker(action)
                self.assertEqual(self.tray.icon.mutations, [])
                self.drain_callbacks()
                self.assertEqual(self.tray.icon.mutations, [('menu', 'menu')])
                self.tray.logger.error.assert_not_called()

    def test_startup_setup_shows_icon_on_main_thread(self):
        self.tray.is_running = False
        icon = ThreadCheckingIcon()
        with patch('src.whisper_key.system_tray.pystray.Icon', return_value=icon):
            self.assertTrue(self.tray.start())
        self.assertEqual(icon.mutations, [])
        self.drain_callbacks()
        self.assertEqual(icon.mutations, [('visible', True)])

    def test_shutdown_prevents_pending_updates_and_visibility_changes(self):
        icon = self.tray.icon
        self.run_worker(lambda: self.tray.update_state('recording'))
        self.run_worker(self.tray.refresh_menu)
        self.run_worker(lambda: self.tray._setup_icon(icon))
        self.run_worker(self.tray.stop)
        self.assertFalse(self.tray.is_running)
        self.assertEqual(icon.mutations, [])
        self.drain_callbacks()
        self.assertEqual(icon.mutations, [('stop', None)])

    def test_old_callbacks_do_not_touch_replacement_icon(self):
        original = self.tray.icon
        self.run_worker(lambda: self.tray.update_state('recording'))
        self.tray.icon = ThreadCheckingIcon()
        self.drain_callbacks()
        self.assertEqual(original.mutations, [])
        self.assertEqual(self.tray.icon.mutations, [])

    def test_dispatch_failure_does_not_fall_back_to_worker(self):
        with patch('src.whisper_key.system_tray.app.dispatch_ui', side_effect=RuntimeError('dispatcher unavailable')):
            self.run_worker(lambda: self.tray.update_state('recording'))
        self.assertEqual(self.tray.icon.mutations, [])
        self.tray.logger.error.assert_called_once_with('Failed to schedule system tray update: dispatcher unavailable')

    def test_scheduled_update_failure_is_logged(self):
        self.tray._create_menu.side_effect = RuntimeError('menu unavailable')
        self.run_worker(self.tray.refresh_menu)
        self.drain_callbacks()
        self.tray.logger.error.assert_called_once_with('Failed to update system tray: menu unavailable')


if __name__ == '__main__':
    unittest.main()
