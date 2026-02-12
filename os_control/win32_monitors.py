import ctypes
from ctypes import wintypes
from state.monitor_state import MonitorInfo

user32 = ctypes.windll.user32

MONITORINFOF_PRIMARY = 1

class RECT(ctypes.Structure):
    _fields_ = [
        ("left", ctypes.c_long),
        ("top", ctypes.c_long),
        ("right", ctypes.c_long),
        ("bottom", ctypes.c_long),
    ]

class MONITORINFO(ctypes.Structure):
    _fields_ = [
        ("cbSize", wintypes.DWORD),
        ("rcMonitor", RECT),
        ("rcWork", RECT),
        ("dwFlags", wintypes.DWORD)
    ]

def get_connected_monitors() -> dict[int, MonitorInfo]:
    monitors = {}
    index = 0

    def enum_proc(hMonitor, hdc, lprcMonitor, dwData):
        nonlocal index
        mi = MONITORINFO()
        mi.cbSize = ctypes.sizeof(MONITORINFO)
        user32.GetMonitorInfoW(hMonitor, ctypes.byref(mi))

        rect = mi.rcMonitor
        monitors[index] = MonitorInfo(
            id=index,
            left=rect.left,
            top=rect.top,
            width=rect.right - rect.left,
            height=rect.bottom - rect.top,
            primary=bool(mi.dwFlags & MONITORINFOF_PRIMARY)
        )
        index += 1
        return 1
    
    user32.EnumDisplayMonitors(
        0, 
        0, 
        ctypes.WINFUNCTYPE(ctypes.c_int, wintypes.HMONITOR, wintypes.HDC, ctypes.POINTER(RECT), wintypes.LPARAM)(enum_proc),
        0
    )

    return monitors