import logging
import os
import sys

logger = logging.getLogger(__name__)

try:
    from ApplicationServices import AXIsProcessTrusted, AXIsProcessTrustedWithOptions
    _appservices_available = True
except ImportError:
    _appservices_available = False
    logger.warning("ApplicationServices not available - permission checks disabled")


def _get_terminal_app_name() -> str:
    term_program = os.environ.get('TERM_PROGRAM', '')
    if 'iTerm' in term_program:
        return 'iTerm'
    elif term_program == 'Apple_Terminal':
        return 'Terminal'
    elif term_program:
        return term_program.replace('.app', '')
    return 'your terminal app'


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

    app_name = _get_terminal_app_name()

    BOLD_CYAN = "\x1b[1;36m"
    DIM = "\x1b[2m"
    RESET = "\x1b[0m"

    title = "Auto-paste requires permission to simulate [Cmd+V] keypress..."
    box_width = len(title) + 4
    styled_message = f"""{BOLD_CYAN}  ┌{'─' * box_width}┐
  │  {title}  │
  └{'─' * box_width}┘{RESET}"""

    options = [
        f"Grant accessibility permission to {app_name}\n      {DIM}Transcribe directly to cursor, with option to auto-send{RESET}",
        f"Disable auto-paste\n      {DIM}Transcribe to clipboard, then manually paste{RESET}"
    ]

    choice = prompt_choice(styled_message, options)

    if choice == 0:
        request_accessibility_permission()
        print()
        print("Exiting Whisper Key... please restart after permission is granted")
        print()
        sys.exit(0)

    elif choice == 1:
        config_manager.update_user_setting('clipboard', 'auto_paste', False)
        print()
        print("Auto-paste disabled. You can re-enable it via the system tray menu.")
        print()
        return True

    else:
        print()
        sys.exit(0)
