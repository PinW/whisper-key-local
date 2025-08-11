"""
Single Instance Manager for Windows Applications

Simple, clean single-instance detection using Windows mutex.
"""

import logging
import sys
import time
import win32api
import win32event
import win32gui

logger = logging.getLogger(__name__)

def guard_against_multiple_instances(app_name: str = "WhisperKeyLocal"):
    """
    Ensure only one instance is running. If duplicate detected, focus existing and exit.
    
    This is designed to be called once at app startup before main() runs.
    """
    mutex_name = f"{app_name}_SingleInstance"
    
    try:
        # Try to create named mutex
        mutex_handle = win32event.CreateMutex(None, True, mutex_name)
        
        # Check if mutex already existed (another instance running)
        if win32api.GetLastError() == 183:  # ERROR_ALREADY_EXISTS
            logger.info("Another instance detected")
            _show_duplicate_message_and_exit()
        else:
            logger.info("Primary instance acquired mutex")
            # Return the mutex handle so it stays alive until app exits
            return mutex_handle
            
    except Exception as e:
        logger.error(f"Error with single instance check: {e}")
        # On error, allow app to continue (better than crashing)
        return None

def _show_duplicate_message_and_exit():
    """Show user-friendly message, try to focus existing window, and exit."""
    print("\n" + "="*50)
    print("🚫 Whisper Key is already running!")
    print("="*50)
    print()
    print("Only one instance can run at a time.")
    
    # Try to focus existing console window
    try:
        def enum_handler(hwnd, results):
            if win32gui.IsWindowVisible(hwnd):
                class_name = win32gui.GetClassName(hwnd)
                title = win32gui.GetWindowText(hwnd)
                
                # Look for console windows with relevant titles
                if (class_name == "ConsoleWindowClass" and 
                    any(keyword in title.lower() for keyword in ["whisper", "python"])):
                    results.append(hwnd)
            return True
        
        windows = []
        win32gui.EnumWindows(enum_handler, windows)
        
        if windows:
            # Focus the first matching window
            hwnd = windows[0]
            win32gui.ShowWindow(hwnd, 9)  # SW_RESTORE
            win32gui.SetForegroundWindow(hwnd)
            print("✓ Focused existing instance")
        else:
            print("⚠️  Could not find existing console window")
            
    except Exception as e:
        logger.error(f"Error focusing window: {e}")
        print("⚠️  Could not focus existing instance")
    
    print("\nThis window will close in 3 seconds...")
    
    # Countdown
    for i in range(3, 0, -1):
        time.sleep(1)
    
    print("\nGoodbye!")
    sys.exit(0)