"""In-process WebSocket registry for live notification delivery.

Notifications are always created synchronously inside a regular (sync)
service-layer call, in the same request/transaction as the action that
triggered them — same pattern as everything else in this codebase (see
LLD.md). Pushing the created notification over an open WebSocket is a
"nice to have" on top of that: the row is already persisted and will show
up via the REST API/next poll regardless of whether the push succeeds, so
failures here are swallowed rather than raised.

Single Docker Compose backend instance today, so an in-process dict is
enough — no Redis pub/sub. If the backend is ever horizontally scaled,
this registry would need to move to Redis pub/sub so a notification
created on one worker can reach a connection held open on another.
"""

from __future__ import annotations

import asyncio
import uuid
from collections import defaultdict

from fastapi import WebSocket


class ConnectionManager:
    def __init__(self) -> None:
        self._connections: dict[uuid.UUID, set[WebSocket]] = defaultdict(set)
        self.loop: asyncio.AbstractEventLoop | None = None

    async def connect(self, user_id: uuid.UUID, websocket: WebSocket) -> None:
        await websocket.accept()
        self._connections[user_id].add(websocket)

    def disconnect(self, user_id: uuid.UUID, websocket: WebSocket) -> None:
        self._connections[user_id].discard(websocket)
        if not self._connections[user_id]:
            self._connections.pop(user_id, None)

    async def _send(self, user_id: uuid.UUID, message: dict) -> None:
        for websocket in list(self._connections.get(user_id, ())):
            try:
                await websocket.send_json(message)
            except Exception:  # noqa: BLE001 — best-effort push, connection cleanup happens on disconnect
                pass

    def push(self, user_id: uuid.UUID, message: dict) -> None:
        """Schedule an async send from synchronous service-layer code. The
        event loop is captured once at app startup (see main.py's lifespan).
        If it's unset for any reason this is a no-op — the notification row
        is already persisted regardless, so nothing is lost, just not pushed
        live.
        """
        if self.loop is None:
            return
        asyncio.run_coroutine_threadsafe(self._send(user_id, message), self.loop)


connection_manager = ConnectionManager()
