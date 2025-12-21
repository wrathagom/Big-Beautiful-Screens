from collections import defaultdict

from fastapi import WebSocket


class ConnectionManager:
    """Manages WebSocket connections per screen."""

    def __init__(self):
        # screen_id -> set of WebSocket connections
        self.connections: dict[str, set[WebSocket]] = defaultdict(set)

    async def connect(self, screen_id: str, websocket: WebSocket):
        """Accept and register a WebSocket connection for a screen."""
        await websocket.accept()
        self.connections[screen_id].add(websocket)

    def disconnect(self, screen_id: str, websocket: WebSocket):
        """Remove a WebSocket connection."""
        self.connections[screen_id].discard(websocket)
        # Clean up empty sets
        if not self.connections[screen_id]:
            del self.connections[screen_id]

    async def broadcast(self, screen_id: str, message: dict) -> int:
        """Broadcast a message to all connections for a screen.

        Returns the number of viewers that received the message.
        """
        viewers = 0
        dead_connections = []

        for websocket in self.connections[screen_id]:
            try:
                await websocket.send_json(message)
                viewers += 1
            except Exception:
                dead_connections.append(websocket)

        # Clean up dead connections
        for ws in dead_connections:
            self.connections[screen_id].discard(ws)

        return viewers

    def get_viewer_count(self, screen_id: str) -> int:
        """Get the number of active viewers for a screen."""
        return len(self.connections[screen_id])


# Global instance
manager = ConnectionManager()
