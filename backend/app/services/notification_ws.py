"""Redis pub/sub-backed WebSocket registry for live notification delivery.

Notifications are always created synchronously inside a regular (sync)
service-layer call, in the same request/transaction as the action that
triggered them — same pattern as everything else in this codebase (see
LLD.md). Pushing the created notification over an open WebSocket is a
"nice to have" on top of that: the row is already persisted and will show
up via the REST API/next poll regardless of whether the push succeeds, so
failures here are swallowed rather than raised.

gunicorn runs multiple worker processes (see backend/Dockerfile), each with
its own copy of this module's in-process `_connections` dict — a
notification created by a request handled on worker A has no way to reach a
WebSocket connection held open on worker B without something shared between
them. Every worker publishes pushes to a shared Redis channel and also runs
a background subscriber thread reading that same channel, so whichever
worker(s) actually hold the target user's connection deliver it; workers
that don't just no-op on an empty local `_connections` lookup.
"""

from __future__ import annotations

import asyncio
import json
import threading
import uuid
from collections import defaultdict

from fastapi import WebSocket

from app.core.logging import get_logger
from app.core.redis_client import get_redis

logger = get_logger(__name__)

NOTIFICATIONS_CHANNEL = "ws:notifications"
LISTENER_POLL_TIMEOUT_SECONDS = 1.0


class ConnectionManager:
    def __init__(self) -> None:
        self._connections: dict[uuid.UUID, set[WebSocket]] = defaultdict(set)
        self.loop: asyncio.AbstractEventLoop | None = None
        self._stopping = False
        self._listener_thread: threading.Thread | None = None

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
        """Publish rather than deliver directly — this process's own
        subscriber thread (started by start_redis_listener) will receive
        this same event back and deliver it if (and only if) this user has
        a connection open on this particular worker.
        """
        get_redis().publish(NOTIFICATIONS_CHANNEL, json.dumps({"user_id": str(user_id), "message": message}))

    def start_redis_listener(self) -> None:
        """One background thread per worker process, started from the app
        lifespan. Polls with a timeout (rather than blocking indefinitely on
        pubsub.listen()) specifically so stop_redis_listener can make it
        exit promptly and deterministically — closing the underlying
        connection to interrupt a blocking listen() isn't reliable across
        Redis client implementations.
        """
        self._stopping = False

        def _listen() -> None:
            pubsub = get_redis().pubsub()
            pubsub.subscribe(NOTIFICATIONS_CHANNEL)
            while not self._stopping:
                try:
                    raw = pubsub.get_message(ignore_subscribe_messages=True, timeout=LISTENER_POLL_TIMEOUT_SECONDS)
                except Exception:  # noqa: BLE001 — transient Redis hiccup; keep polling rather than killing the thread
                    continue
                if raw is None:
                    continue
                try:
                    envelope = json.loads(raw["data"])
                    user_id = uuid.UUID(envelope["user_id"])
                except (ValueError, KeyError, TypeError):
                    logger.warning("ws_notification_bad_envelope", data=raw.get("data"))
                    continue
                if self.loop is not None:
                    coro = self._send(user_id, envelope["message"])
                    try:
                        asyncio.run_coroutine_threadsafe(coro, self.loop)
                    except RuntimeError:
                        # The event loop closed out from under this thread (e.g. a
                        # stop-in-progress racing a message still in flight) — drop
                        # this one message rather than letting the whole listener
                        # thread die and silently stop delivering everything after.
                        # Close explicitly: run_coroutine_threadsafe never got to
                        # schedule it, so nothing else will await/close it.
                        coro.close()
                        logger.warning("ws_notification_delivery_failed", user_id=str(user_id))
            pubsub.close()

        self._listener_thread = threading.Thread(target=_listen, daemon=True)
        self._listener_thread.start()

    def stop_redis_listener(self) -> None:
        self._stopping = True


connection_manager = ConnectionManager()
