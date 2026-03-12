import queue
import threading

class CentralController(threading.Thread):
    def __init__(self, intent_queue, resposne_queue, dispatcher, shutdown_event, security_gate=None):
        super().__init__(daemon=True)
        self.intent_queue = intent_queue
        self.response_queue = resposne_queue
        self.dispatcher = dispatcher
        self.shutdown_event = shutdown_event
        self.security_gate = security_gate
        self.current_task = None

    def run(self):
        print("CentralController [RUNNING]")
        while not self.shutdown_event.is_set():
            try:
                intent = self.intent_queue.get(timeout=0.1)
                
                if self.security_gate and not self.security_gate.allow(intent):
                    self.response_queue.put("Access denied. Owner not recognized.")
                    continue

                self.response_queue.put("On it!")
                result = self.dispatcher.dispatch(intent, self.response_queue)
                if result and result.message:
                    self.response_queue.put(result.message)
                
            except queue.Empty:
                continue
        print("CentralController [STOPPED]")
