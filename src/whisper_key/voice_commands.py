import logging
import os
import re
import shutil
import subprocess
from typing import Optional

from ruamel.yaml import YAML

from .utils import resolve_asset_path, get_user_app_data_path


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
        self.commands = data.get('commands', []) if data else []
        self.commands.sort(key=lambda cmd: len(cmd.get('trigger', '')), reverse=True)
        self.logger.info(f"Loaded {len(self.commands)} voice commands")

    def match_command(self, text: str) -> Optional[dict]:
        normalized = re.sub(r'[^\w\s]', '', text.lower()).strip()

        for command in self.commands:
            trigger = command.get('trigger', '').lower()
            if trigger and trigger in normalized:
                return command

        return None

    def execute_command(self, command: dict):
        run_str = command['run']
        trigger = command.get('trigger', '')
        try:
            subprocess.Popen(run_str, shell=True)
            self.logger.info(f"Executed command '{trigger}': {run_str}")
            print(f"   Executed: {trigger}")
        except Exception as e:
            self.logger.error(f"Failed to execute command '{trigger}': {e}")
            print(f"   Failed to execute command: {e}")
