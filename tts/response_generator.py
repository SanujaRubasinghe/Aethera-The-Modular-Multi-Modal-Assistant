import threading
import queue
import time

class ResponseGenerator(threading.Thread):
    def __init__(self, intent_queue, response_queue, shutdown_event):
        super().__init__(daemon=True)
        self.intent_queue = intent_queue
        self.response_queue = response_queue
        self.shutdown_event = shutdown_event

    def run(self):
        print("ResponseGenerator [IDLE]")
        while not self.shutdown_event.is_set():
            try:
                intents = self.intent_queue.get(timeout=0.1)
            except queue.Empty:
                continue

            if not intents:
                continue
            response, shutdown_triggered = self.generate_response(intents)

            if response:
                self.response_queue.put(response)

            if shutdown_triggered:
                time.sleep(5)
                self.shutdown_event.set()

            self.intent_queue.task_done()
        print("ResponseGenerator [SHUTDOWN]")

    def generate_response(self, intents):
        messages = []
        shutdown_triggered = False

        for intent in intents:
            if intent.name == "SHUTDOWN":
                app = intent.slots.get("app_name", "app")
                if app == "agent":
                    messages.append("Shutting down all systems. Goodbye!")
                    shutdown_triggered = True

            elif intent.name == "OPEN_APP":
                app = intent.slots.get("app_name", "app")
                messages.append(f"Okay, opening {app}")

            elif intent.name == "SEARCH_WEB":
                query = intent.slots.get("query", "")
                messages.append(f"Performing a search for {query}")

            elif intent.name == "PLAY_MUSIC":
                song = intent.slots.get("song_name", "music")
                messages.append(f"Playing {song}")

            elif intent.name == "SET_ALARM":
                alarm_time = intent.slots.get("time", "the specified time")
                messages.append(f"Setting an alarm for {alarm_time}")

            elif intent.name == "GET_WEATHER":
                city = intent.slots.get("city", "your location")
                messages.append(f"Fetching the weather for {city}")

            else:
                messages.append("I didn’t quite catch that. Could you please repeat?")

        return " ".join(messages), shutdown_triggered
