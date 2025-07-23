# Global-Hotkeys Supported Key Names

Based on the official documentation from https://github.com/btsdev/global_hotkeys

## Standard Key Names

### Modifier Keys
- `shift`
- `control` 
- `alt`
- `window`
- `left_shift`, `right_shift`
- `left_control`, `right_control`
- `left_menu`, `right_menu`

### Alphabet Keys
- `a` through `z` (lowercase)

### Number Keys
- `0` through `9`
- `numpad_0` through `numpad_9`

### Function Keys
- `f1` through `f24`

### Navigation Keys
- `backspace`
- `tab`
- `enter`
- `space`
- `escape`
- `delete`
- `home`
- `end`
- `page_up`
- `page_down`
- `left`, `up`, `right`, `down` (arrow keys)

### Punctuation/Symbol Keys (verified)
- `+`
- `,`
- `-`
- `.`
- `/`
- `;`
- `[`
- `]`
- `'` (single quote)

### Media Keys
- `volume_mute`
- `volume_down`
- `volume_up`
- `next_track`
- `previous_track`
- `stop_media`
- `play_pause_media`

### Browser Keys
- `browser_back`
- `browser_forward`
- `browser_refresh`
- `browser_stop`
- `browser_search`
- `browser_favorites`
- `browser_start_and_home`

### Application Keys
- `start_mail`
- `select_media`
- `start_application_1`
- `start_application_2`

### Other Keys
- `clear`
- `pause`
- `caps_lock`
- `num_lock`
- `scroll_lock`
- `print_screen`
- `insert`
- `help`
- `multiply_key`
- `add_key`
- `separator_key`
- `subtract_key`
- `decimal_key`
- `divide_key`

## Special Characters Notes

For special characters like backtick (`), equals (=), brackets, etc., you may need to:

1. Use the `keycode_checker` utility to find the exact keycode
2. Use the keycode directly in your binding: `"control + 0x29"` (where 0x29 is the VK code)

## Key Combination Format

- Separate keys with ` + ` (spaces around plus): `"control + shift + space"`
- Key chords use commas: `"control + 7, control + 4"`
- Case doesn't matter for most keys: `"Control + A"` same as `"control + a"`

## Platform Notes

- This library is Windows-only
- Non-US keyboard layouts may require using keycodes instead of key names
- Modifier key codes may differ on non-US layouts