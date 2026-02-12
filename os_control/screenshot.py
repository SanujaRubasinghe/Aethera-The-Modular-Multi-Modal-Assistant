from PIL import Image
import mss
from state.monitor_state import MonitorInfo

def capture_monitor(monitor: MonitorInfo, save_path: str):
    with mss.mss() as sct:
        m = sct.monitors[2]
        screenshot = sct.grab(m)
        img = Image.frombytes("RGB", screenshot.size, screenshot.rgb)
        img.save(save_path)
        return save_path

def capture_all_monitors(save_path: str):
    with mss.mss() as sct:
        m = sct.monitors[1]
        screenshot = sct.grab(m)
        img = Image.frombytes("RGB", screenshot.size, screenshot.rgb)
        img.save(save_path)
        return save_path
    
def capture_monitor_for_screen_read():
    with mss.mss() as sct:
        m = sct.monitors[2]
        screenshot = sct.grab(m)
        img = Image.frombytes("RGB", screenshot.size, screenshot.rgb)
        return img
