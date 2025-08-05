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
from src.utils import sanitize_for_logging

try:
    import win32gui
    import win32con
    import win32clipboard
    WINDOWS_API_AVAILABLE = True
except ImportError:
    WINDOWS_API_AVAILABLE = False

try:
    import pyautogui
    KEY_SIMULATION_AVAILABLE = True
    # Configure pyautogui for better performance and safety
    pyautogui.FAILSAFE = True  # Move mouse to corner to abort
    pyautogui.PAUSE = 0.05  # Default delay between actions (will be configured from settings)
except ImportError:
    KEY_SIMULATION_AVAILABLE = False

class ClipboardManager:
    """
    A class that handles clipboard operations (copy/paste functionality)
    
    This class can put text onto the clipboard and retrieve text from it.
    """
    
    def __init__(self, config_manager=None):
        """
        Initialize the clipboard manager
        
        We'll test clipboard access when we create this object to make sure it works.
        """
        self.logger = logging.getLogger(__name__)
        self.config_manager = config_manager
        self._configure_pyautogui_timing()
        self._test_clipboard_access()
    
    def _configure_pyautogui_timing(self):
        """Configure PyAutoGUI timing based on user settings"""
        if not KEY_SIMULATION_AVAILABLE:
            return
            
        if self.config_manager:
            try:
                hotkey_config = self.config_manager.get_hotkey_config()
                key_simulation_delay = hotkey_config.get('key_simulation_delay', 0.05)
                pyautogui.PAUSE = key_simulation_delay
                self.logger.info(f"Set PyAutoGUI PAUSE to {key_simulation_delay}s from user config")
            except Exception as e:
                self.logger.warning(f"Could not get config, using default PyAutoGUI timing: {e}")
    
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
            time.sleep(0.05)  # Small delay to ensure clipboard is updated
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
    
    def simulate_paste_keypress(self, text: str) -> bool:
        """
        Automatically paste text using keyboard simulation (Ctrl+V)
        
        Parameters:
        - text: The text to paste
        
        Returns:
        - True if successful, False if failed
        
        This method copies text to clipboard and simulates Ctrl+V keypress,
        which is compatible with most applications.
        """
        if not KEY_SIMULATION_AVAILABLE:
            self.logger.error("pyautogui not available for key simulation")
            return False
            
        if not text:
            self.logger.warning("Attempted to paste empty text via key simulation")
            return False
        
        try:
            # First, copy text to clipboard
            if not self.copy_text(text):
                self.logger.error("Failed to copy text to clipboard for key simulation")
                return False
                      
            # Simulate Ctrl+V keypress
            self.logger.info("Simulating Ctrl+V keypress")
            pyautogui.hotkey('ctrl', 'v')
            
            self.logger.info("Key simulation paste completed successfully")
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to simulate paste keypress: {e}")
            return False
    
    def copy_and_paste(self, text: str, paste_method: str = "key_simulation", show_notification: bool = True) -> bool:
        """
        Copy text to clipboard and automatically paste it using specified method
        
        Parameters:
        - text: Text to copy and paste
        - paste_method: Method to use ("key_simulation" or "windows_api")
        - show_notification: Whether to print status messages
        
        Returns:
        - True if both copy and paste succeeded, False otherwise
        
        This is the main method for auto-paste functionality with method selection.
        """
        if not text:
            if show_notification:
                print("No text to copy and paste!")
            return False
        
        success = False
        method_used = ""
        
        # Try the preferred method first
        if paste_method == "key_simulation":
            success = self.simulate_paste_keypress(text)
            method_used = "key simulation"
            
            # Fallback to Windows API if key simulation fails
            if not success and WINDOWS_API_AVAILABLE:
                self.logger.info("Key simulation failed, trying Windows API fallback")
                success = self.auto_paste_text(text)
                method_used = "Windows API (fallback)"
                
        elif paste_method == "windows_api":
            success = self.auto_paste_text(text)
            method_used = "Windows API"
            
            # Fallback to key simulation if Windows API fails
            if not success and KEY_SIMULATION_AVAILABLE:
                self.logger.info("Windows API failed, trying key simulation fallback")
                success = self.simulate_paste_keypress(text)
                method_used = "key simulation (fallback)"
        
        else:
            self.logger.error(f"Unknown paste method: {paste_method}")
            return False
        
        # Provide user feedback
        if success and show_notification:
            display_text = text if len(text) <= 100 else text[:97] + "..."
            print(f"✓ Auto-pasted via {method_used}: '{display_text}'")
        elif not success and show_notification:
            print("❌ Auto-paste failed with all methods, text remains in clipboard for manual paste")
            # Text should still be in clipboard from the copy attempts
        
        return success
    
    def preserve_and_paste(self, text: str, paste_method: str = "key_simulation", show_notification: bool = True) -> bool:
        """
        Copy text to clipboard, paste it, then restore original clipboard content
        
        Parameters:
        - text: Text to copy and paste
        - paste_method: Method to use ("key_simulation" or "windows_api")  
        - show_notification: Whether to print status messages
        
        Returns:
        - True if all operations succeeded (save original, copy, paste, restore), False otherwise
        
        This method preserves the user's existing clipboard content while pasting the transcription.
        """
        if not text:
            if show_notification:
                print("No text to copy and paste!")
            return False
        
        # Step 1: Save current clipboard content
        original_content = None
        try:
            original_content = pyperclip.paste()
            safe_content = sanitize_for_logging((original_content[:50] + '...') if original_content and len(original_content) > 50 else original_content)
            self.logger.info(f"Saved original clipboard content: '{safe_content}'")
        except Exception as e:
            self.logger.warning(f"Failed to save original clipboard content: {e}")
            # Continue anyway - we'll just warn the user
        
        # Step 2: Copy the transcription text to clipboard
        copy_success = self.copy_text(text)
        if not copy_success:
            if show_notification:
                print("❌ Failed to copy transcription to clipboard")
            return False
        
        # Step 3: Paste the transcription
        paste_success = False
        method_used = ""
        
        # Try the preferred method first
        if paste_method == "key_simulation":
            paste_success = self._paste_via_key_simulation()
            method_used = "key simulation"
            
            # Fallback to Windows API if key simulation fails
            if not paste_success and WINDOWS_API_AVAILABLE:
                self.logger.info("Key simulation failed, trying Windows API fallback")
                paste_success = self._paste_via_windows_api()
                method_used = "Windows API (fallback)"
                
        elif paste_method == "windows_api":
            paste_success = self._paste_via_windows_api()
            method_used = "Windows API"
            
            # Fallback to key simulation if Windows API fails
            if not paste_success and KEY_SIMULATION_AVAILABLE:
                self.logger.info("Windows API failed, trying key simulation fallback")
                paste_success = self._paste_via_key_simulation()
                method_used = "key simulation (fallback)"
        
        else:
            self.logger.error(f"Unknown paste method: {paste_method}")
            paste_success = False
        
        # Step 4: Restore original clipboard content (if we saved it successfully)
        restore_success = True
        if original_content is not None:
            try:
                pyperclip.copy(original_content)
                time.sleep(0.05)  # Small delay to ensure clipboard is updated
                self.logger.info("Restored original clipboard content")
            except Exception as e:
                self.logger.error(f"Failed to restore original clipboard content: {e}")
                restore_success = False
        
        # Provide user feedback
        if paste_success and show_notification:
            display_text = text if len(text) <= 100 else text[:97] + "..."
            print(f"✓ Auto-pasted via {method_used}: '{display_text}'")
            if not restore_success:
                self.logger.warning("Original clipboard content was not restored")
        elif not paste_success and show_notification:
            print("❌ Auto-paste failed with all methods")
            if original_content is not None and restore_success:
                print("✓ Original clipboard content restored")
        
        return paste_success
    
    def _paste_via_key_simulation(self) -> bool:
        """Helper method for key simulation paste (without copying first)"""
        if not KEY_SIMULATION_AVAILABLE:
            return False
            
        try:
            # PyAutoGUI PAUSE provides timing automatically
            pyautogui.hotkey('ctrl', 'v')
            self.logger.info("Executed Ctrl+V key combination")
            return True
        except Exception as e:
            self.logger.error(f"Key simulation paste failed: {e}")
            return False
    
    def _paste_via_windows_api(self) -> bool:
        """Helper method for Windows API paste (without copying first)"""
        if not WINDOWS_API_AVAILABLE:
            return False
        
        try:
            hwnd = self.get_active_window_handle()
            if not hwnd:
                self.logger.error("Could not get active window handle for paste")
                return False
            
            # Send WM_PASTE message to the active window
            win32gui.SendMessage(hwnd, win32con.WM_PASTE, 0, 0)
            self.logger.info(f"Sent WM_PASTE message to window handle {hwnd}")
            return True
        except Exception as e:
            self.logger.error(f"Windows API paste failed: {e}")
            return False
    
    def send_enter_key(self) -> bool:
        """
        Send ENTER key to the active application using key simulation
        
        Returns:
        - True if successful, False if failed
        
        This method is used by the auto-enter hotkey functionality to automatically
        submit text after pasting it (useful for chat applications and forms).
        PyAutoGUI.PAUSE provides automatic timing.
        """
        if not KEY_SIMULATION_AVAILABLE:
            self.logger.error("pyautogui not available for ENTER key simulation")
            return False
        
        try:
            # Send ENTER key press
            self.logger.info("Sending ENTER key to active application")
            pyautogui.press('enter')
            
            self.logger.info("ENTER key sent successfully")
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to send ENTER key: {e}")
            return False

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
                "windows_api_available": WINDOWS_API_AVAILABLE,
                "key_simulation_available": KEY_SIMULATION_AVAILABLE
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
                "windows_api_available": WINDOWS_API_AVAILABLE,
                "key_simulation_available": KEY_SIMULATION_AVAILABLE
            }