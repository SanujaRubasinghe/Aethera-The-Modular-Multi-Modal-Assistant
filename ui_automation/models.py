from dataclasses import dataclass
from typing import Optional, Dict, List

@dataclass
class UIAction:
    action: str
    selector: Dict[str, str]
    value: Optional[str] = None
    timeout_ms: int = 3000

@dataclass
class AutomationPlan:
    steps: List[UIAction]
    rollback_on_failure: bool = True