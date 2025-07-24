# Global-Hotkeys Library Documentation

## Overview
The global-hotkeys library is a Python package for creating system-wide keyboard hotkeys on Windows. It allows developers to set global hotkey bindings that work across all applications.

## Installation
```bash
pip install global-hotkeys -U
```

## Key Features
- Set global hotkey bindings that work system-wide
- Support for complex key combinations and key chords
- Callbacks for press and release events
- Add/remove hotkeys dynamically
- Support for 100+ predefined keys

## Basic Usage

### Simple Example
```python
from global_hotkeys import *

def print_hello():
    print("Hello")

bindings = [
    ["control + 5", None, print_hello, False]
]

register_hotkeys(bindings)
start_checking_hotkeys()
```

### Binding Format
Each binding is a list with 4 elements:
```python
[key_combination, release_callback, press_callback, repeat_on_hold]
```

- `key_combination`: String like "control + shift + space"
- `release_callback`: Function to call on key release (can be None)
- `press_callback`: Function to call on key press
- `repeat_on_hold`: Boolean for whether to repeat while held

## Key Combinations
- Use `+` to separate keys with spaces: `"control + shift + space"`
- Supported modifiers: `control`, `shift`, `alt`
- Common keys: `space`, `enter`, `escape`, `tab`, etc.
- Key chords supported: `"control + 7, control + 4"`

## API Functions
- `register_hotkeys(bindings)`: Register hotkey bindings
- `start_checking_hotkeys()`: Start the hotkey listener
- `stop_checking_hotkeys()`: Stop the hotkey listener
- `clear_hotkeys()`: Remove all hotkey bindings

## Platform Support
- **Windows**: Full support
- **Linux/Mac**: Limited or no support

## Troubleshooting

### Non-US Keyboard Layouts
If your modifier keys have different keycodes, you may need to:
1. Use the `keycode_checker` utility to find correct keycodes
2. Modify the library source for your keyboard layout

### Common Issues
- Empty key combinations result in "not a valid virtual keystroke" error
- Ensure proper spacing in key combinations: `"control + space"` not `"control+space"`
- Some key combinations may conflict with system hotkeys

## License
MIT License - maintained by btsdev

## Repository
https://github.com/btsdev/global_hotkeys