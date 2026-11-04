import ctypes


DEFAULT_HOST = 'Core Audio'
DEFAULT_SOURCES = {'default_input': 'System default input'}


def resolve_default_device(source_mode, devices, hosts):
    if source_mode != 'default_input':
        return -1
    host = next((host for host in hosts if host['name'] == DEFAULT_HOST), None)
    return host['default_input_device'] if host else -1


class PropertyAddress(ctypes.Structure):
    _fields_ = [
        ('selector', ctypes.c_uint32),
        ('scope', ctypes.c_uint32),
        ('element', ctypes.c_uint32),
    ]


class DeviceChangeMonitor:
    def __init__(self, on_change, on_default_change):
        self.on_change = on_change
        self.on_default_change = on_default_change
        self._core_audio = ctypes.CDLL('/System/Library/Frameworks/CoreAudio.framework/CoreAudio')
        callback_type = ctypes.CFUNCTYPE(
            ctypes.c_int32, ctypes.c_uint32, ctypes.c_uint32,
            ctypes.POINTER(PropertyAddress), ctypes.c_void_p,
        )
        self._callback = callback_type(self._changed)
        argument_types = [ctypes.c_uint32, ctypes.POINTER(PropertyAddress), callback_type, ctypes.c_void_p]
        self._core_audio.AudioObjectAddPropertyListener.argtypes = argument_types
        self._core_audio.AudioObjectAddPropertyListener.restype = ctypes.c_int32
        self._core_audio.AudioObjectRemovePropertyListener.argtypes = argument_types
        self._core_audio.AudioObjectRemovePropertyListener.restype = ctypes.c_int32
        self._addresses = []

    def _changed(self, object_id, address_count, addresses, context):
        for index in range(address_count):
            if addresses[index].selector == int.from_bytes(b'dIn ', 'big'):
                self.on_default_change('default_input')
            else:
                self.on_change()
        return 0

    def start(self):
        if self._addresses:
            return
        try:
            for selector in (b'dev#', b'dIn '):
                address = PropertyAddress(int.from_bytes(selector, 'big'), int.from_bytes(b'glob', 'big'), 0)
                result = self._core_audio.AudioObjectAddPropertyListener(1, ctypes.byref(address), self._callback, None)
                if result:
                    raise OSError(f'Could not register audio device notifications: {result}')
                self._addresses.append(address)
        except Exception:
            self.stop()
            raise

    def stop(self):
        while self._addresses:
            address = self._addresses[-1]
            result = self._core_audio.AudioObjectRemovePropertyListener(1, ctypes.byref(address), self._callback, None)
            if result:
                raise OSError(f'Could not unregister audio device notifications: {result}')
            self._addresses.pop()
