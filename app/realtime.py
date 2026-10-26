"""Live updates over WebSockets.

Clients connect to a 'topic' (for example match:7 or leaderboard). When something
changes, the API calls publish() and every client on that topic gets the message.

Limit: connections live inside this one Python process. With several server
processes you would add Redis Pub/Sub so a message reaches every process.
"""
import logging
from collections import defaultdict
from typing import Dict, Set

from anyio import from_thread
from fastapi import WebSocket

logger = logging.getLogger(__name__)


class ConnectionManager:
    def __init__(self):
        self._connections: Dict[str, Set[WebSocket]] = defaultdict(set)

    async def connect(self, topic: str, websocket: WebSocket) -> None:
        await websocket.accept()
        self._connections[topic].add(websocket)

    def disconnect(self, topic: str, websocket: WebSocket) -> None:
        sockets = self._connections.get(topic)
        if sockets is None:
            return
        sockets.discard(websocket)
        if not sockets:
            del self._connections[topic]

    async def broadcast(self, topic: str, message: dict) -> None:
        for websocket in list(self._connections.get(topic, ())):
            try:
                await websocket.send_json(message)
            except Exception:  # the client is gone: forget it
                self.disconnect(topic, websocket)


manager = ConnectionManager()


def publish(topic: str, message: dict) -> None:
    """Call this from normal (non-async) route code. It never raises."""
    try:
        from_thread.run(manager.broadcast, topic, message)
    except Exception:
        logger.warning("Could not publish to %s", topic, exc_info=True)
