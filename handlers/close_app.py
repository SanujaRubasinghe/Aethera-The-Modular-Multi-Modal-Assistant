from handlers.base_handler import BaseHandler
from os_control.win32_app_close import close_app_gracefully
from controllers.task_dispatcher import TaskResult
from permissions.permission_request import PermissionRequest
from policies.unsaved_app_policy import may_have_unsaved_data

class CloseAppHandler(BaseHandler):
    INTENT_NAME = "CLOSE_APP"

    def handle(self, intent, state, permission_manager):
        app_name = intent.slots.get("app_name")

        target_app = None
        target_pid = None

        # closing app using the app name
        if app_name:
            for pid, app in list(state.opened_apps.items()):
                if app.name.lower().strip('.') == app_name.lower():
                    target_app = app
                    target_pid = pid
                    break
        else:
            target_app = state.get_focused_app() or state.get_last_opened_app()

        if not target_app:
            return TaskResult(False, "No application available to close")

        # Safety check
        if may_have_unsaved_data(target_app.name):
            approved = permission_manager.request(
                PermissionRequest(
                    action="CLOSE_APP",
                    app_name=target_app.name,
                    reason="unsaved_data",
                    prompt=f"{target_app.name} may have unsaved changes. Do you want me to close it?"
                )
            )

            if not approved:
                return TaskResult(False, "Close operation cancelled")

        # Perform close
        success = close_app_gracefully(
            pid=target_pid or target_app.pid,
            hwnd=target_app.hwnd,
            app_name=target_app.name
        )

        if success:
            state.unregister_app(target_app.pid)
            return TaskResult(True, f"{target_app.name} closed")

        return TaskResult(False, f"Could not close {target_app.name}")
