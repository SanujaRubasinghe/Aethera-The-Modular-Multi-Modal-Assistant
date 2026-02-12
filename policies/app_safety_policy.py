SYSTEM_PROCESS_NAMES = {
    "explorer.exe",
    "winlogon.exe",
    "crss.exe",
    "services.exe",
    "lsass.exe",
    "smss.exe",
    "svchost.exe"
}

PROTECTED_APP_NAMES = {
    "windows security",
    "task manager",
    "registry editor"
}

def is_safe_to_close(process_name: str, app_name: str | None = None) -> bool:
    pname = process_name.lower()
    aname = app_name.lower() if app_name else ""

    if pname in SYSTEM_PROCESS_NAMES:
        return False
    
    if aname in PROTECTED_APP_NAMES:
        return False
    
    return True

