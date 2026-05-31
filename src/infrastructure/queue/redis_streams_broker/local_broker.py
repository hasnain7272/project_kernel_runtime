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
        self._pending: Dict[str, StreamMessage] = {}
        self._completed: Set[str] = set()
        self._dlq: List[StreamMessage] = []
        self._counter = 0
        
    async def publish(self, stream: str, data: Dict[str, Any], trace_id: Optional[str] = None, **kwargs) -> str:
        if stream not in self._streams:
            self._streams[stream] = asyncio.Queue()
        if trace_id and "trace_id" not in data:
            data["trace_id"] = trace_id
        if "tenant_id" in kwargs and "tenant_id" not in data:
            data["tenant_id"] = kwargs["tenant_id"]
         
        self._counter += 1
        msg_id = f"{time.time()}-{self._counter}"
        message = StreamMessage(id=msg_id, stream=stream, data=data, trace_id=trace_id or str(uuid.uuid4()))
        await self._streams[stream].put(message)
        return msg_id
    
    async def subscribe_channel(self, channel: str, callback: Callable[[Any], Any]):
        if channel not in self._streams:
            self._streams[channel] = asyncio.Queue()
        logger.info(f"[LocalBroker] Subscribed to channel {channel}")
        while True:
            try:
                msg = await self._streams[channel].get()
                await callback(msg)
            except asyncio.CancelledError:
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
