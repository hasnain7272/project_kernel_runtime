"""
Event Broker — Redis-backed Pub/Sub with local asyncio fallback.

In production: connects to a real Redis instance.
Locally (venv): falls back to asyncio queues identically.
Controlled by the REDIS_URL environment variable.
"""
import asyncio
import json
import logging
import os
from typing import Any, Callable, Dict, Optional

logger = logging.getLogger(__name__)

REDIS_URL = os.environ.get("REDIS_URL", "")

# ──────────────────────────────────────────────────
# Redis-backed implementation
# ──────────────────────────────────────────────────

class RedisBroker:
    """Production broker using redis.asyncio pub/sub."""

    def __init__(self, url: str):
        self.url = url
        self._redis = None
        self._pubsub = None

    async def _get_client(self):
        if self._redis is None:
            import redis.asyncio as aioredis
            self._redis = aioredis.from_url(
                self.url, decode_responses=True
            )
        return self._redis

    async def publish(self, channel: str, message: Dict[str, Any]):
        client = await self._get_client()
        await client.publish(channel, json.dumps(message))
        logger.debug(f"[Redis] Published -> {channel}")

    async def subscribe(
        self, channel: str, callback: Callable[[Dict], Any]
    ):
        client = await self._get_client()
        pubsub = client.pubsub()
        await pubsub.subscribe(channel)
        async for raw in pubsub.listen():
            if raw["type"] == "message":
                data = json.loads(raw["data"])
                await callback(data)


# ──────────────────────────────────────────────────
# Local asyncio fallback (venv-only, no Redis needed)
# ──────────────────────────────────────────────────

class LocalBroker:
    """Thread-safe in-process broker for local dev without Redis."""

    def __init__(self):
        self._subscribers: Dict[str, list[Callable]] = {}
        self._queues: Dict[str, asyncio.Queue] = {}

    async def publish(self, channel: str, message: Dict[str, Any]):
        logger.debug(f"[Local] Published -> {channel}")
        if channel in self._subscribers:
            for cb in self._subscribers[channel]:
                asyncio.create_task(cb(message))
        if channel in self._queues:
            await self._queues[channel].put(message)

    def subscribe_sync(self, channel: str, callback: Callable):
        self._subscribers.setdefault(channel, []).append(callback)

    async def get_queue(self, channel: str) -> asyncio.Queue:
        if channel not in self._queues:
            self._queues[channel] = asyncio.Queue()
        return self._queues[channel]


# ──────────────────────────────────────────────────
# Factory — single broker instance per process
# ──────────────────────────────────────────────────

_broker_instance = None


def get_broker():
    global _broker_instance
    if _broker_instance is None:
        if REDIS_URL:
            logger.info(f"[Broker] Using Redis at {REDIS_URL}")
            _broker_instance = RedisBroker(REDIS_URL)
        else:
            logger.info("[Broker] No REDIS_URL — using local asyncio broker")
            _broker_instance = LocalBroker()
    return _broker_instance
