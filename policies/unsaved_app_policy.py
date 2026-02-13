UNSAVED_SENSITIVE_APPS = {
    "notepad.",
    "word.",
    "excel.",
    "powerpoint.",
    "visual studio.",
    "vs code."
}

def may_have_unsaved_data(app_name: str) -> bool:
    return app_name.lower() in UNSAVED_SENSITIVE_APPS