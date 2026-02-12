from state.assistant_state import AssistantState

class BaseHandler:
    INTENT_NAME = None
    def handle(self, intent, state: AssistantState, permission_manager):
        raise NotImplementedError