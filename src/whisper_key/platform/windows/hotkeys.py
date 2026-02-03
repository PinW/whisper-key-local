from global_hotkeys import register_hotkeys, start_checking_hotkeys, stop_checking_hotkeys

# global-hotkeys library expects: 'control + window + shift' format
KEY_MAP = {
    'ctrl': 'control',
    'win': 'window',
    'windows': 'window',
    'cmd': 'window',
    'super': 'window',
    'esc': 'escape',
}

def _normalize_hotkey(hotkey_str: str) -> str:
    keys = hotkey_str.lower().split('+')
    converted = [KEY_MAP.get(k.strip(), k.strip()) for k in keys]
    return ' + '.join(converted)

def register(bindings: list):
    normalized = []
    for binding in bindings:
        hotkey_str = binding[0]
        normalized_binding = [_normalize_hotkey(hotkey_str)] + binding[1:]
        normalized.append(normalized_binding)
    register_hotkeys(normalized)

def start():
    start_checking_hotkeys()

def stop():
    stop_checking_hotkeys()
