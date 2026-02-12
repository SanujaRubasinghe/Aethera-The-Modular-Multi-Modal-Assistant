from dataclasses import dataclass
from typing import Dict
import threading

@dataclass
class MonitorInfo:
    id: int
    left: int
    top: int
    width: int
    height: int
    primary: bool

class MonitorState:
    def __init__(self):
        self._lock = threading.RLock()
        self.monitors: Dict[int, MonitorInfo] = {}

    def update(self, monitors: Dict[int, MonitorInfo]):
        with self._lock:
            self.monitors = monitors

    def get_primary(self) -> MonitorInfo | None:
        for m in self.monitors.values():
            if m.primary:
                return m
        return None
    
    def get_by_id(self, monitor_id: int) -> MonitorInfo | None:
        return self.monitors.get(monitor_id)
    
    def get_all(self):
        return list(self.monitors.values())