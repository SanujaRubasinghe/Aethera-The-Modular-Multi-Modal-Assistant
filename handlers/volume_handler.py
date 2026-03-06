from handlers.base_handler import BaseHandler
from controllers.task_dispatcher import TaskResult
from os_control.win32_volume import (
    set_volume,
    increase_volume,
    decrease_volume,
    mute,
    unmute,
    get_volume
)


class VolumeHandler(BaseHandler):

    INTENT_NAMES = {
        "SET_VOLUME",
        "INCREASE_VOLUME",
        "DECREASE_VOLUME",
        "MUTE_VOLUME",
        "UNMUTE_VOLUME",
        "GET_VOLUME"
    }

    def handle(self, intent, state, permission_manager):

        intent_name = intent.name
        level = intent.slots.get("level")

        try:

            if intent_name == "SET_VOLUME":
                if level is None:
                    return TaskResult(False, "Volume level not provided")

                set_volume(int(level))
                return TaskResult(True, f"Volume set to {level}%")

            elif intent_name == "INCREASE_VOLUME":
                new_level = increase_volume()
                return TaskResult(True, f"Volume increased to {new_level}%")

            elif intent_name == "DECREASE_VOLUME":
                new_level = decrease_volume()
                return TaskResult(True, f"Volume decreased to {new_level}%")

            elif intent_name == "MUTE_VOLUME":
                mute()
                return TaskResult(True, "Volume muted")

            elif intent_name == "UNMUTE_VOLUME":
                unmute()
                return TaskResult(True, "Volume unmuted")

            elif intent_name == "GET_VOLUME":
                level = get_volume()
                return TaskResult(True, f"Current volume is {level}%")

            return TaskResult(False, "Unsupported volume command")

        except Exception as e:
            return TaskResult(False, f"Volume control failed: {str(e)}")
