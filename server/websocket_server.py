import asyncio
import json
import logging
import threading
from websockets.server import serve

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("WebSocketServer")

class WebSocketServer:
    def __init__(self, host="localhost", port=8765):
        self.host = host
        self.port = port
        self.clients = set()
        self.loop = None
        self.server = None
        self._thread = None

    async def register(self, websocket):
        self.clients.add(websocket)
        logger.info(f"Client connected. Total clients: {len(self.clients)}")
        try:
            await websocket.wait_closed()
        finally:
            self.clients.remove(websocket)
            logger.info(f"Client disconnected. Total clients: {len(self.clients)}")

    async def _broadcast(self, message: dict):
        if not self.clients:
            return
        
        message_json = json.dumps(message)
        # Create a copy of clients to avoid set changed during iteration
        for client in list(self.clients):
            try:
                await client.send(message_json)
            except Exception as e:
                logger.error(f"Error sending message to client: {e}")

    def broadcast(self, message_type: str, value):
        """
        Thread-safe broadcast method.
        message_type: 'state', 'audio_level', 'transcript', 'modules'
        """
        if self.loop and self.loop.is_running():
            message = {"type": message_type, "value": value}
            asyncio.run_coroutine_threadsafe(self._broadcast(message), self.loop)

    async def main(self):
        self.loop = asyncio.get_running_loop()
        async with serve(self.register, self.host, self.port):
            logger.info(f"WebSocket server started on ws://{self.host}:{self.port}")
            await asyncio.Future()  # run forever

    def _run_server(self):
        asyncio.run(self.main())

    def start(self):
        if self._thread and self._thread.is_alive():
            return
        self._thread = threading.Thread(target=self._run_server, daemon=True)
        self._thread.start()

# Global instance
ws_server = WebSocketServer()
