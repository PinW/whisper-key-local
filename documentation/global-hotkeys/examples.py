"""
Global-Hotkeys Library Examples

These examples show various ways to use the global-hotkeys library
for system-wide keyboard shortcuts.
"""

from global_hotkeys import *
import time

# Example 1: Basic hotkey binding
def example_basic():
    """Simple hotkey that prints a message"""
    def print_hello():
        print("Hello from global hotkey!")
    
    bindings = [
        ["control + 5", None, print_hello, False]
    ]
    
    register_hotkeys(bindings)
    start_checking_hotkeys()
    
    print("Press Ctrl+5 to trigger hotkey. Press Enter to stop...")
    input()
    stop_checking_hotkeys()

# Example 2: Multiple hotkeys
def example_multiple():
    """Multiple hotkeys with different functions"""
    def func1():
        print("Function 1 triggered!")
    
    def func2():
        print("Function 2 triggered!")
    
    def func3():
        print("Function 3 triggered!")
    
    bindings = [
        ["control + 1", None, func1, False],
        ["control + 2", None, func2, False],
        ["control + shift + 3", None, func3, False]
    ]
    
    register_hotkeys(bindings)
    start_checking_hotkeys()
    
    print("Hotkeys registered:")
    print("- Ctrl+1: Function 1")
    print("- Ctrl+2: Function 2") 
    print("- Ctrl+Shift+3: Function 3")
    print("Press Enter to stop...")
    input()
    stop_checking_hotkeys()

# Example 3: Press and release callbacks
def example_press_release():
    """Hotkey with both press and release callbacks"""
    def on_press():
        print("Key pressed!")
    
    def on_release():
        print("Key released!")
    
    bindings = [
        ["control + space", on_release, on_press, False]
    ]
    
    register_hotkeys(bindings)
    start_checking_hotkeys()
    
    print("Press and hold Ctrl+Space to see press/release events")
    print("Press Enter to stop...")
    input()
    stop_checking_hotkeys()

# Example 4: Key chords (sequences)
def example_key_chords():
    """Key chord example - press Ctrl+7 then Ctrl+4"""
    def chord_triggered():
        print("Key chord Ctrl+7, Ctrl+4 completed!")
    
    bindings = [
        ["control + 7, control + 4", None, chord_triggered, False]
    ]
    
    register_hotkeys(bindings)
    start_checking_hotkeys()
    
    print("Press Ctrl+7 followed by Ctrl+4 within a few seconds")
    print("Press Enter to stop...")
    input()
    stop_checking_hotkeys()

# Example 5: Dynamic hotkey management
def example_dynamic():
    """Add and remove hotkeys dynamically"""
    def hotkey1():
        print("Hotkey 1!")
    
    def hotkey2():
        print("Hotkey 2!")
    
    # Start with first hotkey
    bindings1 = [["control + q", None, hotkey1, False]]
    register_hotkeys(bindings1)
    start_checking_hotkeys()
    
    print("Hotkey Ctrl+Q registered. Press it, then press Enter to continue...")
    input()
    
    # Add second hotkey
    bindings2 = [["control + w", None, hotkey2, False]]
    register_hotkeys(bindings2)
    
    print("Added Ctrl+W hotkey. Now both Ctrl+Q and Ctrl+W work. Press Enter to continue...")
    input()
    
    # Clear all hotkeys
    clear_hotkeys()
    print("All hotkeys cleared. They won't work now. Press Enter to exit...")
    input()
    
    stop_checking_hotkeys()

if __name__ == "__main__":
    print("Global-Hotkeys Examples")
    print("=" * 30)
    print("1. Basic hotkey")
    print("2. Multiple hotkeys")
    print("3. Press/release callbacks")
    print("4. Key chords")
    print("5. Dynamic management")
    
    choice = input("Choose example (1-5): ").strip()
    
    if choice == "1":
        example_basic()
    elif choice == "2":
        example_multiple()
    elif choice == "3":
        example_press_release()
    elif choice == "4":
        example_key_chords()
    elif choice == "5":
        example_dynamic()
    else:
        print("Invalid choice")