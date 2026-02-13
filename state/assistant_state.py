import threading
from typing import Dict, Optional
from dataclasses import dataclass
from datetime import datetime
from os_control.win32_window import (
    get_foreground_window_info,
    get_main_window_for_pid
)

from state.monitor_state import MonitorState

@dataclass
class AppProcess:
    name: str
    pid: int
    exe_path: str
    opened_at: datetime
    hwnd: Optional[int] = None
    focused: bool = False

class AssistantState:
    def __init__(self):
        self._lock = threading.RLock()

        self.last_intent: Optional[str] = None
        self.last_opened_app: Optional[str] = None
        self.current_focus_app: Optional[str] = None

        self.opened_apps: Dict[int, AppProcess] = {}

        self.is_listening = False
        self.is_busy = False

        self.monitors = MonitorState()

    def register_app(self, app: AppProcess):
        with self._lock:
            if not app.hwnd:
                app.hwnd = get_main_window_for_pid(app.pid)

            self.opened_apps[app.pid] = app
            self.last_opened_app = app.name
            self._set_focus_internal(app.pid)

    def unregister_app(self, pid: int):
        with self._lock:
            app = self.opened_apps.pop(pid, None)
            if app and app.name == self.current_focus_app:
                self.current_focus_app = None

    def _set_focus_internal(self, pid: int):
        for p in self.opened_apps.values():
            p.focused = False
        
        if pid in self.opened_apps:
            self.opened_apps[pid].focused = True
            self.current_focus_app = self.opened_apps[pid].name
    
    def set_focus(self, pid: int):
        with self._lock:
            self._set_focus_internal(pid)
        
    def sync_focus_from_os(self):
        with self._lock:
            info = get_foreground_window_info()
            if not info:
                return
            
            for app in self.opened_apps.values():
                app.focused = False

            app = self.opened_apps.get(info["pid"])
            if app:
                app.focused = True
                app.hwnd = info["hwnd"]
                self.current_focus_app = app.name
            else:
                self.current_focus_app = None

    def get_focused_app(self) -> Optional[AppProcess]:
        with self._lock:
            for app in self.opened_apps.values():
                if app.focused:
                    return app
            return None
        
    def get_last_opened_app(self) -> Optional[AppProcess]:
        with self._lock:
            if not self.last_opened_app:
                return None
            for app in self.opened_apps.values():
                if app.name == self.last_opened_app:
                    return app
            return None
        
    def update_intent(self, intent_name: str):
        with self._lock:
            self.last_intent = intent_name