#!/usr/bin/env python3
"""Test script for period key detection on macOS"""

import sys
import time

from AppKit import NSEvent, NSApplication

NSKeyDownMask = 1 << 10
NSFlagsChangedMask = 1 << 12

MODIFIER_MASK = (1 << 18) | (1 << 20) | (1 << 19) | (1 << 17) | (1 << 23)

def handle_event(event):
    event_type = event.type()

    if event_type == 10:  # NSKeyDown
        key_code = event.keyCode()
        flags = event.modifierFlags() & MODIFIER_MASK
        chars = event.charactersIgnoringModifiers() or ""
        print(f"KeyDown: keycode={key_code}, char='{chars}', flags={flags:#x}")

        if key_code == 47:
            print("  >>> PERIOD KEY DETECTED!")
        if chars == '.':
            print("  >>> PERIOD CHAR DETECTED!")

    elif event_type == 12:  # NSFlagsChanged
        flags = event.modifierFlags() & MODIFIER_MASK
        print(f"FlagsChanged: flags={flags:#x}")

def main():
    print("Period hotkey test")
    print("=" * 40)
    print("Expected keycode for period: 47")
    print("Expected flag for cmd: 0x100000")
    print()
    print("Press keys to test detection...")
    print("Press Ctrl+C to exit")
    print("=" * 40)

    app = NSApplication.sharedApplication()

    mask = NSKeyDownMask | NSFlagsChangedMask
    monitor = NSEvent.addGlobalMonitorForEventsMatchingMask_handler_(mask, handle_event)

    if monitor is None:
        print("ERROR: Failed to create monitor!")
        print("Check Accessibility permissions in System Settings")
        sys.exit(1)

    print("Monitor started successfully")
    print()

    try:
        while True:
            time.sleep(0.1)
    except KeyboardInterrupt:
        print("\nStopping...")
        NSEvent.removeMonitor_(monitor)

if __name__ == "__main__":
    main()
