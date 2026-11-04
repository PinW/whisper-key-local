import ctypes
import uuid

import sounddevice as sd


DEFAULT_HOST = 'Windows WASAPI'
DEFAULT_SOURCES = {
    'default_input': 'System default input',
    'default_output': 'System default output',
}


def _device_endpoint_id(library, device_index):
    device = ctypes.c_void_p()
    result = library.PaWasapi_GetIMMDevice(device_index, ctypes.byref(device))
    if result < 0:
        raise OSError(f'Could not identify audio endpoint: {result}')
    vtable = ctypes.cast(device, ctypes.POINTER(ctypes.POINTER(ctypes.c_void_p))).contents
    get_id = ctypes.WINFUNCTYPE(ctypes.c_long, ctypes.c_void_p, ctypes.POINTER(ctypes.c_void_p))(vtable[5])
    endpoint_id = ctypes.c_void_p()
    result = get_id(device, ctypes.byref(endpoint_id))
    if result < 0:
        raise OSError(f'Could not read audio endpoint ID: {result}')
    ole32 = ctypes.OleDLL('ole32')
    ole32.CoTaskMemFree.argtypes = [ctypes.c_void_p]
    ole32.CoTaskMemFree.restype = None
    try:
        return ctypes.wstring_at(endpoint_id)
    finally:
        ole32.CoTaskMemFree(endpoint_id)


def resolve_default_device(source_mode, devices, hosts):
    host_index = next((index for index, host in enumerate(hosts) if host['name'] == DEFAULT_HOST), None)
    if host_index is None:
        return -1
    host = hosts[host_index]
    if source_mode == 'default_input':
        return host['default_input_device']
    if source_mode != 'default_output':
        return -1
    output_index = host['default_output_device']
    if output_index < 0:
        return -1
    library = ctypes.CDLL(sd._libname)
    library.PaWasapi_GetIMMDevice.argtypes = [ctypes.c_int, ctypes.POINTER(ctypes.c_void_p)]
    library.PaWasapi_GetIMMDevice.restype = ctypes.c_int
    library.PaWasapi_IsLoopback.argtypes = [ctypes.c_int]
    library.PaWasapi_IsLoopback.restype = ctypes.c_int
    output_endpoint = _device_endpoint_id(library, output_index)
    for index, device in enumerate(devices):
        if device['hostapi'] != host_index or device['max_input_channels'] <= 0:
            continue
        if library.PaWasapi_IsLoopback(index) == 1 and _device_endpoint_id(library, index) == output_endpoint:
            return index
    return -1


class Guid(ctypes.Structure):
    _fields_ = [
        ('data1', ctypes.c_uint32),
        ('data2', ctypes.c_uint16),
        ('data3', ctypes.c_uint16),
        ('data4', ctypes.c_ubyte * 8),
    ]

    @classmethod
    def from_string(cls, value):
        return cls.from_buffer_copy(uuid.UUID(value).bytes_le)


class PropertyKey(ctypes.Structure):
    _fields_ = [('format_id', Guid), ('property_id', ctypes.c_uint32)]


class NotificationClient(ctypes.Structure):
    _fields_ = [('vtable', ctypes.POINTER(ctypes.c_void_p))]


