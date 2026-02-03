#!/usr/bin/env python3
"""
Standalone test script for NSEvent-based hotkey detection on macOS.

Run this directly on macOS to test hotkey detection before integrating with the app.
Requires Accessibility permissions in System Settings > Privacy & Security > Accessibility.

Usage:
    python tools/test_nsevent_hotkey.py
"""

import sys
import signal

if sys.platform != 'darwin':
    print("This script only works on macOS")
    sys.exit(1)

from AppKit import NSApplication, NSApplicationActivationPolicyAccessory, NSEventMaskAny, NSDefaultRunLoopMode
from Foundation import NSDate

app = NSApplication.sharedApplication()
app.setActivationPolicy_(NSApplicationActivationPolicyAccessory)

sys.path.insert(0, 'src')
from whisper_key.platform.macos import hotkeys

def on_ctrl_option_press():
    print("\n✓ CTRL+OPTION pressed!")

def on_ctrl_option_release():
    print("✓ CTRL+OPTION released!")

def on_ctrl_cmd_press():
    print("\n✓ CTRL+CMD pressed!")

def on_ctrl_cmd_release():
    print("✓ CTRL+CMD released!")

def on_escape_press():
    print("\n✓ ESCAPE pressed!")

def on_ctrl_option_space_press():
    print("\n✓ CTRL+OPTION+SPACE pressed!")

running = True

def main():
    global running
    print("=" * 50)
    print("NSEvent Hotkey Test")
    print("=" * 50)
    print()
    print("Testing the following hotkeys:")
    print("  - Ctrl+Option (modifier-only, with release)")
    print("  - Ctrl+Cmd (modifier-only, with release)")
    print("  - Escape (single key)")
    print("  - Ctrl+Option+Space (traditional)")
    print()
    print("Press Ctrl+C to exit")
    print("=" * 50)
    print()

    bindings = [
        ["control + option", on_ctrl_option_press, on_ctrl_option_release, False],
        ["control + command", on_ctrl_cmd_press, on_ctrl_cmd_release, False],
        ["escape", on_escape_press, None, False],
        ["control + option + space", on_ctrl_option_space_press, None, False],
    ]

    hotkeys.register(bindings)
    hotkeys.start()

    print("Hotkey monitor started. Waiting for events...")
    print()

    def signal_handler(sig, frame):
        global running
        print("\n\nShutting down...")
        running = False

    signal.signal(signal.SIGINT, signal_handler)

    while running:
        event = app.nextEventMatchingMask_untilDate_inMode_dequeue_(
            NSEventMaskAny,
            NSDate.dateWithTimeIntervalSinceNow_(0.1),
            NSDefaultRunLoopMode,
            True
        )
        if event:
            app.sendEvent_(event)

    hotkeys.stop()

if __name__ == "__main__":
    main()
