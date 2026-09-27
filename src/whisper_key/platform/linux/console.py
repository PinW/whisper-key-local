import sys
import os

def setup():
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')


def owns_console():
    return False


def hide():
    pass


def show():
    pass


def is_minimized():
    return False


def start_minimize_monitor(on_minimize):
    pass