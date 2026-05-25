"""
Emissao de eventos realtime a partir de controllers sincronas.
"""

import asyncio
from typing import Any

import anyio

from controllers.connection_manager import connection_manager


def emit_to_rooms(rooms: set[str], event: dict[str, Any]) -> None:
    """Envia evento WebSocket para varias salas, quando houver loop disponivel."""
    if not rooms:
        return
    try:
        anyio.from_thread.run(connection_manager.broadcast_rooms, rooms, event)
        return
    except RuntimeError:
        pass

    try:
        loop = asyncio.get_running_loop()
    except RuntimeError:
        return
    loop.create_task(connection_manager.broadcast_rooms(rooms, event))


def emit_to_user(user_id: int, event: dict[str, Any]) -> None:
    """Envia evento WebSocket para todas as conexoes de um utilizador."""
    try:
        anyio.from_thread.run(connection_manager.send_to_user, user_id, event)
        return
    except RuntimeError:
        pass

    try:
        loop = asyncio.get_running_loop()
    except RuntimeError:
        return
    loop.create_task(connection_manager.send_to_user(user_id, event))
