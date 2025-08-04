#!/usr/bin/env python3
"""
Alternate Key Helper Utility (Keycode Checker)

This utility helps you discover the virtual keycodes for key combinations,
which is especially useful for non-US keyboard layouts.

Usage:
    python tools/key_helper_alt.py

Then, after confirmation, it will load the keycode checker.
Press any key combination to see its virtual keycode (VK Code).
Press Ctrl+C to exit.
"""

def main():
    """
    Main function to run the keycode checker utility.
    """
    print("=" * 60)
    print("🔑 ALTERNATE KEY HELPER (KEYCODE CHECKER)")
    print("=" * 60)
    print()
    print("This tool helps you find the virtual keycodes for your keys.")
    print("This is useful for non-US keyboards or when standard key names don't work.")
    print()
    print("HOW TO USE:")
    print("1. When prompted, type 'y' and press Enter to start.")
    print("2. Press any key or key combination.")
    print("3. The tool will show you the VK Code (virtual keycode).")
    print("4. Use this code in your config, e.g., 'ctrl+0x41' for Ctrl+A.")
    print("5. Press Ctrl+C when you're done.")
    print()

    try:
        confirm = input("Do you want to start the keycode checker? (y/n): ")
        if confirm.lower() == 'y':
            print("\nStarting keycode checker... Press Ctrl+C to exit.")
            from global_hotkeys import keycode_checker
            # The keycode_checker module, when imported, starts listening.
            # We need to keep the script alive.
            import time
            while True:
                time.sleep(1)
        else:
            print("\nExiting without starting the checker.")
    except KeyboardInterrupt:
        print("\n\n👋 Exiting Keycode Helper. Happy configuring!")
    except ImportError:
        print("\n❌ Error: Could not import 'keycode_checker' from 'global_hotkeys'.")
        print("Please ensure the 'global-hotkeys' package is installed correctly.")
    except Exception as e:
        print(f"\n❌ An unexpected error occurred: {e}")

if __name__ == "__main__":
    main()
