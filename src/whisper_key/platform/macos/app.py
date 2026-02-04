from AppKit import NSApplication, NSApplicationActivationPolicyAccessory, NSEventMaskAny, NSDefaultRunLoopMode
from Foundation import NSDate, NSObject

class AppDelegate(NSObject):
    def applicationSupportsSecureRestorableState_(self, app):
        return True

_delegate = None

def setup():
    global _delegate
    app = NSApplication.sharedApplication()
    app.setActivationPolicy_(NSApplicationActivationPolicyAccessory)
    _delegate = AppDelegate.alloc().init()
    app.setDelegate_(_delegate)

def run_event_loop(shutdown_event):
    app = NSApplication.sharedApplication()
    while not shutdown_event.is_set():
        event = app.nextEventMatchingMask_untilDate_inMode_dequeue_(
            NSEventMaskAny,
            NSDate.dateWithTimeIntervalSinceNow_(0.1),
            NSDefaultRunLoopMode,
            True
        )
        if event:
            app.sendEvent_(event)
