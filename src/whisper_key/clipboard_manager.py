import logging
import time
from typing import Optional

import pyperclip
import pyautogui

from .utils import parse_hotkey

pyautogui.FAILSAFE = True  # Enable "move mouse to corner to abort automation"

class ClipboardManager:
    def __init__(self, key_simulation_delay, auto_paste, preserve_clipboard, paste_hotkey):
        self.logger = logging.getLogger(__name__)
        self.key_simulation_delay = key_simulation_delay
        self.auto_paste = auto_paste
        self.preserve_clipboard = preserve_clipboard
        self.paste_hotkey = paste_hotkey
        self.paste_keys = parse_hotkey(paste_hotkey)
        self._configure_pyautogui_timing()
        self._test_clipboard_access()
        self._print_status()
    
    def _configure_pyautogui_timing(self):
        pyautogui.PAUSE = self.key_simulation_delay
    
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
            print(f"   ✓ Auto-paste is ENABLED using key simulation ({hotkey_display})")
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
    
    def execute_auto_paste(self, text: str, preserve_clipboard: bool) -> bool:              
        try:
            original_content = None
            if preserve_clipboard:
                original_content = pyperclip.paste()

            if not self.copy_text(text):
                return False
                      
            pyautogui.hotkey(*self.paste_keys)

            print(f"   ✓ Auto-pasted via key simulation")

            if original_content is not None:
                pyperclip.copy(original_content)
                time.sleep(self.key_simulation_delay)

            return True
            
        except Exception as e:
            self.logger.error(f"Failed to simulate paste keypress: {e}")
            return False
        
    def send_enter_key(self) -> bool:
        try:
            self.logger.info("Sending ENTER key to active application")
            pyautogui.press('enter')
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
               
                # Force auto-paste when using auto-enter hotkey
                success = self.execute_auto_paste(transcribed_text, self.preserve_clipboard)
                if success:
                    success = self.send_enter_key()

            elif self.auto_paste:
                print("🚀 Auto-pasting text...")
                success = self.execute_auto_paste(transcribed_text, self.preserve_clipboard)             
                    
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