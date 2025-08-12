"""
Utility functions for the Whisper Key application.

This module contains common utility functions that are used across multiple
components of the application to maintain consistency and reduce code duplication.
"""

import os
from contextlib import contextmanager
from pathlib import Path


class OptionalComponent:
    """
    A wrapper for optional components that may be None.
    
    This allows calling methods on optional components without checking 
    if they exist first. If the component is None, all method calls 
    become no-ops that return None.
    """
    def __init__(self, component):
        self._component = component
    
    def __getattr__(self, name):
        if self._component and hasattr(self._component, name):
            attr = getattr(self._component, name)
            return attr
        else:
            # Return a no-op function for missing methods/attributes
            return lambda *args, **kwargs: None


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
def error_logging(context: str, logger, print_to_user: bool = True):
    """
    Context manager for consistent error handling and logging across the application.
    
    This provides a clean way to wrap risky operations with standardized error logging
    and optional user-facing error messages. Use this for operations that might fail
    and need consistent error reporting.
    
    Args:
        context (str): Description of what operation is being attempted (for error messages)
        logger: Logger instance to use for error reporting
        print_to_user (bool): Whether to print red error message to user (default: True)
        
    Usage:
        with error_logging("standard hotkey", self.logger):
            self.state_manager.toggle_recording()  # The risky operation
            
        # For internal operations that shouldn't show to user:
        with error_logging("internal cleanup", self.logger, print_to_user=False):
            self._cleanup_resources()
            
    operation, automatically catching any errors and logging them in a consistent format.
    """
    try:
        yield
    except Exception as e:
        error_message = f"Error in {context}: {e}"
        
        # Always log the technical details
        logger.error(error_message)
        
        # Optionally print user-facing error in red (same message as log)
        if print_to_user:
            print(f"\033[91m{error_message}\033[0m")



def resolve_asset_path(asset_path: str) -> str:
    """
    Resolve asset file path relative to project root for PyInstaller compatibility.
    
    This function ensures assets work in both development and bundled environments.
    (for example with PyInstaller)
    
    Args:
        asset_path (str): Path from config (may be relative or absolute)
        
    Returns:
        str: Absolute path to asset file
        
    Examples:
        >>> resolve_asset_path("assets/sounds/beep.wav")
        '/path/to/project/assets/sounds/beep.wav'  # (development)
        # or: '/tmp/_MEI123/assets/sounds/beep.wav'  # (PyInstaller bundle)
        
        >>> resolve_asset_path("/absolute/path/file.wav")
        '/absolute/path/file.wav'  # (unchanged)
    """
    if not asset_path:
        return asset_path
    
    # If already absolute, return as-is
    if os.path.isabs(asset_path):
        return asset_path
    
    # Resolve relative path using __file__ (works with PyInstaller)
    project_root = Path(__file__).parent.parent
    resolved_path = project_root / asset_path
    return str(resolved_path)