class DeviceChangeMonitor:
    def __init__(self, on_change, on_default_change):
        self.on_change = on_change
        self.on_default_change = on_default_change
        self._enumerator = ctypes.c_void_p()
        self._registered = False
        self._com_initialized = False
        self._references = 1
        self._unknown_id = Guid.from_string('00000000-0000-0000-c000-000000000046')
        self._notification_id = Guid.from_string('7991eec9-7e89-4d85-8390-6c703cec60c0')
        self._ole32 = ctypes.OleDLL('ole32')
        self._ole32.CoInitialize.argtypes = [ctypes.c_void_p]
        self._ole32.CoCreateInstance.argtypes = [
            ctypes.POINTER(Guid), ctypes.c_void_p, ctypes.c_uint32,
            ctypes.POINTER(Guid), ctypes.POINTER(ctypes.c_void_p),
        ]
        self._ole32.CoUninitialize.argtypes = []
        self._ole32.CoUninitialize.restype = None
        callback = ctypes.WINFUNCTYPE
        self._callbacks = (
            callback(ctypes.c_long, ctypes.c_void_p, ctypes.POINTER(Guid), ctypes.POINTER(ctypes.c_void_p))(self._query_interface),
            callback(ctypes.c_ulong, ctypes.c_void_p)(self._add_ref),
            callback(ctypes.c_ulong, ctypes.c_void_p)(self._release),
            callback(ctypes.c_long, ctypes.c_void_p, ctypes.c_wchar_p, ctypes.c_uint32)(self._changed),
            callback(ctypes.c_long, ctypes.c_void_p, ctypes.c_wchar_p)(self._changed),
            callback(ctypes.c_long, ctypes.c_void_p, ctypes.c_wchar_p)(self._changed),
            callback(ctypes.c_long, ctypes.c_void_p, ctypes.c_int, ctypes.c_int, ctypes.c_wchar_p)(self._default_changed),
            callback(ctypes.c_long, ctypes.c_void_p, ctypes.c_wchar_p, PropertyKey)(self._property_changed),
        )
        self._vtable = (ctypes.c_void_p * len(self._callbacks))(
            *(ctypes.cast(function, ctypes.c_void_p) for function in self._callbacks)
        )
        self._client = NotificationClient(self._vtable)

    def _query_interface(self, instance, interface_id, result):
        result[0] = None
        if bytes(interface_id.contents) not in (bytes(self._unknown_id), bytes(self._notification_id)):
            return -2147467262
        result[0] = ctypes.addressof(self._client)
        self._add_ref(instance)
        return 0

    def _add_ref(self, instance):
        self._references += 1
        return self._references

    def _release(self, instance):
        self._references -= 1
        return self._references

    def _changed(self, *arguments):
        self.on_change()
        return 0

    def _default_changed(self, instance, flow, role, device_id):
        if role == 1 and flow in (0, 1):
            self.on_default_change('default_input' if flow == 1 else 'default_output')
        return 0

    def _property_changed(self, instance, device_id, property_key):
        friendly_name = Guid.from_string('a45c254e-df1c-4efd-8020-67d146a850e0')
        if bytes(property_key.format_id) == bytes(friendly_name) and property_key.property_id == 14:
            self.on_change()
        return 0

    def _enumerator_method(self, index, *argument_types):
        vtable = ctypes.cast(self._enumerator, ctypes.POINTER(ctypes.POINTER(ctypes.c_void_p))).contents
        return ctypes.WINFUNCTYPE(ctypes.c_long, ctypes.c_void_p, *argument_types)(vtable[index])

    def start(self):
        if self._registered:
            return
        try:
            self._ole32.CoInitialize(None)
            self._com_initialized = True
            class_id = Guid.from_string('bcde0395-e52f-467c-8e3d-c4579291692e')
            enumerator_id = Guid.from_string('a95664d2-9614-4f35-a746-de8db63617e6')
            self._ole32.CoCreateInstance(
                ctypes.byref(class_id), None, 1, ctypes.byref(enumerator_id), ctypes.byref(self._enumerator)
            )
            result = self._enumerator_method(6, ctypes.c_void_p)(self._enumerator, ctypes.byref(self._client))
            if result < 0:
                raise OSError(f'Could not register audio device notifications: {result}')
            self._registered = True
        except Exception:
            self.stop()
            raise

    def stop(self):
        if self._registered:
            result = self._enumerator_method(7, ctypes.c_void_p)(self._enumerator, ctypes.byref(self._client))
            if result < 0:
                raise OSError(f'Could not unregister audio device notifications: {result}')
            self._registered = False
        if self._enumerator:
            self._enumerator_method(2)(self._enumerator)
            self._enumerator = ctypes.c_void_p()
        if self._com_initialized:
            self._ole32.CoUninitialize()
            self._com_initialized = False
