"""
Utility functions for the Whisper Key application.

This module contains common utility functions that are used across multiple
components of the application to maintain consistency and reduce code duplication.
"""


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