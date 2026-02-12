from dataclasses import dataclass
from typing import Callable

@dataclass
class PermissionRequest:
    action: str
    app_name: str
    reason: str
    prompt: str
    timeout: float = 10.0

