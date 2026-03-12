"""
ProactiveEngine — lets Aethera initiate conversations without user input.

Two trigger types:
  - Scheduled:     runs at a fixed time or interval (morning brief, reminders)
  - Event-driven:  fires when a system condition is met (low battery, etc.)

Integrates with your existing response_queue — no changes to STT/TTS pipeline needed.
"""

from __future__ import annotations

import threading
import time
import queue
from dataclasses import dataclass, field
from datetime import datetime
from typing import Callable


# ─────────────────────────────────────────────
# Trigger definitions
# ─────────────────────────────────────────────

@dataclass
class ScheduledTrigger:
    """Fires at a specific time of day (HH:MM) or on an interval."""
    name: str
    prompt: str                          
    time_of_day: str | None = None      
    interval_seconds: float | None = None  
    _last_fired: str = field(default="", init=False, repr=False)  


@dataclass
class EventTrigger:
    """Fires when a condition function returns True."""
    name: str
    prompt: str                          
    condition: Callable[[], bool] = field(repr=False)  
    cooldown_seconds: float = 60.0       
    _last_fired: float = field(default=0.0, init=False, repr=False)


# ─────────────────────────────────────────────
# Proactive Engine
# ─────────────────────────────────────────────

class ProactiveEngine(threading.Thread):
    """
    Background thread that monitors triggers and pushes AETHERA-generated
    messages directly into response_queue.

    Usage in main.py:
        engine = ProactiveEngine(AETHERA=self.AETHERA, response_queue=self.response_queue,
                                 shutdown_event=self.shutdown_event)
        engine.register_defaults()
        engine.start()
    """

    POLL_INTERVAL = 10.0   

    def __init__(
        self,
        AETHERA,                
        response_queue: queue.Queue,
        shutdown_event: threading.Event,
    ):
        super().__init__(daemon=True, name="ProactiveEngine")
        self.AETHERA = AETHERA
        self.response_queue = response_queue
        self.shutdown_event = shutdown_event

        self._scheduled: list[ScheduledTrigger] = []
        self._events: list[EventTrigger] = []
        self._lock = threading.Lock()

    # ─────────────────────────────────────────
    # Registration API
    # ─────────────────────────────────────────

    def add_scheduled(self, trigger: ScheduledTrigger):
        with self._lock:
            self._scheduled.append(trigger)
        print(f"[ProactiveEngine] Scheduled trigger registered: {trigger.name}")

    def add_event(self, trigger: EventTrigger):
        with self._lock:
            self._events.append(trigger)
        print(f"[ProactiveEngine] Event trigger registered: {trigger.name}")

    def register_defaults(self):
        """Register the built-in AETHERA triggers. Call before start()."""

        # ── Morning briefing ─────────────────
        self.add_scheduled(ScheduledTrigger(
            name="morning_briefing",
            time_of_day="07:30",
            prompt=(
                "Good morning. Give the user a brief morning briefing: "
                "greet them by name, state today's date and day, and mention "
                "that you are ready for their commands. Keep it to 2 sentences."
            ),
        ))

        # ── End-of-day wrap-up ───────────────
        self.add_scheduled(ScheduledTrigger(
            name="evening_summary",
            time_of_day="18:00",
            prompt=(
                "It is end of day. Greet the user and briefly note that "
                "the workday is wrapping up. Offer to help with anything "
                "before they finish. One sentence only."
            ),
        ))

        # ── battery alert ────────────────
        self.add_event(EventTrigger(
            name="low_battery",
            condition=_is_battery_low,
            prompt=(
                "Alert the user that the system battery is low and "
                "suggest plugging in the charger. Be brief and direct."
            ),
            cooldown_seconds=300,   
        ))

        self.add_event(EventTrigger(
            name="unplugged_battery",
            condition=_is_battery_unplugged,
            prompt=(
                "Alert the user that the system battery is unplugged and "
                "suggest plugging in the charger. Be brief and direct."
            ),
            cooldown_seconds=300,
        ))

        # ── Idle check-in (every 2 hours) ────
        self.add_scheduled(ScheduledTrigger(
            name="idle_checkin",
            interval_seconds=7_200,
            prompt=(
                "The user hasn't interacted for a while. "
                "Briefly and naturally check if they need anything. "
                "One sentence only — do not be intrusive."
            ),
        ))

    # ─────────────────────────────────────────
    # Main loop
    # ─────────────────────────────────────────

    def run(self):
        print("[ProactiveEngine] RUNNING")
        while not self.shutdown_event.is_set():
            now = datetime.now()
            current_time_str = now.strftime("%H:%M")
            current_timestamp = time.time()

            with self._lock:
                scheduled = list(self._scheduled)
                events = list(self._events)

            for trigger in scheduled:
                self._check_scheduled(trigger, current_time_str, current_timestamp)

            for trigger in events:
                self._check_event(trigger, current_timestamp)

            self.shutdown_event.wait(timeout=self.POLL_INTERVAL)

        print("[ProactiveEngine] STOPPED")

    # ─────────────────────────────────────────
    # Trigger evaluation
    # ─────────────────────────────────────────

    def _check_scheduled(
        self,
        trigger: ScheduledTrigger,
        current_time_str: str,
        current_timestamp: float,
    ):
        should_fire = False

        if trigger.time_of_day:
            # Fire once per day at the given HH:MM
            today = datetime.now().strftime("%Y-%m-%d")
            if (
                current_time_str == trigger.time_of_day
                and trigger._last_fired != today
            ):
                trigger._last_fired = today
                should_fire = True

        elif trigger.interval_seconds:
            # Fire every N seconds
            elapsed = current_timestamp - float(trigger._last_fired or 0)
            if elapsed >= trigger.interval_seconds:
                trigger._last_fired = str(current_timestamp)
                should_fire = True

        if should_fire:
            self._fire(trigger.name, trigger.prompt)

    def _check_event(self, trigger: EventTrigger, current_timestamp: float):
        cooldown_passed = (current_timestamp - trigger._last_fired) >= trigger.cooldown_seconds
        if not cooldown_passed:
            return
        try:
            if trigger.condition():
                trigger._last_fired = current_timestamp
                self._fire(trigger.name, trigger.prompt)
        except Exception as e:
            print(f"[ProactiveEngine] Error checking trigger '{trigger.name}': {e}")

    # ─────────────────────────────────────────
    # Fire — ask AETHERA to generate the message
    # ─────────────────────────────────────────

    def _fire(self, name: str, prompt: str):
        print(f"[ProactiveEngine] Firing trigger: {name}")
        try:
            response = self.AETHERA.process(f"[SYSTEM TRIGGER: {name}] {prompt}")
            if response:
                self.response_queue.put(response)
        except Exception as e:
            print(f"[ProactiveEngine] AETHERA error on trigger '{name}': {e}")


# ─────────────────────────────────────────────
# Built-in condition helpers
# ─────────────────────────────────────────────

def _is_battery_low(threshold: int = 20) -> bool:
    try:
        import psutil
        bat = psutil.sensors_battery()
        return bat is not None and bat.percent < threshold and not bat.power_plugged
    except Exception:
        return False

def _is_battery_unplugged() -> bool:
    try:
        import psutil
        bat = psutil.sensors_battery()
        return bat is not None and not bat.power_plugged
    except Exception:
        return False


def make_process_crash_condition(process_name: str) -> Callable[[], bool]:
    """Returns a condition that fires if a specific process is no longer running."""
    import psutil
    _was_running = {"value": False}

    def condition() -> bool:
        running = any(p.name().lower() == process_name.lower()
                      for p in psutil.process_iter())
        if _was_running["value"] and not running:
            _was_running["value"] = False
            return True
        _was_running["value"] = running
        return False

    return condition