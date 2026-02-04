import logging
import sys
import time

from .platform import instance_lock

logger = logging.getLogger(__name__)

def guard_against_multiple_instances(app_name: str = "WhisperKeyLocal"):
    try:
        mutex_handle = instance_lock.acquire_lock(app_name)

        if mutex_handle is None:
            logger.info("Another instance detected")
            _exit_to_prevent_duplicate()
        else:
            logger.info("Primary instance acquired mutex")
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
