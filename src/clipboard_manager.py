import logging
import pyperclip
import time
from typing import Optional

import win32gui
import pyautogui

pyautogui.FAILSAFE = True  # Enable "move mouse to corner to abort automation"

class ClipboardManager:    
    def __init__(self, key_simulation_delay, auto_paste, preserve_clipboard):
        self.logger = logging.getLogger(__name__)
        self.key_simulation_delay = key_simulation_delay
        self.auto_paste = auto_paste
        self.preserve_clipboard = preserve_clipboard
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
            raise RuntimeError("Could not access system clipboard. Please check permissions.")
    
    def _print_status(self):
        if self.auto_paste:
            method_name = "key simulation (CTRL+V)"
            print(f"   ✓ Auto-paste is ENABLED using {method_name}")
        else:
            print("   ✗ Auto-paste is DISABLED - paste manually with Ctrl+V")
    
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
    
    def get_active_window_handle(self) -> Optional[int]:
        try:
            hwnd = win32gui.GetForegroundWindow()
            if hwnd:
                window_title = win32gui.GetWindowText(hwnd)
                self.logger.info(f"Active window: '{window_title}' (handle: {hwnd})")
                return hwnd
            else:
                return None
        except Exception as e:
            self.logger.error(f"Failed to get active window handle: {e}")
            return None       
    
    def execute_auto_paste(self, text: str, preserve_clipboard: bool) -> bool:              
        try:
            if preserve_clipboard:
                original_content = pyperclip.paste()

            if not self.copy_text(text):
                return False
                      
            pyautogui.hotkey('ctrl', 'v')

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
            success = False

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
        
    def get_clipboard_info(self) -> dict:
        try:
            content = pyperclip.paste()
            info = {
                "has_content": bool(content),
                "content_length": len(content) if content else 0,
                "preview": content[:50] + "..." if content and len(content) > 50 else content,
                "key_simulation_available": True
            }
            
            hwnd = self.get_active_window_handle()
            if hwnd:
                try:
                    window_title = win32gui.GetWindowText(hwnd)
                    info["active_window"] = {
                        "handle": hwnd,
                        "title": window_title
                    }
                except:
                    info["active_window"] = {"handle": hwnd, "title": "Unknown"}
            
            return info
            
        except Exception as e:
            return {
                "has_content": False,
                "content_length": 0,
                "error": str(e),
                "key_simulation_available": True
            }