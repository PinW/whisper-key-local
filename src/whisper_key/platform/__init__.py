import platform as _platform

_system = _platform.system()
PLATFORM = 'linux' if _system == 'Linux' else 'macos' if _system == 'Darwin' else 'windows'
IS_LINUX = PLATFORM == 'linux'
IS_MACOS = PLATFORM == 'macos'
IS_WINDOWS = PLATFORM == 'windows'

if IS_LINUX:
    from .linux import instance_lock, keyboard, hotkeys, paths, app, permissions, icons, gpu, console
elif IS_MACOS:
    from .macos import instance_lock, keyboard, hotkeys, paths, app, permissions, icons, gpu, console
else:
    from .windows import instance_lock, keyboard, hotkeys, paths, app, permissions, icons, gpu, console