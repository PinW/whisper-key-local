"""
Utility functions for the Whisper Key application.

This module contains common utility functions that are used across multiple
components of the application to maintain consistency and reduce code duplication.
"""

from contextlib import contextmanager


def beautify_hotkey(hotkey_string: str) -> str:
    """
    Format a hotkey string for display to users.
    
    Converts hotkey combinations to a consistent, user-friendly format by:
    - Replacing '+' separators with '+' for better readability
    - Converting to uppercase for consistency
    
    Args:
        hotkey_string (str): The hotkey combination string (e.g., "ctrl+`" or "shift+f1")
    
    Returns:
        str: Formatted hotkey string for display (e.g., "CTRL+`" or "SHIFT+F1")
    
    Examples:
        >>> beautify_hotkey("ctrl+`")
        'CTRL+`'
        >>> beautify_hotkey("shift+f1")
        'SHIFT+F1'
        >>> beautify_hotkey("alt+space")
        'ALT+SPACE'
    """
    if not hotkey_string:
        return ""
    
    return hotkey_string.replace('+', '+').upper()


@contextmanager
def error_logging(context: str, logger):
    """
    Context manager for consistent error handling and logging across the application.
    
    This provides a clean way to wrap risky operations with standardized error logging
    without cluttering the main code logic. Use this for operations that might fail
    and need consistent error reporting.
    
    Args:
        context (str): Description of what operation is being attempted (for error messages)
        logger: Logger instance to use for error reporting
        
    Usage:
        with error_logging("standard hotkey", self.logger):
            self.state_manager.toggle_recording()  # The risky operation
            
    For beginners: This is a "context manager" - it runs code before and after your
    operation, automatically catching any errors and logging them in a consistent format.
    """
    try:
        yield
    except Exception as e:
        logger.error(f"Error in {context}: {e}")