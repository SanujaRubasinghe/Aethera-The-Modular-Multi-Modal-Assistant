import cv2
import os
import json
import time
from datetime import datetime
from typing import List, Dict, Any, Optional
import numpy as np
from config.constants import (
    INTRUSION_DATA_DIR,
    INTRUSION_CAPTURE_COOLDOWN,
    INTRUSION_RETENTION_DAYS
)

class IntrusionLogger:
    def __init__(self):
        self.data_dir = INTRUSION_DATA_DIR
        self.log_file = os.path.join(self.data_dir, "intrusion_log.json")
        self._ensure_dirs()
        self.last_capture_time = 0

    def _ensure_dirs(self):
        if not os.path.exists(self.data_dir):
            os.makedirs(self.data_dir, exist_ok=True)
        if not os.path.exists(self.log_file):
            with open(self.log_file, 'w') as f:
                json.dump([], f)

    def log_intrusion(self, frame: np.ndarray):
        """Capture photo and log event if cooldown has passed."""
        current_time = time.time()
        if current_time - self.last_capture_time < INTRUSION_CAPTURE_COOLDOWN:
            return

        self.last_capture_time = current_time
        timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
        photo_filename = f"intruder_{timestamp}.jpg"
        photo_path = os.path.join(self.data_dir, photo_filename)
        try:
            # Refresh directory just in case
            if not os.path.exists(self.data_dir):
                os.makedirs(self.data_dir, exist_ok=True)
            
            # Save photo
            cv2.imwrite(photo_path, frame)
            
            # Log entry
            entry = {
                "timestamp": datetime.now().isoformat(),
                "photo_path": photo_path,
                "reviewed": False
            }
            
            with open(self.log_file, 'r+') as f:
                logs = json.load(f)
                logs.append(entry)
                f.seek(0)
                json.dump(logs, f, indent=2)
                f.truncate()
            print(f"IntrusionLogger: Logged intrusion at {timestamp}")
        except Exception as e:
            print(f"IntrusionLogger: Error saving log: {e}")


    def get_unreviewed_count(self) -> int:
        try:
            with open(self.log_file, 'r') as f:
                logs = json.load(f)
                return sum(1 for log in logs if not log.get("reviewed", False))
        except Exception as e:
            print(f"Error reading log file: {e}")
            return 0

    def mark_all_reviewed(self):
        try:
            with open(self.log_file, 'r+') as f:
                logs = json.load(f)
                for log in logs:
                    log["reviewed"] = 1
                f.seek(0)
                json.dump(logs, f, indent=2)
                f.truncate()
        except Exception as e:
            print(f"IntrusionLogger: Error marking logs reviewed: {e}")

    def clear_old_logs(self):
        # Later old records should be deleted after a set date.
        pass
