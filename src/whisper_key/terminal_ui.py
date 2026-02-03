import sys

def _getch():
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
            ch = _getch()
            if ch in valid_choices:
                print(ch)
                return valid_choices[ch]
            if ch in ('\x03', '\x04'):
                print()
                return -1
        except (KeyboardInterrupt, EOFError):
            print()
            return -1
