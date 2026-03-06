import re
import os
import json
from typing import List, Dict, Tuple, Optional, Any
from pathlib import Path

from app_indexer.windows_app_indexer import WindowsAppIndexer

class Intent:
    def __init__(self, name: str, slots: Optional[Dict[str, str]] = None, priority: int = 0, depends_on: Optional[str] = None,
                 timeout_ms: int = 5000):
        self.name = name
        self.slots = slots or {}
        self.priority = priority
        self.depends_on = depends_on
        self.timeout_ms = timeout_ms

    def to_dict(self):
        return {
            "intent": self.name, 
            "slots": self.slots,
            "priority": self.priority,
            "timeout_ms": self.timeout_ms
        }
    
class IntentChain:
    def __init__(self, intents: List[Intent], mode: str = "sequential", rollback_on_error: bool = True):
        self.intents = intents
        self.mode = mode
        self.rollback_on_error = rollback_on_error

class MacroResolver:
    def __init__(self, macro_file: str = "config/macro_definitions.json"):
        self.macro_file = macro_file
        self.macros = self._load_macros()

    def _load_macros(self) -> Dict[str, Any]:
        if os.path.exists(self.macro_file):
            with open(self.macro_file, 'r') as f:
                data = json.load(f)
                return {k: v for k, v in data['macros'].items() if v.get('enabled', True)}
        return {}
    
    def is_macro(self, text: str) -> bool:
        normalized = text.lower().replace(" ", "_")
        return normalized in self.macros
    
    def resolve_macro(self, text: str, context: Optional[Dict[str, str]] = None) -> IntentChain:
        normalized = text.lower().replace(" ", "_")
        macro_def = self.macros.get(normalized)

        if not macro_def:
            raise ValueError(f"Macro '{text}' not found")
        
        variables = macro_def.get("variables", {})
        context = context or {}
        context['username'] = os.getenv('USERNAME', 'user')
        context.update(variables)

        intents = []
        for intent_def in macro_def['intents']:
            slots = {}
            # TODO: integrate app resolver to add path and type
            for key, value in intent_def['slots'].items():
                if isinstance(value, str) and '${' in value:
                    for var_name, var_value in context.items():
                        value = value.replace(f'${{{var_name}}}', var_value)
                    slots[key] = value
            
            intent = Intent(
                name=intent_def['name'],
                slots=slots,
                timeout_ms=intent_def.get('timeout_ms', 5000),
                priority=intent_def.get('priority', 0)
            )
            intents.append(intent)
        
        return IntentChain(
            intents=intents,
            mode=macro_def.get('mode', 'sequential'),
            rollback_on_error=macro_def.get('rollback_on_error', True)
        )
    
    def list_macros(self) -> List[str]:
        return list(self.macros.keys())
    
