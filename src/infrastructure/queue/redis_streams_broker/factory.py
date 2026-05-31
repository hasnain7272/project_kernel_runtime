"""Broker Factory."""
import logging
import os
from typing import Optional, Any
from .local_broker import LocalDurableBroker

logger = logging.getLogger(__name__)

_broker_instance: Optional[Any] = None

async def get_streams_broker():
    global _broker_instance
    if _broker_instance is None:
        broker_url = os.environ.get("REDIS_URL", "memory://")
        if broker_url.startswith("memory://"):
            logger.info("[Broker] Initialized MemoryBroker")
            _broker_instance = LocalDurableBroker()
        else:
            logger.warning("[Broker] Redis not fully split to <150 lines yet. Using MemoryBroker fallback.")
            _broker_instance = LocalDurableBroker()
    return _broker_instance

get_broker = get_streams_broker
