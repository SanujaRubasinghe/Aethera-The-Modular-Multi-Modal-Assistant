from __future__ import annotations
import time
import queue
from dataclasses import dataclass
from datetime import datetime
from typing import Callable

@dataclass
class ScheduledTrigger:
    name: str
    prompt: str 
    time_of_day: str | None = None 
    interval_seconds: float | None = None
    _last_fired: str = field(default="", init=False, repr=False)

@dataclass
class EventTrigger:
    name: str 
    prompt: str
    condition: Callable[[], bool] = field(repr=False)
    cooldown_seconds: float = 300.0
    _last_fired: float = field(default=0.0, init=False, repr=False)
