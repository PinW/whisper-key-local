import logging
import os
import re
import shutil
import subprocess
from typing import Optional

from ruamel.yaml import YAML

from .utils import resolve_asset_path, get_user_app_data_path
from .platform import keyboard


class VoiceCommandManager:
    def __init__(self, enabled=True):
        self.enabled = enabled
        self.logger = logging.getLogger(__name__)

        if not self.enabled:
            self.logger.info("Voice commands disabled by configuration")
            return

        defaults_path = resolve_asset_path("commands.defaults.yaml")
        user_path = os.path.join(get_user_app_data_path(), "commands.yaml")

        if not os.path.exists(user_path):
            shutil.copy2(defaults_path, user_path)
            self.logger.info(f"Created user commands file from defaults: {user_path}")

        yaml = YAML()
        with open(user_path, 'r', encoding='utf-8') as f:
            data = yaml.load(f)

        self.commands_path = user_path
        raw_commands = data.get('commands', []) if data else []
        self.commands = self._validate_commands(raw_commands)
        self.commands.sort(key=lambda cmd: len(cmd.get('trigger', '')), reverse=True)
        self.logger.info(f"Loaded {len(self.commands)} voice commands")

    def _validate_commands(self, raw_commands: list) -> list:
        valid = []
        for i, cmd in enumerate(raw_commands):
            trigger = cmd.get('trigger', '')
            has_run = 'run' in cmd
            has_hotkey = 'hotkey' in cmd

            if not trigger:
                self.logger.warning(f"Command {i}: missing trigger, skipping")
                continue

            if has_run == has_hotkey:
                self.logger.warning(f"Command '{trigger}': needs exactly one of 'run' or 'hotkey', skipping")
                continue

            valid.append(cmd)
        return valid

    def match_command(self, text: str) -> Optional[dict]:
        normalized = re.sub(r'[^\w\s]', '', text.lower()).strip()

        for command in self.commands:
            trigger = command.get('trigger', '').lower()
            if trigger and trigger in normalized:
                return command

        return None

    def execute_command(self, command: dict):
        trigger = command.get('trigger', '')

        if 'run' in command:
            self._execute_shell(command['run'], trigger)
        elif 'hotkey' in command:
            self._send_hotkey(command['hotkey'], trigger)

    def _execute_shell(self, run_str: str, trigger: str):
        try:
            subprocess.Popen(run_str, shell=True)
            self.logger.info(f"Executed command '{trigger}': {run_str}")
            print(f"   Executed: {trigger}")
        except Exception as e:
            self.logger.error(f"Failed to execute command '{trigger}': {e}")
            print(f"   Failed to execute command: {e}")

    def _send_hotkey(self, hotkey_str: str, trigger: str):
        keys = [k.strip() for k in hotkey_str.lower().split('+')]
        try:
            keyboard.send_hotkey(*keys)
            self.logger.info(f"Sent hotkey '{trigger}': {hotkey_str}")
            print(f"   Sent hotkey: {trigger} [{hotkey_str}]")
        except Exception as e:
            self.logger.error(f"Failed to send hotkey '{trigger}': {e}")
            print(f"   Failed to send hotkey: {e}")
