import platform as _platform

PLATFORM = 'macos' if _platform.system() == 'Darwin' else 'windows'
IS_MACOS = PLATFORM == 'macos'
IS_WINDOWS = PLATFORM == 'windows'

if IS_MACOS:
    from .macos import instance_lock, console, keyboard, hotkeys, paths, app
else:
    from .windows import instance_lock, console, keyboard, hotkeys, paths, app
