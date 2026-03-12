import threading


class TerminalInput(threading.Thread):
    """
    Debug input — type text in the terminal, it goes straight
    to the agent via text_queue (same path as voice).
    """

    def __init__(self, text_queue, shutdown_event):
        super().__init__(daemon=True)
        self.text_queue = text_queue
        self.shutdown_event = shutdown_event

    def run(self):
        print("TerminalInput [READY] - Type commands below:")
        while not self.shutdown_event.is_set():
            try:
                user_input = input(">> ").strip()
                if not user_input:
                    continue

                print(f"TerminalInput: '{user_input}' → Agent")
                self.text_queue.put(user_input)

            except EOFError:
                break
            except Exception as e:
                print(f"TerminalInput Error: {e}")
        print("TerminalInput [STOPPED]")
