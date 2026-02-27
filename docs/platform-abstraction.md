## Structure

```
platform/
├── __init__.py        # sets `IS_MACOS` / `IS_WINDOWS` and imports
└── {macos,windows}/
    ├── assets/        # platform-specific assets
    └── *.py           # modules (mirrored API)
```

Module Contract:
- Mirrored with identical API (no-ops OK)
- Imported in `__init__.py`
- No-op stubs are valid when a platform doesn't need the functionality 

## Usage

```python
from .platform import keyboard, hotkeys, app, paths, icons  # prefer
from .platform import IS_MACOS, IS_WINDOWS  # sparingly
```
