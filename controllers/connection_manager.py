"""
Gestao de conexoes WebSocket em memoria.

Cada processo da API mantem as suas proprias conexoes. Em producao com varios
workers, esta camada deve ser ligada a Redis Pub/Sub ou outro broker.
"""

from collections import defaultdict
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any

from fastapi import WebSocket
from fastapi.encoders import jsonable_encoder


@dataclass
class ConnectionMeta:
    user_id: int
    user_type: str
    rooms: set[str] = field(default_factory=set)
    connected_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))


class ConnectionManager:
    """Mantem sockets por utilizador e por sala."""

    def __init__(self) -> None:
        self._connections: dict[WebSocket, ConnectionMeta] = {}
        self._users: dict[int, set[WebSocket]] = defaultdict(set)
        self._rooms: dict[str, set[WebSocket]] = defaultdict(set)

    async def connect(self, websocket: WebSocket, user_id: int, user_type: str) -> None:
        await websocket.accept()
        self._connections[websocket] = ConnectionMeta(user_id=user_id, user_type=user_type)
        self._users[user_id].add(websocket)
        await self.join(websocket, f"user:{user_id}")
        await self.join(websocket, f"role:{user_type}")

    def disconnect(self, websocket: WebSocket) -> None:
        meta = self._connections.pop(websocket, None)
        if meta is None:
            return

        self._users[meta.user_id].discard(websocket)
        if not self._users[meta.user_id]:
            self._users.pop(meta.user_id, None)

        for room in list(meta.rooms):
            self._rooms[room].discard(websocket)
            if not self._rooms[room]:
                self._rooms.pop(room, None)

    async def join(self, websocket: WebSocket, room: str) -> None:
        meta = self._connections.get(websocket)
        if meta is None:
            return
        meta.rooms.add(room)
        self._rooms[room].add(websocket)

    async def leave(self, websocket: WebSocket, room: str) -> None:
        meta = self._connections.get(websocket)
        if meta is None:
            return
        meta.rooms.discard(room)
        self._rooms[room].discard(websocket)
        if not self._rooms[room]:
            self._rooms.pop(room, None)

    async def send_personal(self, websocket: WebSocket, event: dict[str, Any]) -> None:
        await websocket.send_json(jsonable_encoder(event))

    async def send_to_user(self, user_id: int, event: dict[str, Any]) -> None:
        for websocket in list(self._users.get(user_id, set())):
            await self._safe_send(websocket, event)

    async def broadcast_room(self, room: str, event: dict[str, Any]) -> None:
        for websocket in list(self._rooms.get(room, set())):
            await self._safe_send(websocket, event)

    async def broadcast_rooms(self, rooms: set[str], event: dict[str, Any]) -> None:
        targets: set[WebSocket] = set()
        for room in rooms:
            targets.update(self._rooms.get(room, set()))
        for websocket in list(targets):
            await self._safe_send(websocket, event)

    def online_count(self, room: str | None = None) -> int:
        if room is None:
            return len(self._connections)
        return len(self._rooms.get(room, set()))

    async def _safe_send(self, websocket: WebSocket, event: dict[str, Any]) -> None:
        try:
            await websocket.send_json(jsonable_encoder(event))
        except RuntimeError:
            self.disconnect(websocket)


connection_manager = ConnectionManager()
