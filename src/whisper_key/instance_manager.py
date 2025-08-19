import logging
import sys
import time

import win32api
import win32event

logger = logging.getLogger(__name__)

def guard_against_multiple_instances(app_name: str = "WhisperKeyLocal"):
    mutex_name = f"{app_name}_SingleInstance"
    
    try:
        mutex_handle = win32event.CreateMutex(None, True, mutex_name)
        
        if win32api.GetLastError() == 183:  # ERROR_ALREADY_EXISTS
            logger.info("Another instance detected")
            _exit_to_prevent_duplicate()
        else:
            logger.info("Primary instance acquired mutex")
            # Return the mutex handle so it stays alive until app exits
            return mutex_handle
            
    except Exception as e:
        logger.error(f"Error with single instance check: {e}")
        raise

def _exit_to_prevent_duplicate():
    print("\nWhisper Key is already running!")       
    print("\nThis app will close in 3 seconds...")
    
    for i in range(3, 0, -1):
        time.sleep(1)
    
    print("\nGoodbye!")
    sys.exit(0)