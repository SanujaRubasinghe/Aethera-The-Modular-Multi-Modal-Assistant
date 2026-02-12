class AutomationError(Exception):
    def __init__(self, error_message):
        super.__init__(error_message)
