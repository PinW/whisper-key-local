import msvcrt
import pythoncom


def setup():
    pass

def run_event_loop(shutdown_event, on_idle):
    while not shutdown_event.wait(timeout=0.1):
        pythoncom.PumpWaitingMessages()
        on_idle()

def getch():
    return msvcrt.getwch()
