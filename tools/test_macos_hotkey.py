#!/usr/bin/env python3
"""
Standalone macOS hotkey test (Phase 1 of hotkey implementation).

Tests QuickMacHotKey with two hotkey styles:
  1. ctrl+cmd (modifier-only style, like Windows ctrl+win)
  2. ctrl+option+space (traditional style with regular key)

Usage: python tools/test_macos_hotkey.py
Press Ctrl+Cmd or Ctrl+Option+Space to test. Ctrl+C to quit.
"""
import signal
import sys

try:
    from AppKit import NSApplication, NSApplicationActivationPolicyAccessory, NSEventMaskAny, NSDefaultRunLoopMode
    from Foundation import NSDate, NSObject
    from quickmachotkey import quickHotKey, mask
    from quickmachotkey.constants import kVK_Space, controlKey, optionKey
except ImportError as e:
    print(f"Import error: {e}")
    print("This script requires macOS with: pip install quickmachotkey pyobjc-framework-Cocoa")
    sys.exit(1)

running = True

def signal_handler(sig, frame):
    global running
    print("\nShutting down...")
    running = False

signal.signal(signal.SIGINT, signal_handler)

class AppDelegate(NSObject):
    def applicationSupportsSecureRestorableState_(self, app):
        return True

# Virtual key code for Command key (used as "regular key" not modifier)
kVK_Command = 0x37

# Test 1: Modifier-only style (ctrl + cmd, like Windows ctrl+win)
@quickHotKey(virtualKey=kVK_Command, modifierMask=mask(controlKey))
def on_ctrl_cmd():
    print(">>> Hotkey 1 pressed! (Ctrl+Cmd) - modifier-only style")

# Test 2: Traditional style with regular key (ctrl + option + space)
@quickHotKey(virtualKey=kVK_Space, modifierMask=mask(controlKey, optionKey))
def on_ctrl_option_space():
    print(">>> Hotkey 2 pressed! (Ctrl+Option+Space) - traditional style")

def main():
    print("macOS Hotkey Test")
    print("-" * 50)
    print("Testing two hotkey styles:")
    print("  1. Ctrl+Cmd           (modifier-only, like Windows Ctrl+Win)")
    print("  2. Ctrl+Option+Space  (traditional with regular key)")
    print()
    print("Press either hotkey to test detection.")
    print("Press Ctrl+C to quit.")
    print("-" * 50)

    app = NSApplication.sharedApplication()
    app.setActivationPolicy_(NSApplicationActivationPolicyAccessory)
    delegate = AppDelegate.alloc().init()
    app.setDelegate_(delegate)

    print("Event loop running...")

    while running:
        event = app.nextEventMatchingMask_untilDate_inMode_dequeue_(
            NSEventMaskAny,
            NSDate.dateWithTimeIntervalSinceNow_(0.1),
            NSDefaultRunLoopMode,
            True
        )
        if event:
            app.sendEvent_(event)

    print("Done.")

if __name__ == "__main__":
    main()
