import win32api
import win32event

def acquire_lock(app_name: str):
    mutex_name = f"{app_name}_SingleInstance"
    mutex_handle = win32event.CreateMutex(None, True, mutex_name)

    if win32api.GetLastError() == 183:  # ERROR_ALREADY_EXISTS
        return None

    return mutex_handle

def release_lock(handle):
    pass  # Mutex is released automatically when process exits
