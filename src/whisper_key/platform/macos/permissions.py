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
    from ...terminal_ui import getch

    app_name = _get_terminal_app_name()

    BOLD_CYAN = "\x1b[1;36m"
    DIM = "\x1b[2m"
    RESET = "\x1b[0m"

    title = "Auto-paste requires permission to simulate [Cmd+V] keypress..."
    opt1_main = f"[1] Grant accessibility permission to {app_name}"
    opt1_desc = "Transcribe directly to cursor, with option to auto-send"
    opt2_main = "[2] Disable auto-paste"
    opt2_desc = "Transcribe to clipboard, then manually paste"

    width = max(len(title), len(opt1_main), len(opt1_desc), len(opt2_main), len(opt2_desc)) + 4

    def pad(text):
        return text + ' ' * (width - len(text))

    print()
    print(f"{BOLD_CYAN}  ┌{'─' * width}┐")
    print(f"  │ {pad(title)} │")
    print(f"  │ {' ' * width} │")
    print(f"  │ {pad(opt1_main)} │")
    print(f"  │ {RESET}{DIM}   {pad(opt1_desc)}{RESET}{BOLD_CYAN} │")
    print(f"  │ {' ' * width} │")
    print(f"  │ {pad(opt2_main)} │")
    print(f"  │ {RESET}{DIM}   {pad(opt2_desc)}{RESET}{BOLD_CYAN} │")
    print(f"  └{'─' * width}┘{RESET}")
    print()
    print("  Press a number to choose: ", end="", flush=True)

    while True:
        ch = getch()
        if ch == '1':
            print(ch)
            choice = 0
            break
        elif ch == '2':
            print(ch)
            choice = 1
            break
        elif ch in ('\x03', '\x04'):
            print()
            choice = -1
            break

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
