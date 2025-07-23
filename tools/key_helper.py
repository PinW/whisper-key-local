#!/usr/bin/env python3
"""
Key Helper Utility

This utility helps you discover what key combinations to use in your config.yaml file.
It listens for any key combination you press and shows you the exact format to use.

For beginners: This is like a "key detector" - press any combination of keys and 
it will tell you what to put in your configuration file.

Usage:
    python tools/key_helper.py

Then press any key combination and it will show you the config format.
Press Ctrl+C to exit.
"""

import sys
import time
import threading
from typing import Set, List
from global_hotkeys import register_hotkeys, start_checking_hotkeys, stop_checking_hotkeys

class KeyHelper:
    """
    Interactive key combination detector for configuration setup
    
    This class listens for all possible key combinations and displays them
    in the format needed for the config.yaml file.
    """
    
    def __init__(self):
        """Initialize the key helper"""
        self.pressed_keys: Set[str] = set()
        self.is_running = False
        self.key_mappings = {
            # Modifier keys
            'control': 'ctrl',
            'shift': 'shift', 
            'alt': 'alt',
            'cmd': 'win',  # macOS command key maps to Windows key
            'meta': 'win', # Meta key maps to Windows key
            'super': 'win', # Super key maps to Windows key
            
            # Special keys
            'space': 'space',
            'return': 'enter',
            'enter': 'enter',
            'tab': 'tab',
            'escape': 'esc',
            'backspace': 'backspace',
            'delete': 'del',
            'insert': 'ins',
            'home': 'home',
            'end': 'end',
            'page_up': 'pageup',
            'page_down': 'pagedown',
            'up': 'up',
            'down': 'down',
            'left': 'left',
            'right': 'right',
            
            # Function keys
            'f1': 'f1', 'f2': 'f2', 'f3': 'f3', 'f4': 'f4',
            'f5': 'f5', 'f6': 'f6', 'f7': 'f7', 'f8': 'f8',
            'f9': 'f9', 'f10': 'f10', 'f11': 'f11', 'f12': 'f12',
            
            # Special characters and punctuation
            'grave': 'grave',
            'tilde': 'tilde', 
            '`': 'grave',
            '~': 'tilde',
            'minus': 'minus',
            'underscore': 'underscore',
            '-': 'minus',
            '_': 'underscore',
            'equal': 'equal',
            'plus': 'plus',
            '=': 'equal',
            '+': 'plus',
            'bracket_left': 'bracketleft',
            'brace_left': 'braceleft',
            '[': 'bracketleft',
            '{': 'braceleft',
            'bracket_right': 'bracketright',
            'brace_right': 'braceright',
            ']': 'bracketright',
            '}': 'braceright',
            'backslash': 'backslash',
            'pipe': 'pipe',
            '\\': 'backslash',
            '|': 'pipe',
            'semicolon': 'semicolon',
            'colon': 'colon',
            ';': 'semicolon',
            ':': 'colon',
            'quote': 'quote',
            'doublequote': 'doublequote',
            "'": 'quote',
            '"': 'doublequote',
            'comma': 'comma',
            'less': 'less',
            ',': 'comma',
            '<': 'less',
            'period': 'period',
            'greater': 'greater',
            '.': 'period',
            '>': 'greater',
            'slash': 'slash',
            'question': 'question',
            '/': 'slash',
            '?': 'question'
        }
        
        self.hotkey_bindings = []
        self._setup_comprehensive_hotkeys()
    
    def _setup_comprehensive_hotkeys(self):
        """
        Set up hotkey bindings to catch common key combinations
        
        We'll register a variety of common combinations to catch user input.
        """
        # Common modifier combinations with various keys
        modifiers = [
            ['control'],
            ['shift'], 
            ['alt'],
            ['control', 'shift'],
            ['control', 'alt'],
            ['shift', 'alt'],
            ['control', 'shift', 'alt']
        ]
        
        # Common keys to combine with modifiers
        keys = [
            # Special keys
            'space', 'enter', 'tab', 'escape', 'backspace', 'delete',
            
            # Letters
            'a', 'b', 'c', 'd', 'e', 'f', 'g', 'h', 'i', 'j', 'k', 'l', 'm',
            'n', 'o', 'p', 'q', 'r', 's', 't', 'u', 'v', 'w', 'x', 'y', 'z',
            
            # Numbers
            '1', '2', '3', '4', '5', '6', '7', '8', '9', '0',
            
            # Special characters and punctuation
            'grave', 'tilde', '`', '~',  # Tilde/grave accent key
            'minus', 'underscore', '-', '_',  # Minus/underscore
            'equal', 'plus', '=', '+',  # Equal/plus
            'bracket_left', 'brace_left', '[', '{',  # Left brackets
            'bracket_right', 'brace_right', ']', '}',  # Right brackets
            'backslash', 'pipe', '\\', '|',  # Backslash/pipe
            'semicolon', 'colon', ';', ':',  # Semicolon/colon
            'quote', 'doublequote', "'", '"',  # Quotes
            'comma', 'less', ',', '<',  # Comma/less than
            'period', 'greater', '.', '>',  # Period/greater than
            'slash', 'question', '/', '?',  # Slash/question mark
            
            # Function keys
            'f1', 'f2', 'f3', 'f4', 'f5', 'f6', 'f7', 'f8', 'f9', 'f10', 'f11', 'f12',
            
            # Arrow keys
            'up', 'down', 'left', 'right',
            
            # Navigation keys
            'home', 'end', 'page_up', 'page_down', 'insert'
        ]
        
        # Register combinations
        for modifier_combo in modifiers:
            for key in keys:
                combo = modifier_combo + [key]
                hotkey_string = ' + '.join(combo)
                
                # Create a callback that captures the current combination
                callback = self._create_callback(combo)
                self.hotkey_bindings.append([hotkey_string, None, callback, False])
        
        # Also register individual keys (no modifiers)
        for key in keys:
            callback = self._create_callback([key])
            self.hotkey_bindings.append([key, None, callback, False])
    
    def _create_callback(self, keys: List[str]):
        """
        Create a callback function for a specific key combination
        
        This is a closure that captures the key combination for the callback.
        """
        def callback():
            self._key_combination_detected(keys)
        return callback
    
    def _key_combination_detected(self, keys: List[str]):
        """
        Handle when a key combination is detected
        
        This converts the detected keys to the config format and displays them.
        """
        if not self.is_running:
            return
            
        # Convert keys to config format
        config_keys = []
        for key in keys:
            if key.lower() in self.key_mappings:
                config_keys.append(self.key_mappings[key.lower()])
            else:
                config_keys.append(key.lower())
        
        # Create config string
        config_string = '+'.join(config_keys)
        
        print(f"\n🔑 Key combination detected!")
        print(f"   Raw keys: {' + '.join(keys)}")
        print(f"   Config format: {config_string}")
        print(f"   Add this to config.yaml: combination: \"{config_string}\"")
        print("\nPress another key combination or Ctrl+C to exit...")
    
    def start(self):
        """
        Start the key helper utility
        """
        print("=" * 60)
        print("🔑 KEY HELPER UTILITY")
        print("=" * 60)
        print()
        print("This tool helps you find the right key combination for config.yaml")
        print()
        print("HOW TO USE:")
        print("1. Press any key combination you want to use as your hotkey")
        print("2. The tool will show you the exact format for config.yaml")
        print("3. Copy the 'Config format' line to your config.yaml file")
        print("4. Press Ctrl+C when you're done")
        print()
        print("EXAMPLES:")
        print("- Press Ctrl+Shift+Space → shows: ctrl+shift+space")
        print("- Press Alt+F12 → shows: alt+f12") 
        print("- Press Win+V → shows: win+v")
        print()
        print("=" * 60)
        print("Ready! Press any key combination...")
        print("=" * 60)
        
        try:
            # Register hotkeys
            register_hotkeys(self.hotkey_bindings)
            
            # Start the hotkey checker
            start_checking_hotkeys()
            self.is_running = True
            
            # Keep the program running
            while True:
                time.sleep(0.1)
                
        except KeyboardInterrupt:
            print("\n\n👋 Exiting Key Helper. Happy configuring!")
            
        except Exception as e:
            print(f"\n❌ Error: {e}")
            print("Make sure you're running this on Windows with proper permissions.")
            
        finally:
            self.stop()
    
    def stop(self):
        """
        Stop the key helper utility
        """
        self.is_running = False
        try:
            stop_checking_hotkeys()
        except:
            pass  # Ignore errors when stopping

def main():
    """
    Main function to run the key helper utility
    """
    try:
        helper = KeyHelper()
        helper.start()
    except Exception as e:
        print(f"Failed to start Key Helper: {e}")
        print("\nTroubleshooting:")
        print("1. Make sure you're running on Windows")
        print("2. Try running as Administrator if hotkeys don't work")
        print("3. Check that global-hotkeys library is installed")
        sys.exit(1)

if __name__ == "__main__":
    main()