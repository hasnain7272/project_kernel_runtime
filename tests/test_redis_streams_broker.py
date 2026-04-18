"""
Tests for Redis Streams Broker
"""
import asyncio
import pytest
import pytest_asyncio
from datetime import datetime

from src.infrastructure.queue.redis_streams_broker import (
    LocalDurableBroker,
    StreamMessage,
    MessageStatus
)


@pytest_asyncio.fixture
async def local_broker():
    """Fixture for local broker."""
    broker = LocalDurableBroker()
    yield broker


@pytest.mark.asyncio
class TestLocalDurableBroker:
    """Test local durable broker implementation."""
    
    async def test_publish_and_subscribe(self, local_broker):
        """Test basic publish/subscribe."""
        received_messages = []
        
        async def callback(msg):
            received_messages.append(msg)
        
        # Start subscriber
        task = asyncio.create_task(
            local_broker.subscribe("test_stream", "test_group", callback)
        )
        
        # Give subscriber time to start
        await asyncio.sleep(0.1)
        
        # Publish message
        await local_broker.publish("test_stream", {"test": "data"})
        
        # Wait for processing
        await asyncio.sleep(0.1)
        
        # Cleanup
        task.cancel()
        try:
            await task
        except asyncio.CancelledError:
            pass
        
        # Verify
        assert len(received_messages) == 1
        assert received_messages[0].data["test"] == "data"
    
    async def test_message_ack(self, local_broker):
        """Test message acknowledgment."""
        received = []
        
        async def callback(msg):
            received.append(msg)
        
        task = asyncio.create_task(
            local_broker.subscribe("ack_stream", "ack_group", callback)
        )
        await asyncio.sleep(0.1)
        
        await local_broker.publish("ack_stream", {"id": 1})
        await asyncio.sleep(0.1)
        
        task.cancel()
        try:
            await task
        except asyncio.CancelledError:
            pass
        
        assert len(received) == 1
        assert received[0].status == MessageStatus.COMPLETED
    
    async def test_dead_letter_queue(self, local_broker):
        """Test DLQ for failed messages."""
        fail_count = 0
        
        async def failing_callback(msg):
            nonlocal fail_count
            fail_count += 1
            raise Exception("Always fails")
        
        task = asyncio.create_task(
            local_broker.subscribe("dlq_stream", "dlq_group", failing_callback)
        )
        await asyncio.sleep(0.1)
        
        await local_broker.publish("dlq_stream", {"fail": True})
        await asyncio.sleep(0.5)  # Wait for retries
        
        task.cancel()
        try:
            await task
        except asyncio.CancelledError:
            pass
        
        # Should have attempted 3 times
        assert fail_count == 3
        
        # Check DLQ
        assert len(local_broker._dlq) == 1
        assert local_broker._dlq[0].status == MessageStatus.DEAD_LETTER


@pytest.mark.asyncio
class TestStreamMessage:
    """Test StreamMessage dataclass."""
    
    def test_message_creation(self):
        """Test creating a stream message."""
        msg = StreamMessage(
            id="123",
            stream="test_stream",
            data={"key": "value"},
            trace_id="trace-456"
        )
        
        assert msg.id == "123"
        assert msg.stream == "test_stream"
        assert msg.data == {"key": "value"}
        assert msg.trace_id == "trace-456"
        assert msg.status == MessageStatus.PENDING
        assert msg.attempt_count == 0
    
    def test_message_hash(self):
        """Test message hashing for deduplication."""
        msg1 = StreamMessage(id="1", stream="s1", data={"a": 1})
        msg2 = StreamMessage(id="2", stream="s2", data={"a": 1})
        
        # Different IDs should be different objects
        assert msg1 != msg2