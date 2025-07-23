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
    
    def get_clipboard_info(self) -> dict:
        """
        Get information about current clipboard state (for debugging)
        
        Returns a dictionary with clipboard information.
        """
        try:
            content = pyperclip.paste()
            return {
                "has_content": bool(content),
                "content_length": len(content) if content else 0,
                "preview": content[:50] + "..." if content and len(content) > 50 else content
            }
        except Exception as e:
            return {
                "has_content": False,
                "content_length": 0,
                "error": str(e)
            }