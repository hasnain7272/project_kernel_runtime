import asyncio
import base64
import json
import logging
import os
from typing import Any, Callable, Dict, Optional

from .redis_streams_broker import get_streams_broker

logger = logging.getLogger(__name__)
REDIS_URL = os.environ.get("REDIS_URL", "")

class RedisPubSubBroker:
    """Legacy-compatible PubSub broker for ephemeral UI logs."""
    def __init__(self, url: str):
        self.url = url
        self._redis = None

    async def _get_client(self):
        if self._redis is None:
            import redis.asyncio as aioredis
            self._redis = aioredis.from_url(self.url, decode_responses=True)
        return self._redis

    async def publish(self, channel: str, message: Any):
        client = await self._get_client()
        payload = json.dumps({"data": message}) if not isinstance(message, (str, bytes)) else message
        if isinstance(payload, bytes):
            payload = payload.decode('utf-8', errors='replace')
        await client.publish(channel, payload)

    async def iter_messages(self, channel: str):
        client = await self._get_client()
        pubsub = client.pubsub()
        await pubsub.subscribe(channel)
        try:
            async for raw in pubsub.listen():
                if raw["type"] == "message":
                    data = raw["data"]
                    try:
                        yield json.loads(data)["data"]
                    except:
                        yield data
        finally:
            await pubsub.unsubscribe(channel)
            await pubsub.close()

class LocalPubSubBroker:
    """In-memory fallback for PubSub."""
    def __init__(self):
        self._queues: Dict[str, asyncio.Queue] = {}

    async def publish(self, channel: str, message: Any):
        if channel in self._queues:
            await self._queues[channel].put(message)

    async def get_queue(self, channel: str) -> asyncio.Queue:
        if channel not in self._queues:
            self._queues[channel] = asyncio.Queue()
        return self._queues[channel]

_pubsub_instance = None

def get_broker():
    """Returns the PubSub broker for transient logging."""
    global _pubsub_instance
    if _pubsub_instance is None:
        _pubsub_instance = RedisPubSubBroker(REDIS_URL) if REDIS_URL else LocalPubSubBroker()
    return _pubsub_instance

async def get_broker_async():
    return get_broker()
