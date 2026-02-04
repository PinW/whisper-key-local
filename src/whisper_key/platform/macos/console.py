import logging

class ConsoleManager:
    def __init__(self, config: dict, is_executable_mode: bool = False):
        self.logger = logging.getLogger(__name__)
        self.config = config
        self.is_executable_mode = is_executable_mode

    def show_console(self):
        return True

    def hide_console(self):
        return True
