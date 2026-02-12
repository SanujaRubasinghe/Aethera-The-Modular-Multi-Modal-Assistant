from handlers.base_handler import BaseHandler
from controllers.task_dispatcher import TaskResult
from os_control.screenshot import capture_monitor, capture_all_monitors
from datetime import datetime
import os

class ScreenShotHandler(BaseHandler):
    INTENT_NAME = "TAKE_SCREENSHOT"

    def handle(self, intent, state, permission_manager):
        state.monitors.update(state.monitors.monitors or {})

        slot = intent.slots.get("monitor", "primary")
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        base_path = os.path.join(os.getcwd(), "screenshots")
        os.makedirs(base_path, exist_ok=True)

        if slot == "all":
            path = os.path.join(base_path, f"screenshot_all_{timestamp}.png")
            capture_all_monitors(path)
            return TaskResult(True, "Screenshot of all monitors taken")
        
        if slot in ("primary", None):
            monitor = state.monitors.get_primary()
        else:
            try:
                monitor = state.monitors.get_by_id(int(slot))
            except:
                return TaskResult(False, "Invalid monitor specified")
        
        if not monitor:
            return TaskResult(False, "Monitor not found")
        
        path = os.path.join(base_path, f"screenshot_monitor_{monitor.id}_{timestamp}.png")
        capture_monitor(monitor, path)
        return TaskResult(True, f"Screenshot taken on monitor {monitor.id}")