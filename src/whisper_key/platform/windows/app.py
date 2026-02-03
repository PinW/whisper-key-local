def setup():
    pass

def run_event_loop(shutdown_event):
    while not shutdown_event.wait(timeout=0.1):
        pass
