from handlers.base_handler import BaseHandler
from controllers.task_dispatcher import TaskResult
from ui_automation.engine import UIAutomationEngine
from ui_automation.models import AutomationPlan, UIAction

class WhatsappSendHandler(BaseHandler):
    INTENT_NAME = "SEND_WHATSAPP_MESSAGE"

    def handle(self, intent, state, permission_manager):
        contact = intent.slots.get("contact")
        message = intent.slots.get("message")
        approved = False

        if not contact or not message:
            return TaskResult(False, "Missing contact or message")
        
        app = state.get_focused_app()
        if not app or "whatsapp" not in app.name.lower():
            return TaskResult(False, "Whatsapp is not focused")
        
        approved = permission_manager.request(
            action = "SEND_WHATSAPP_MESSAGE",
            app_name="whatsapp",
            reason="sending message",
            prompt=f"You're about to send a WhatsApp message to {contact}"
        )
        
        if not approved:
            return TaskResult(False, "Message sending cancelled")
        
        plan = AutomationPlan(steps=[
            UIAction(
                action="set_text",
                selector={"control_type": "Edit", "name": "Search"},
                value=contact
            ),
            UIAction(
                action="click",
                selector={"control_type": "Text", "name": contact}
            ),
            UIAction(
                action="set_text",
                selector={"control_type": "Edit", "name": "Type a message"},
                value=message
            ),
            UIAction(
                action="click",
                selector={"control_type": "Button", "name": "Send"}
            )
        ])

        UIAutomationEngine.execute(app.hwnd, plan)
        return TaskResult(True, f"Message sent to contact {contact}")