class RuleBasedIntentClassifier:
    def __init__(self, response_queue):
        self.rules = [
            ("CONFIRM_YES", re.compile(r"\b(yes|sure|go ahead)\b", re.IGNORECASE)), 
            ("CONFIRM_NO", re.compile(r"\b(no|cancel|don't close)\b", re.IGNORECASE)),
            ("CLOSE_APP", re.compile(r"\b(close|exit)\s+(?P<app_name>.+)", re.IGNORECASE)), # working
            ("OPEN_APP", re.compile(r"\b(open|launch|start)\s+(?P<app_name>.+)", re.IGNORECASE)), # working
            ("SHUTDOWN", re.compile(r"\b(shutdown)\s+(?P<app_name>.+)", re.IGNORECASE)),
            ("SET_ALARM", re.compile(r"\b(set alarm|wake me up)\s+at\s+(?P<time>[\d:apm\s]+)", re.IGNORECASE)),
            ("PLAY_MUSIC", re.compile(r"\b(play|song|music)\s+(?P<song_name>.+)", re.IGNORECASE)),
            ("GET_WEATHER", re.compile(r"\b(weather|temperature)\s*(in\s+(?P<city>\w+))?", re.IGNORECASE)),
            ("CHECK_EMAIL", re.compile(r"\bcheck(?:\s+\w+)*\s+emails?\b", re.IGNORECASE)),
            ("SEARCH_WEB", re.compile(r"\b(search for|look up|search|find)\s+(?P<query>.+)", re.IGNORECASE)), # working
            ("SET_VOLUME", re.compile(r"\b(set volume|volume)\s+(to\s+)?(?P<level>\d+)", re.IGNORECASE)),
            ("INCREASE_VOLUME", re.compile(r"\b(increase|raise|turn up)\s+(the\s+)?volume\b", re.IGNORECASE)),
            ("DECREASE_VOLUME", re.compile(r"\b(decrease|lower|turn down)\s+(the\s+)?volume\b", re.IGNORECASE)),
            ("MUTE_VOLUME", re.compile(r"\b(mute)\s+(the\s+)?(volume|sound|audio)\b", re.IGNORECASE)),
            ("UNMUTE_VOLUME", re.compile(r"\b(unmute)\s+(the\s+)?(volume|sound|audio)\b", re.IGNORECASE)),
            ("GET_VOLUME", re.compile(r"\b(what('s)?|what is|get)\s+(the\s+)?(current\s+)?volume\b", re.IGNORECASE)),
            ("MOVE_WINDOW_LEFT", re.compile(r"\b(move|shift)\s+(this\s+|the\s+)?window\s+to\s+(the\s+)?(left|next|other)\b", re.IGNORECASE)),
            ("MOVE_WINDOW_RIGHT", re.compile(r"\b(move|shift)\s+(this\s+|the\s+)?window\s+to\s+(the\s+)?(right|main|primary)\b", re.IGNORECASE)),
            ("MINIMIZE_APP", re.compile(r"\b(minimize)\s+(?P<app_name>.+)", re.IGNORECASE)),
            ("TAKE_SCREENSHOT", re.compile(
                r"\b("
                r"take\s+(a\s+)?screenshot|"
                r"screenshot|"
                r"capture\s+(my\s+)?screen"
                r")"
                r"(\s+(of|on)\s+"
                r"(?P<monitor>primary|secondary|all|monitor\s*\d+|\d+))?",
                re.IGNORECASE
            )),
            ("SEND_WHATSAPP_MESSAGE", re.compile(
                r"\b(send|text|whatsapp)\s+(?P<contact>[\w\s]+)\s+(a\s+)?message\s+(saying|with|:)\s+(?P<message>.+)",
                re.IGNORECASE
            )),
            ("READ_SCREEN", re.compile(
                r"\b(what am i looking at|what is on my screen|what's on my screen|describe my screen|read my screen)\b",
                re.IGNORECASE
            )),
        ]

        self.response_queue = response_queue

        self.macro_resolver = MacroResolver()
        self.fallback_intent = "fallback"

        self.app_indexer = WindowsAppIndexer()

    @staticmethod
    def split_commands(text: str) -> List[str]:
        text = text.lower().strip()
        parts = re.split(r"\band\b|\bthen\b|;", text)
        return [p.strip() for p in parts if p.strip()]
    
    def classify_single(self, text: str) -> Intent:
        text = text.strip()

        for intent_name, pattern in self.rules:
            match = pattern.search(text)
            if match:
                slots = {k: v for k, v in match.groupdict().items() if v}
                
                if intent_name == "OPEN_APP":
                    app_entry = self.app_indexer.search(slots["app_name"])
                    if app_entry == None:
                        self.response_queue.put("Sorry, I couldn't open the app, try again please.")
                        # TODO: add app re index dialog
                        return Intent(self.fallback_intent)
                    else:
                        if app_entry["type"] == "uwp":
                            slots["aumid"] = app_entry["aumid"]
                        else:
                            slots["path"] = app_entry["path"]
                        slots["type"] = app_entry["type"]
                
                if intent_name == "TAKE_SCREENSHOT":
                    monitor = slots.get("monitor")
                    if monitor:
                        monitor = monitor.lower().replace("monitor", "").strip()
                        if monitor == "secondary":
                            slots["monitor"] = "1"
                        elif monitor.isdigit():
                            slots["monitor"] = monitor
                        else:
                            slots["monitor"] = monitor
                return Intent(intent_name, slots)
        return Intent(self.fallback_intent)
    
    def classify(self, text: str) -> List[Intent]:
        if self.macro_resolver.is_macro(text):
            chain = self.macro_resolver.resolve_macro(text)
            return chain.intents
        
        subcommands = self.split_commands(text)
        intents = [self.classify_single(sub) for sub in subcommands]
        return intents
    
    def classify_json(self, text: str) -> str:
        intents = self.classify(text)
        return json.dumps([intent.to_dict() for intent in intents], indent=2)
