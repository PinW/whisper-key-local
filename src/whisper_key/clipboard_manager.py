import logging
import time
from typing import Optional

import pyperclip

from .platform import keyboard
from .utils import parse_hotkey

class ClipboardManager:
    def __init__(self, key_simulation_delay, auto_paste, preserve_clipboard,
                 paste_hotkey, delivery_method, clipboard_restore_delay):
        self.logger = logging.getLogger(__name__)
        self.key_simulation_delay = key_simulation_delay
        self.auto_paste = auto_paste
        self.preserve_clipboard = preserve_clipboard
        self.paste_hotkey = paste_hotkey
        self.paste_keys = parse_hotkey(paste_hotkey)
        self.delivery_method = delivery_method
        self.clipboard_restore_delay = clipboard_restore_delay
        self._configure_keyboard_timing()
        if self.delivery_method == "paste":
            self._test_clipboard_access()
        self._print_status()

    def _configure_keyboard_timing(self):
        keyboard.set_delay(self.key_simulation_delay)

    def _test_clipboard_access(self):
        try:
            pyperclip.paste()
            self.logger.info("Clipboard access test successful")

        except Exception as e:
            self.logger.error(f"Clipboard access test failed: {e}")
            raise

    def _print_status(self):
        hotkey_display = self.paste_hotkey.upper()
        if self.auto_paste:
            if self.delivery_method == "type":
                print(f"   ✓ Auto-paste is ENABLED using direct text injection")
            else:
                print(f"   ✓ Auto-paste is ENABLED using clipboard paste ({hotkey_display})")
        else:
            print(f"   ✗ Auto-paste is DISABLED - paste manually with {hotkey_display}")

    def copy_text(self, text: str) -> bool:
        if not text:
            return False

        try:
            self.logger.info(f"Copying text to clipboard ({len(text)} chars)")
            pyperclip.copy(text)
            return True

        except Exception as e:
            self.logger.error(f"Failed to copy text to clipboard: {e}")
            return False

    def get_clipboard_content(self) -> Optional[str]:
        try:
            clipboard_content = pyperclip.paste()

            if clipboard_content:
                return clipboard_content
            else:
                return None

        except Exception as e:
            self.logger.error(f"Failed to paste text from clipboard: {e}")
            return None

    def copy_with_notification(self, text: str) -> bool:
        if not text:
            return False

        success = self.copy_text(text)

        if success:
            print("   ✓ Copied to clipboard")
            print("   ✓ You can now paste with Ctrl+V in any application!")

        return success

    def clear_clipboard(self) -> bool:
        try:
            pyperclip.copy("")
            return True

        except Exception as e:
            self.logger.error(f"Failed to clear clipboard: {e}")
            return False

    def _type_delivery(self, text: str) -> bool:
        try:
            keyboard.type_text(text)
            print(f"   ✓ Text injected directly")
            return True
        except Exception as e:
            self.logger.error(f"Failed to inject text: {e}")
            return False

    def _clipboard_paste(self, text: str) -> bool:
        try:
            original_content = None
            if self.preserve_clipboard:
                original_content = pyperclip.paste()

            if not self.copy_text(text):
                return False

            keyboard.send_hotkey(*self.paste_keys)

            print(f"   ✓ Auto-pasted via clipboard")

            if original_content is not None:
                time.sleep(self.clipboard_restore_delay)
                pyperclip.copy(original_content)

            return True

        except Exception as e:
            self.logger.error(f"Failed to simulate paste keypress: {e}")
            return False

    def execute_delivery(self, text: str) -> bool:
        if self.delivery_method == "type":
            return self._type_delivery(text)
        else:
            return self._clipboard_paste(text)

    def send_enter_key(self) -> bool:
        try:
            self.logger.info("Sending ENTER key to active application")
            keyboard.send_key('enter')
            print("   ✓ Text submitted with ENTER!")

            return True

        except Exception as e:
            self.logger.error(f"Failed to send ENTER key: {e}")
            return False

    def deliver_transcription(self,
                              transcribed_text: str,
                              use_auto_enter: bool = False) -> bool:

        try:
            if use_auto_enter:
                print("🚀 Auto-pasting text and SENDING with ENTER...")

                success = self._clipboard_paste(transcribed_text)
                if success:
                    success = self.send_enter_key()

            elif self.auto_paste:
                print("🚀 Auto-pasting text...")
                success = self.execute_delivery(transcribed_text)

            else:
                print("📋 Copying to clipboard...")
                success = self.copy_with_notification(transcribed_text)

            return success

        except Exception as e:
            self.logger.error(f"Delivery workflow failed: {e}")
            return False

    def update_auto_paste(self, enabled: bool):
        self.auto_paste = enabled
        self._print_status()
