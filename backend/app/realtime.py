import asyncio
from fastapi import WebSocket


class Hub:
    def __init__(self):
        self.clients: set[WebSocket] = set()

    async def broadcast(self, kind, **data):
        async def send(client):
            try:
                await asyncio.wait_for(client.send_json({'type': kind, **data}), timeout=2)
            except Exception:
                self.clients.discard(client)
        await asyncio.gather(*(send(client) for client in tuple(self.clients)))


hub = Hub()
