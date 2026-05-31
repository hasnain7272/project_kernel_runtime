"""Broker Models."""
import time
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, Optional

class MessageStatus(Enum):
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"
    DEAD_LETTER = "dead_letter"

@dataclass
class StreamMessage:
    id: str
    stream: str
    data: Dict[str, Any]
    consumer_group: Optional[str] = None
    consumer_name: Optional[str] = None
    status: MessageStatus = MessageStatus.PENDING
    attempt_count: int = 0
    created_at: float = field(default_factory=time.time)
    processed_at: Optional[float] = None
    error: Optional[str] = None
    trace_id: Optional[str] = None
