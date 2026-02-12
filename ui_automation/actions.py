from ui_automation.models import UIAction
from ui_automation.exceptions import AutomationError
import comtypes

UIA = comtypes.client.GetModule("UIAutomationCore.dll")

def perform_action(element, action: UIAction):
    if action.action == "click":
        invoke = element.GetCurrentPattern(UIA.UIA_InvokePatternId)
        invoke.Invoke()

    elif action.action == "set_text":
        value = element.GetCurrentPattern(UIA.UIA_ValuePatternId)
        value.SetValue(action.value)

    elif action.action == "focus":
        element.SetFocus()

    else:
        raise AutomationError(f"Unsupported action: {action.action}")