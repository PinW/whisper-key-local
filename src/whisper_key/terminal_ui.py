import sys

CYAN = "\x1b[36m"
BOLD_CYAN = "\x1b[1;36m"
DIM = "\x1b[2m"
RESET = "\x1b[0m"


def getch():
    try:
        import tty
        import termios
        fd = sys.stdin.fileno()
        old_settings = termios.tcgetattr(fd)
        try:
            tty.setraw(fd)
            ch = sys.stdin.read(1)
        finally:
            termios.tcsetattr(fd, termios.TCSADRAIN, old_settings)
        return ch
    except Exception:
        return input()[0] if input() else ''


def prompt_choice(message: str, options: list[str]) -> int:
    print()
    print(message)
    print()
    for i, option in enumerate(options, 1):
        print(f"  [{i}] {option}")
        print()
    print("Press a number to choose: ", end="", flush=True)

    valid_choices = {str(i): i - 1 for i in range(1, len(options) + 1)}

    while True:
        try:
            ch = getch()
            if ch in valid_choices:
                print(ch)
                return valid_choices[ch]
            if ch in ('\x03', '\x04'):
                print()
                return -1
        except (KeyboardInterrupt, EOFError):
            print()
            return -1


def prompt_choice_boxed(title: str, options: list[tuple[str, str]]) -> int:
    all_texts = [title]
    for main_text, desc in options:
        all_texts.append(main_text)
        if desc:
            all_texts.append("    " + desc)

    width = max(len(t) for t in all_texts) + 2

    def pad(text):
        return text + ' ' * (width - len(text))

    def line(text=""):
        return f"{CYAN}  │{RESET} {pad(text)} {CYAN}│{RESET}"

    def line_dim(text):
        return f"{CYAN}  │{RESET} {DIM}{pad(text)}{RESET} {CYAN}│{RESET}"

    print()
    print(f"{CYAN}  ┌{'─' * (width + 2)}┐{RESET}")
    print(f"{CYAN}  │{RESET} {BOLD_CYAN}{pad(title)}{RESET} {CYAN}│{RESET}")

    for i, (main_text, desc) in enumerate(options, 1):
        print(line())
        print(line(f"[{i}] {main_text}"))
        if desc:
            print(line_dim("    " + desc))

    print(f"{CYAN}  └{'─' * (width + 2)}┘{RESET}")
    print()
    print("  Press a number to choose: ", end="", flush=True)

    valid_choices = {str(i): i for i in range(1, len(options) + 1)}

    while True:
        try:
            ch = getch()
            if ch in valid_choices:
                print(ch)
                return valid_choices[ch]
            if ch in ('\x03', '\x04'):
                print()
                return -1
        except (KeyboardInterrupt, EOFError):
            print()
            return -1
