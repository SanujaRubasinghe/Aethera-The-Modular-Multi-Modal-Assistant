from ui_automation.uia_tree import UIATree
from ui_automation.exceptions import AutomationError
from ui_automation.actions import perform_action

class UIAutomationEngine:
    def execute(self, hwnd: int, plan):
        tree = UIATree(hwnd=hwnd)

        for step in plan.steps:
            element = tree.find(step.selector, timeout_ms=step.timeout_ms)
            if not element:
                raise AutomationError(f"UI element not found: {step.selector}")
            
            perform_action(element=element, action=step)
        return True