import threading
from intent.intent_classifier import RuleBasedIntentClassifier
from intent.llm_intent_classifier import LLMIntentClassifier

class TerminalInput(threading.Thread):
    def __init__(self, intent_queue, response_queue, shutdown_event):
        super().__init__(daemon=True)
        self.intent_queue = intent_queue
        self.response_queue = response_queue
        self.shutdown_event = shutdown_event
        self.rule_classifier = RuleBasedIntentClassifier(self.response_queue)
        self.llm_classifier = LLMIntentClassifier()

    def run(self):
        print("TerminalInput [READY] - Type commands below:")
        while not self.shutdown_event.is_set():
            try:
                # Use a small timeout to check shutdown_event periodically
                # However, input() is blocking. We'll use a trick or just let it block.
                # Since it's a daemon thread, it will exit when the main thread exits.
                user_input = input(">> ").strip()
                if not user_input:
                    continue

                print(f"TerminalInput: Processing '{user_input}'")
                
                # Rule-based classification
                intents = self.rule_classifier.classify(user_input)
                
                # Check for fallback
                if len(intents) == 1 and intents[0].name == "fallback":
                    llm_intent = self.llm_classifier.classify(user_input)
                    if llm_intent:
                        intents = [llm_intent]

                for intent in intents:
                    print(f"TerminalInput: Dispatching intent '{intent.name}'")
                    self.intent_queue.put(intent)
                    
            except EOFError:
                break
            except Exception as e:
                print(f"TerminalInput Error: {e}")
        print("TerminalInput [STOPPED]")
