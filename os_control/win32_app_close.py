import psutil
import win32gui
import win32con
from policies.app_safety_policy import is_safe_to_close

def close_app_gracefully(pid: int, hwnd: int | None, 
                         app_name: str | None = None, 
                         timeout = 3) -> bool:
    try:
        proc = psutil.Process(pid)
        process_name = proc.name()

        if not is_safe_to_close(process_name, app_name):
            return False
        
        # try graceful window close
        if hwnd and win32gui.IsWindow(hwnd):
            win32gui.PostMessage(hwnd, win32con.WM_CLOSE, 0, 0)

            try:
                proc.wait(timeout=timeout)
                return True
            except psutil.TimeoutExpired:
                pass

        # Force terminate only if still alive
        proc.terminate()
        proc.wait(timeout=timeout)
        return True
    except (psutil.NoSuchProcess, psutil.AccessDenied):
        return False
