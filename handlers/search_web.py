from handlers.base_handler import BaseHandler
from controllers.task_dispatcher import TaskResult
from urllib.parse import quote_plus
import webbrowser

SUPPORTED_BROWSER_NAMES = {"chrome", "edge", "firefox", "brave"}

class WebSearchHandler(BaseHandler):
    INTENT_NAME = "SEARCH_WEB"

    def handle(self, intent, state, permission_manager):
        query = intent.slots.get("query")
        if not query:
            return TaskResult(False, "No search query provided")
        
        encoded = quote_plus(query)
        url = f"https://www.google.com/search?q={encoded}"

        # try to search using the focused browser
        focused_app = state.get_focused_app()
        if focused_app and focused_app.name.lower() in SUPPORTED_BROWSER_NAMES:
            webbrowser.open(url, new=0)
            return TaskResult(True, f"Searching for {query}")
        
        # try to search using last opened browser
        for app in state.opened_apps.values():
            if app.name.lower() in SUPPORTED_BROWSER_NAMES:
                webbrowser.open(url, new=0)
                return TaskResult(True, f"Searching for {query}")
            
        webbrowser.open(url, new=0)
        return TaskResult(True, f"Searching for {query}")