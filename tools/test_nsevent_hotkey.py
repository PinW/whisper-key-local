#!/usr/bin/env python3
"""
Test script for NSEvent-based hotkey detection on macOS.
Tests the real app's hotkey configuration.

Requires Accessibility permissions in System Settings > Privacy & Security > Accessibility.

Usage:
    python tools/test_nsevent_hotkey.py
"""

import sys
import signal
import logging

logging.basicConfig(level=logging.DEBUG, format='%(name)s: %(message)s')

if sys.platform != 'darwin':
    print("This script only works on macOS")
    sys.exit(1)

from AppKit import NSApplication, NSApplicationActivationPolicyAccessory, NSEventMaskAny, NSDefaultRunLoopMode
from Foundation import NSDate

app = NSApplication.sharedApplication()
app.setActivationPolicy_(NSApplicationActivationPolicyAccessory)

sys.path.insert(0, 'src')
from whisper_key.platform.macos import hotkeys

def on_recording_press():
    print("\n✓ RECORDING HOTKEY pressed (ctrl+option)")

def on_recording_release():
    print("✓ RECORDING HOTKEY released")

def on_fn_ctrl_press():
    print("\n✓ FN+CTRL pressed (alternative recording hotkey)")

def on_fn_ctrl_release():
    print("✓ FN+CTRL released")

def on_option_press():
    print("\n✓ OPTION pressed (auto-enter)")

def on_option_release():
    print("✓ OPTION released")

def on_ctrl_press():
    print("\n✓ CTRL pressed (stop-modifier)")

def on_ctrl_release():
    print("✓ CTRL released")

def on_escape_press():
    print("\n✓ ESCAPE pressed (cancel)")

running = True

def main():
    global running
    print("=" * 60)
    print("NSEvent Hotkey Test - Real App Configuration")
    print("=" * 60)
    print()
    print("Testing the following hotkeys:")
    print("  - Ctrl+Option  : Toggle recording (modifier-only)")
    print("  - Fn+Ctrl      : Alternative recording (modifier-only)")
    print("  - Option       : Auto-enter stop (modifier-only)")
    print("  - Ctrl         : Stop-modifier (modifier-only)")
    print("  - Escape       : Cancel recording (traditional)")
    print()
    print("Press Ctrl+C to exit")
    print("=" * 60)
    print()

    bindings = [
        ["control + option", on_recording_press, on_recording_release, False],
        ["fn + control", on_fn_ctrl_press, on_fn_ctrl_release, False],
        ["option", on_option_press, on_option_release, False],
        ["control", on_ctrl_press, on_ctrl_release, False],
        ["escape", on_escape_press, None, False],
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
