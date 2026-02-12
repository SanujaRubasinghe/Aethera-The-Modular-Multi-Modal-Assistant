from handlers.base_handler import BaseHandler
from controllers.task_dispatcher import TaskResult
from state.assistant_state import AppProcess

import subprocess
import time
from datetime import datetime

from os_control.win32_window import get_main_window_for_pid
import psutil

class OpenAppHandler(BaseHandler):
    INTENT_NAME = "OPEN_APP"

    def handle(self, intent, state, permission_manager):
        app_name = intent.slots.get("app_name")
        app_type = intent.slots.get("type")

        if not app_name or not app_type:
            return TaskResult(False, "Invalid app details")
        
        if app_type == "exe":
            path = intent.slots.get("path")
            if not path:
                return TaskResult(False, "Executable path missing")
            
            try:
                proc = subprocess.Popen(path)
            except Exception as e:
                return TaskResult(False, f"Failed to open {app_name}")
            
            hwnd = self._wait_for_window(proc.pid)

            app = AppProcess(
                name=app_name,
                pid=proc.pid,
                exe_path=path,
                opened_at=datetime.now(),
                hwnd=hwnd,
                focused=True
            )
            state.register_app(app)
            return TaskResult(True, f"{app_name} opened successfully")
        
        if app_type == "uwp":
            aumid = intent.slots.get("aumid")
            if not aumid:
                return TaskResult(False, "UWP app id missing")
            
            subprocess.Popen(
                ["explorer.exe", f"shell:AppsFolder\\{aumid}"],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL
            )

            pid = self._find_new_process_pid(app_name)
            hwnd = self._wait_for_window(pid) if pid else None

            if not pid:
                return TaskResult(True, f"{app_name} opened")
            
            app = AppProcess(
                name=app_name,
                pid=pid,
                exe_path=aumid,
                opened_at=datetime.now(),
                hwnd=hwnd,
                focused=True
            )
            state.register_app(app)
            return TaskResult(True, f"{app_name} opened successfully")
        return TaskResult(False, "Unsupported application type")
    
    def _wait_for_window(self, pid: int, timeout=2.0):
        end = time.time() + timeout
        while time.time() < end:
            hwnd = get_main_window_for_pid(pid)
            if hwnd:
                return hwnd
            time.sleep(0.1)
        return None
    
    def _find_new_process_pid(self, app_name: str, timeout=3.0):
        end = time.time() + timeout
        name = app_name.lower()

        while time.time() < end:
            for proc in psutil.process_iter(["pid", "name"]):
                try:
                    if name in proc.info["name"].lower():
                        return proc.info["pid"]
                except Exception:
                    continue
            time.sleep(0.2)
        return None