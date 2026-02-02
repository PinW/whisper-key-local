from global_hotkeys import register_hotkeys, start_checking_hotkeys, stop_checking_hotkeys

def register(bindings: list):
    register_hotkeys(bindings)

def start():
    start_checking_hotkeys()

def stop():
    stop_checking_hotkeys()
