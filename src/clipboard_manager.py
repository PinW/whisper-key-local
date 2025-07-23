"""
Clipboard Management Module

This module handles copying text to the system clipboard and pasting it into 
the currently active application.

For beginners: This is like the "Ctrl+C" and "Ctrl+V" functionality - it takes 
the transcribed text and automatically pastes it wherever your cursor is.
"""

import logging
import pyperclip
import time
from typing import Optional

try:
    import win32gui
    import win32con
    import win32clipboard
    WINDOWS_API_AVAILABLE = True
except ImportError:
    WINDOWS_API_AVAILABLE = False

class ClipboardManager:
    """
    A class that handles clipboard operations (copy/paste functionality)
    
    This class can put text onto the clipboard and retrieve text from it.
    """
    
    def __init__(self):
        """
        Initialize the clipboard manager
        
        We'll test clipboard access when we create this object to make sure it works.
        """
        self.logger = logging.getLogger(__name__)
        self._test_clipboard_access()
    
    def _test_clipboard_access(self):
        """
        Test if we can access the system clipboard
        
        This is important because clipboard access can sometimes fail due to 
        system permissions or other applications blocking it.
        """
        try:
            # Try to read current clipboard content
            current_content = pyperclip.paste()
            self.logger.info("Clipboard access test successful")
            
        except Exception as e:
            self.logger.error(f"Clipboard access test failed: {e}")
            raise RuntimeError("Could not access system clipboard. Please check permissions.")
    
    def copy_text(self, text: str) -> bool:
        """
        Copy text to the system clipboard
        
        Parameters:
        - text: The text to copy to clipboard
        
        Returns:
        - True if successful, False if failed
        
        For beginners: This is like pressing Ctrl+C - it puts the text into 
        the system's memory so it can be pasted elsewhere.
        """
        if not text:
            self.logger.warning("Attempted to copy empty text to clipboard")
            return False
        
        try:
            self.logger.info(f"Copying text to clipboard: '{text[:50]}...' ({len(text)} chars)")
            
            # Use pyperclip to put text on clipboard
            pyperclip.copy(text)
            
            # Verify it worked by reading it back
            time.sleep(0.1)  # Small delay to ensure clipboard is updated
            clipboard_content = pyperclip.paste()
            
            if clipboard_content == text:
                self.logger.info("Text successfully copied to clipboard")
                return True
            else:
                self.logger.error("Clipboard verification failed - text doesn't match")
                return False
                
        except Exception as e:
            self.logger.error(f"Failed to copy text to clipboard: {e}")
            return False
    
    def paste_text(self) -> Optional[str]:
        """
        Get text from the system clipboard
        
        Returns:
        - The text from clipboard, or None if clipboard is empty/inaccessible
        
        For beginners: This is like pressing Ctrl+V - it gets whatever text 
        is currently stored in the system's clipboard memory.
        """
        try:
            clipboard_content = pyperclip.paste()
            
            if clipboard_content:
                self.logger.info(f"Retrieved text from clipboard: '{clipboard_content[:50]}...' ({len(clipboard_content)} chars)")
                return clipboard_content
            else:
                self.logger.info("Clipboard is empty")
                return None
                
        except Exception as e:
            self.logger.error(f"Failed to paste text from clipboard: {e}")
            return None
    
    def copy_and_notify(self, text: str, show_notification: bool = True) -> bool:
        """
        Copy text to clipboard and optionally show a notification
        
        Parameters:
        - text: Text to copy
        - show_notification: Whether to print a message (for user feedback)
        
        This is the main method our app will use - it copies the transcribed 
        text and lets the user know it's ready to paste.
        """
        if not text:
            if show_notification:
                print("No text to copy!")
            return False
        
        success = self.copy_text(text)
        
        if success and show_notification:
            # Show user-friendly message
            display_text = text if len(text) <= 100 else text[:97] + "..."
            print(f"✓ Copied to clipboard: '{display_text}'")
            print("You can now paste with Ctrl+V in any application!")
        elif not success and show_notification:
            print("✗ Failed to copy text to clipboard")
        
        return success
    
    def clear_clipboard(self) -> bool:
        """
        Clear the clipboard (remove all content)
        
        This might be useful for security/privacy purposes in the future.
        """
        try:
            pyperclip.copy("")  # Copy empty string to clear clipboard
            self.logger.info("Clipboard cleared")
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to clear clipboard: {e}")
            return False
    
    def get_active_window_handle(self) -> Optional[int]:
        """
        Get the handle of the currently active window
        
        Returns:
        - Window handle (HWND) as integer, or None if Windows API unavailable
        """
        if not WINDOWS_API_AVAILABLE:
            self.logger.warning("Windows API not available for getting active window")
            return None
            
        try:
            hwnd = win32gui.GetForegroundWindow()
            if hwnd:
                window_title = win32gui.GetWindowText(hwnd)
                self.logger.info(f"Active window: '{window_title}' (handle: {hwnd})")
                return hwnd
            else:
                self.logger.warning("No active window found")
                return None
        except Exception as e:
            self.logger.error(f"Failed to get active window handle: {e}")
            return None
    
    def auto_paste_text(self, text: str) -> bool:
        """
        Automatically paste text into the active application using Windows API
        
        Parameters:
        - text: The text to paste
        
        Returns:
        - True if successful, False if failed
        
        This method copies text to clipboard and then sends a WM_PASTE message
        directly to the active window, bypassing keyboard simulation.
        """
        if not WINDOWS_API_AVAILABLE:
            self.logger.error("Windows API not available for auto-paste")
            return False
            
        if not text:
            self.logger.warning("Attempted to auto-paste empty text")
            return False
        
        try:
            # First, copy text to clipboard
            if not self.copy_text(text):
                self.logger.error("Failed to copy text to clipboard for auto-paste")
                return False
            
            # Get the active window handle
            hwnd = self.get_active_window_handle()
            if not hwnd:
                self.logger.error("No active window available for auto-paste")
                return False
            
            # Send WM_PASTE message directly to the active window
            self.logger.info(f"Sending WM_PASTE to window handle: {hwnd}")
            result = win32gui.SendMessage(hwnd, win32con.WM_PASTE, 0, 0)
            
            # Note: SendMessage return value doesn't reliably indicate success for WM_PASTE
            # We'll assume success if no exception was thrown
            self.logger.info("Auto-paste command sent successfully")
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to auto-paste text: {e}")
            return False
    
    def copy_and_paste(self, text: str, show_notification: bool = True) -> bool:
        """
        Copy text to clipboard and automatically paste it using Windows API
        
        Parameters:
        - text: Text to copy and paste
        - show_notification: Whether to print status messages
        
        Returns:
        - True if both copy and paste succeeded, False otherwise
        
        This is the main method for auto-paste functionality.
        """
        if not text:
            if show_notification:
                print("No text to copy and paste!")
            return False
        
        # First attempt auto-paste
        success = self.auto_paste_text(text)
        
        if success and show_notification:
            display_text = text if len(text) <= 100 else text[:97] + "..."
            print(f"✓ Auto-pasted: '{display_text}'")
            print("Text has been inserted directly into the active application!")
        elif not success:
            if show_notification:
                print("❌ Auto-paste failed, text remains in clipboard for manual paste")
            # Text is already in clipboard from auto_paste_text attempt
        
        return success
    
    def get_clipboard_info(self) -> dict:
        """
        Get information about current clipboard state (for debugging)
        
        Returns a dictionary with clipboard information.
        """
        try:
            content = pyperclip.paste()
            info = {
                "has_content": bool(content),
                "content_length": len(content) if content else 0,
                "preview": content[:50] + "..." if content and len(content) > 50 else content,
                "windows_api_available": WINDOWS_API_AVAILABLE
            }
            
            # Add active window info if Windows API is available
            if WINDOWS_API_AVAILABLE:
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
                "windows_api_available": WINDOWS_API_AVAILABLE
            }