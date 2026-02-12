import time
import comtypes.client

UIA = comtypes.client.GetModule("UIAutomationCore.dll")
uia = comtypes.client.CreateObject(
    "{ff48dba4-60ef-4201-aa87-54103eef594e}",
    interface=UIA.IUIAutomation
)

class UIATree:
    def __init__(self, hwnd: int):
        self.root = uia.ElementFromHandle(hwnd)

    def find(self, selector: dict, timeout_ms=3000):
        end = time.time() + (timeout_ms / 1000)

        while time.time() < end:
            element = self._search(self.root, selector)
            if element:
                return element
            time.sleep(0.2)

        return None
    
    def _search(self, root, selector):
        condition = self._build_condition(selector)
        return root.FindFirst(UIA.TreeScope_Subtree, condition)
    
    def _build_condition(self, selector):
        conditions = []

        if "name" in selector:
            conditions.append(
                uia.CreatePropertyCondition(
                    UIA.UIA_NamePropertyId,
                    selector["name"]
                )
            )

        if "control_type" in selector:
            conditions.append(
                uia.CreatePropertyCondition(
                    UIA.UIA_ControlTypePropertyId,
                    getattr(UIA, f"UIA_{selector['control_type']}ControlTypeId")
                )
            )

        if not conditions:
            return uia.CreateTrueCondition()
        
        cond = conditions[0]
        for c in conditions[1:]:
            cond = uia.CreateAndCondition(cond, c)

        return cond