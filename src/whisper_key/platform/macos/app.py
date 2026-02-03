from AppKit import NSApplication, NSApplicationActivationPolicyAccessory, NSEventMaskAny, NSDefaultRunLoopMode
from Foundation import NSDate

def setup():
    app = NSApplication.sharedApplication()
    app.setActivationPolicy_(NSApplicationActivationPolicyAccessory)

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
