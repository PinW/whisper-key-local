import threading
import sys
import os

def setup():
    pass

def run_event_loop(shutdown_event):
    while not shutdown_event.wait(timeout=0.1):
        pass

def getch():
    import termios
    import tty
    fd = sys.stdin.fileno()
    if not os.isatty(fd):
        return '2'  # Default to "Skip for now" in non-interactive environments
    old_settings = termios.tcgetattr(fd)
    try:
        tty.setraw(fd)
        ch = sys.stdin.read(1)
    finally:
        termios.tcsetattr(fd, termios.TCSADRAIN, old_settings)
    return ch