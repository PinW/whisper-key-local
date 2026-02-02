import fcntl
import os
from pathlib import Path

_lock_file = None

def acquire_lock(app_name: str):
    global _lock_file
    lock_path = Path.home() / f".{app_name}.lock"

    try:
        _lock_file = open(lock_path, 'w')
        fcntl.flock(_lock_file.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
        _lock_file.write(str(os.getpid()))
        _lock_file.flush()
        return _lock_file
    except (IOError, OSError):
        if _lock_file:
            _lock_file.close()
            _lock_file = None
        return None

def release_lock(handle):
    global _lock_file
    if handle:
        try:
            fcntl.flock(handle.fileno(), fcntl.LOCK_UN)
            handle.close()
        except:
            pass
    _lock_file = None
