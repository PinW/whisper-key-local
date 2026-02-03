import logging
import sys

logger = logging.getLogger(__name__)

try:
    from ApplicationServices import AXIsProcessTrusted, AXIsProcessTrustedWithOptions
    _appservices_available = True
except ImportError:
    _appservices_available = False
    logger.warning("ApplicationServices not available - permission checks disabled")


def check_accessibility_permission() -> bool:
    if not _appservices_available:
        return True
    return AXIsProcessTrusted()


def request_accessibility_permission():
    if not _appservices_available:
        return
    options = {'AXTrustedCheckOptionPrompt': True}
    AXIsProcessTrustedWithOptions(options)


def handle_missing_permission(config_manager) -> bool:
    from ...terminal_ui import prompt_choice

    message = """\
⚠️  Auto-paste requires Accessibility permission

Your terminal app needs permission to simulate the Cmd+V keyboard shortcut.
Without it, transcribed text will be copied to clipboard only (manual paste)."""

    options = [
        "Grant permission (opens Settings, then app closes - restart after)",
        "Disable auto-paste (clipboard only, saves to config)"
    ]

    choice = prompt_choice(message, options)

    if choice == 0:
        request_accessibility_permission()
        print()
        print("Opening System Settings...")
        print("Grant Accessibility permission to your terminal app, then restart.")
        print()
        sys.exit(0)

    elif choice == 1:
        config_manager.update_user_setting('clipboard', 'auto_paste', False)
        print()
        print("Auto-paste disabled. Text will be copied to clipboard.")
        print()
        return True

    else:
        return True
