from datetime import datetime
from state.assistant_state import AppProcess
from os_control.win32_window_enum import enum_visible_windows
from os_control.process_info import get_process_info

def bootstrap_existing_apps(state):
    windows = enum_visible_windows()

    for win in windows:
        pid = win["pid"]
        hwnd = win["hwnd"]

        if pid in state.opened_apps:
            continue

        name, exe = get_process_info(pid)
        if not name or not exe:
            continue

        app = AppProcess(
            name=name,
            pid=pid,
            exe_path=exe,
            opened_at=datetime.now(),
            hwnd=hwnd,
            focused=False
        )

        state.opened_apps[pid] = app
