import win32gui
import win32process

def get_foreground_window_info():
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

def get_main_window_for_pid(pid: int):
    result = []

    def enum_handler(hwnd, _):
        if not win32gui.IsWindowVisible(hwnd):
            return
        _, window_pid = win32process.GetWindowThreadProcessId(hwnd)
        if window_pid == pid:
            result.append(hwnd)

    win32gui.EnumWindows(enum_handler, None)
    return result[0] if result else None