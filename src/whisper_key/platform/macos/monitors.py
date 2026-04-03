from dataclasses import dataclass


@dataclass
class MonitorInfo:
    index: int = 0
    name: str = "Primary"
    x: int = 0
    y: int = 0
    width: int = 1920
    height: int = 1080
    work_x: int = 0
    work_y: int = 0
    work_width: int = 1920
    work_height: int = 1080
    is_primary: bool = True


def enumerate_monitors():
    return [MonitorInfo()]


def get_monitor_by_index(index):
    return MonitorInfo()


def get_primary_monitor():
    return MonitorInfo()


def get_monitor_at_cursor():
    return MonitorInfo()


def get_monitor_of_focused_window():
    return MonitorInfo()


def set_dpi_awareness():
    pass
