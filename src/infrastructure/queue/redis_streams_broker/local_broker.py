"""Local Durable Broker for dev."""
import asyncio
import logging
import time
import uuid
from typing import Any, Callable, Dict, List, Optional, Set

from .models import StreamMessage, MessageStatus

logger = logging.getLogger(__name__)

class LocalDurableBroker:
    def __init__(self):
        self._streams: Dict[str, asyncio.Queue] = {}
        self._channels: Dict[str, Set[asyncio.Queue]] = {}
        self._pending: Dict[str, StreamMessage] = {}
        self._completed: Set[str] = set()
        self._dlq: List[StreamMessage] = []
        self._counter = 0
        
    async def publish(self, stream: str, data: Any, trace_id: Optional[str] = None, **kwargs) -> str:
        if isinstance(data, dict) and trace_id and "trace_id" not in data:
            data["trace_id"] = trace_id
        if isinstance(data, dict) and "tenant_id" in kwargs and "tenant_id" not in data:
            data["tenant_id"] = kwargs["tenant_id"]
         
        self._counter += 1
        msg_id = f"{time.time()}-{self._counter}"
        message = StreamMessage(id=msg_id, stream=stream, data=data, trace_id=trace_id or str(uuid.uuid4()))
        # Only enqueue to _streams if a durable subscriber exists (via subscribe())
        if stream in self._streams:
            await self._streams[stream].put(message)
        # Broadcast to all channel subscribers
        for subscriber in list(self._channels.get(stream, set())):
            await subscriber.put(message)
        return msg_id
    
    async def subscribe_channel(self, channel: str, callback: Callable[[Any], Any]):
        subscriber: asyncio.Queue = asyncio.Queue()
        self._channels.setdefault(channel, set()).add(subscriber)
        logger.info(f"[LocalBroker] Subscribed to channel {channel}")
        while True:
            try:
                msg = await subscriber.get()
                await callback(msg)
            except asyncio.CancelledError:
                self._channels.get(channel, set()).discard(subscriber)
                break
            except Exception as e:
                logger.error(f"[LocalBroker] Channel error: {e}")
                await asyncio.sleep(1)
    
    async def subscribe(self, stream: str, group: str, callback: Callable[[StreamMessage], Any], **kwargs):
        if stream not in self._streams:
            self._streams[stream] = asyncio.Queue()
        logger.info(f"[LocalBroker] Consumer joined {group} on {stream}")
        while True:
            try:
                message = await self._streams[stream].get()
                if message.id in self._completed:
                    continue
                message.consumer_group = group
                message.status = MessageStatus.PROCESSING
                self._pending[message.id] = message
                try:
                    await callback(message)
                    message.status = MessageStatus.COMPLETED
                    self._completed.add(message.id)
                    del self._pending[message.id]
                except Exception as e:
                    message.attempt_count += 1
                    if message.attempt_count >= 3:
                        message.status = MessageStatus.DEAD_LETTER
                        message.error = str(e)
                        self._dlq.append(message)
                    else:
                        await self._streams[stream].put(message)
            except asyncio.CancelledError:
                break
