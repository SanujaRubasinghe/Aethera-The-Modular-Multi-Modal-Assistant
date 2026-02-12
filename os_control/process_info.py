import psutil
import os

def get_process_info(pid: int):
    try:
        p = psutil.Process(pid)
        exe = p.exe()
        name = os.path.splitext(os.path.basename(exe))[0]
        return name, exe
    except Exception:
        return None, None
