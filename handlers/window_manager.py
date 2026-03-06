import win32gui
import win32process
import win32api
import pygetwindow as gw
import screeninfo
import ctypes
from ctypes import wintypes
from handlers.base_handler import BaseHandler
from controllers.task_dispatcher import TaskResult

user32 = ctypes.windll.user32

class RECT(ctypes.Structure):
    _fields_ = [
        ("left", ctypes.c_long),
        ("top", ctypes.c_long),
        ("right", ctypes.c_long),
        ("bottom", ctypes.c_long),
    ]

class WindowManagerHandler(BaseHandler):
    INTENT_NAME = "MOVE_WINDOW" # Handled via slots for direction or specific intents

    def handle(self, intent, state, permission_manager):
        direction = intent.slots.get("direction")
        
        # Get monitors from state or system
        monitors = screeninfo.get_monitors()
        if not monitors:
            return TaskResult(False, "No monitors detected.")

        # Logic to decide monitor index based on direction
        # Simple implementation: 0 for left, 1 for right if 2 monitors exist
        if len(monitors) < 2:
            return TaskResult(False, "Window moving requires at least two monitors.")

        monitor_index = 1 if direction == "left" else 0
        
        try:
            self._move_window_to_monitor(monitor_index)
            return TaskResult(True, f"Moved window to {'left' if monitor_index == 0 else 'right'} monitor.")
        except Exception as e:
            return TaskResult(False, f"Failed to move window: {str(e)}")

    def _get_foreground_window_info(self):
        hwnd = win32gui.GetForegroundWindow()
        if not hwnd:
            return None
        
        _, pid = win32process.GetWindowThreadProcessId(hwnd)
        title = win32gui.GetWindowText(hwnd)

        return {
            "hwnd": hwnd,
            "pid": pid,
            "title": title
        }

    def _get_monitor_work_areas(self):
        monitors = []

        def callback(hMonitor, hdcMonitor, lprcMonitor, dwData):
            info = win32api.GetMonitorInfo(hMonitor)
            monitors.append(info["Work"]) 
            return True

        user32.EnumDisplayMonitors(
            0, 
            0, 
            ctypes.WINFUNCTYPE(ctypes.c_int, wintypes.HMONITOR, wintypes.HDC, ctypes.POINTER(RECT), wintypes.LPARAM)(callback),
            0
        )
        return monitors

    def _move_window_to_monitor(self, monitor_index):
        foreground_window = self._get_foreground_window_info()
        if not foreground_window:
            raise RuntimeError("No foreground window found.")
        
        hwnd = foreground_window["hwnd"]
        # Use pygetwindow to handle the actual movement
        window = gw.Win32Window(hwnd)

        work_areas = self._get_monitor_work_areas()
        if monitor_index >= len(work_areas):
            raise IndexError("Monitor index out of range.")
            
        left, top, right, bottom = work_areas[monitor_index]

        width = right - left
        height = bottom - top

        monitors = screeninfo.get_monitors()
        monitor = monitors[monitor_index]

        if window.isMinimized or window.isMaximized:
            window.restore()
        
        window.moveTo(monitor.x, monitor.y)
        window.resizeTo(width, height)

class WindowMoveLeftHandler(WindowManagerHandler):
    INTENT_NAME = "MOVE_WINDOW_LEFT"
    def handle(self, intent, state, permission_manager):
        intent.slots["direction"] = "left"
        return super().handle(intent, state, permission_manager)

class WindowMoveRightHandler(WindowManagerHandler):
    INTENT_NAME = "MOVE_WINDOW_RIGHT"
    def handle(self, intent, state, permission_manager):
        intent.slots["direction"] = "right"
        return super().handle(intent, state, permission_manager)
