import pkgutil
import importlib
import inspect
from handlers.base_handler import BaseHandler

def load_handlers(dispatcher, handlers_package):
    for _, module_name, _ in pkgutil.iter_modules(handlers_package.__path__):
        module = importlib.import_module(f"{handlers_package.__name__}.{module_name}")

        for _, obj in inspect.getmembers(module, inspect.isclass):
            if issubclass(obj, BaseHandler) and obj is not BaseHandler:
                # Support single intent handlers
                if hasattr(obj, "INTENT_NAME") and obj.INTENT_NAME:
                    dispatcher.register(obj.INTENT_NAME, obj())
                # Support multi-intent handlers
                elif hasattr(obj, "INTENT_NAMES") and obj.INTENT_NAMES:
                    instance = obj()
                    for intent in obj.INTENT_NAMES:
                        dispatcher.register(intent, instance)