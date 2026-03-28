"""
Event Bus — Central Event Publish/Subscribe System

Provides decoupled communication between all kernel subsystems.
All agent actions, tool executions, task state changes, and governance
decisions are published as typed events through the bus.

Inspired by: OpenHands EventStream, Cursor's flow-based architecture
"""

import asyncio
import logging
from collections import defaultdict
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Callable, Coroutine, Dict, List, Optional
from uuid import uuid4

logger = logging.getLogger(__name__)


# ============================================================================
# Event Types
# ============================================================================

@dataclass
class AgentEvent:
    """Base event published through the event bus."""
    type: str                           # e.g. "task.created", "tool.called"
    payload: Dict[str, Any]             # Event-specific data
    source: str = "kernel"              # Subsystem that emitted the event
    id: str = field(default_factory=lambda: str(uuid4()))
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    session_id: Optional[str] = None    # Link to session context
    task_id: Optional[str] = None       # Link to task context


# Standard event type constants
class EventTypes:
    """Known event types in the kernel."""
    # Task lifecycle
    TASK_CREATED = "task.created"
    TASK_STARTED = "task.started"
    TASK_STEP_STARTED = "task.step.started"
    TASK_STEP_COMPLETED = "task.step.completed"
    TASK_COMPLETED = "task.completed"
    TASK_FAILED = "task.failed"
    TASK_PAUSED = "task.paused"
    TASK_RESUMED = "task.resumed"
    TASK_CANCELLED = "task.cancelled"
    
    # Tool execution
    TOOL_CALLED = "tool.called"
    TOOL_RESULT = "tool.result"
    TOOL_ERROR = "tool.error"
    
    # Governance
    GOVERNANCE_CHECK = "governance.check"
    GOVERNANCE_APPROVED = "governance.approved"
    GOVERNANCE_DENIED = "governance.denied"
    GOVERNANCE_APPROVAL_REQUIRED = "governance.approval_required"
    
    # Session
    SESSION_CREATED = "session.created"
    SESSION_ENDED = "session.ended"
    SESSION_TIMEOUT = "session.timeout"
    
    # LLM
    LLM_REQUEST = "llm.request"
    LLM_RESPONSE = "llm.response"
    LLM_ERROR = "llm.error"
    LLM_TOKEN_USAGE = "llm.token_usage"
    
    # MCP
    MCP_CLIENT_CONNECTED = "mcp.client.connected"
    MCP_CLIENT_DISCONNECTED = "mcp.client.disconnected"
    MCP_TOOL_DISCOVERED = "mcp.tool.discovered"
    
    # A2A
    A2A_TASK_RECEIVED = "a2a.task.received"
    A2A_TASK_DELEGATED = "a2a.task.delegated"
    A2A_PEER_DISCOVERED = "a2a.peer.discovered"
    
    # System
    SYSTEM_STARTUP = "system.startup"
    SYSTEM_SHUTDOWN = "system.shutdown"
    SYSTEM_HEALTH_CHECK = "system.health_check"
    SYSTEM_ERROR = "system.error"

    # UI Events (for real-time UI updates)
    UI_CONNECTED = "ui.connected"
    UI_DISCONNECTED = "ui.disconnected"
    UI_PARAM_CHANGED = "ui.param_changed"
    UI_SUBSCRIPTION = "ui.subscription"
    UI_STATUS_REQUEST = "ui.status_request"
    
    # Reasoning Stream (for ReAct visualization)
    REASONING_START = "reasoning.start"
    REASONING_STEP = "reasoning.step"
    REASONING_COMPLETE = "reasoning.complete"
    
    # Agent Activity
    AGENT_SPAWN = "agent.spawn"
    AGENT_COMPLETE = "agent.complete"
    AGENT_FAILED = "agent.failed"
    
    # Resource Metrics
    METRIC_CPU = "metric.cpu"
    METRIC_MEMORY = "metric.memory"
    METRIC_TOKEN = "metric.token"
    METRIC_LATENCY = "metric.latency"


# ============================================================================
# Event Bus
# ============================================================================

EventHandler = Callable[[AgentEvent], Coroutine[Any, Any, None]]


class EventBus:
    """
    Asynchronous event bus for decoupled inter-subsystem communication.
    
    Features:
    - Typed event publish/subscribe
    - Wildcard subscriptions (e.g., "task.*" matches all task events)
    - Event replay from log for crash recovery
    - Async handlers with error isolation
    - Event log for auditing and debugging
    """
    
    def __init__(self, max_log_size: int = 10000):
        self._subscribers: Dict[str, List[EventHandler]] = defaultdict(list)
        self._event_log: List[AgentEvent] = []
        self._max_log_size = max_log_size
        self._lock = asyncio.Lock()
        logger.info("[EventBus] Initialized")
    
    def subscribe(self, event_type: str, handler: EventHandler) -> None:
        """
        Subscribe a handler to an event type.
        
        Supports wildcards: "task.*" matches "task.created", "task.started", etc.
        Use "*" to subscribe to all events.
        """
        self._subscribers[event_type].append(handler)
        logger.debug(f"[EventBus] Subscribed handler to '{event_type}'")
    
    def unsubscribe(self, event_type: str, handler: EventHandler) -> None:
        """Remove a handler from an event type."""
        if event_type in self._subscribers:
            self._subscribers[event_type] = [
                h for h in self._subscribers[event_type] if h != handler
            ]
    
    async def publish(self, event: AgentEvent) -> None:
        """
        Publish an event to all matching subscribers.
        
        Handlers are called concurrently. Errors in one handler
        don't prevent other handlers from executing.
        """
        # Store in event log
        async with self._lock:
            self._event_log.append(event)
            if len(self._event_log) > self._max_log_size:
                self._event_log = self._event_log[-self._max_log_size:]
        
        # Find matching handlers
        handlers = []
        for pattern, handler_list in self._subscribers.items():
            if self._matches(pattern, event.type):
                handlers.extend(handler_list)
        
        if not handlers:
            return
        
        # Execute all handlers concurrently with error isolation
        tasks = []
        for handler in handlers:
            tasks.append(self._safe_call(handler, event))
        
        await asyncio.gather(*tasks)
    
    async def publish_and_wait(self, event: AgentEvent) -> None:
        """Publish and wait for all handlers to complete."""
        await self.publish(event)
    
    def emit(self, event_type: str, payload: Dict[str, Any] = None,
             source: str = "kernel", session_id: str = None,
             task_id: str = None) -> AgentEvent:
        """
        Convenience method to create and return an event (does not publish).
        Call `await bus.publish(event)` to dispatch.
        """
        return AgentEvent(
            type=event_type,
            payload=payload or {},
            source=source,
            session_id=session_id,
            task_id=task_id,
        )
    
    async def emit_and_publish(self, event_type: str, payload: Dict[str, Any] = None,
                               source: str = "kernel", session_id: str = None,
                               task_id: str = None) -> AgentEvent:
        """Create, publish, and return an event in one call."""
        event = self.emit(event_type, payload, source, session_id, task_id)
        await self.publish(event)
        return event
    
    def replay(self, from_event_id: Optional[str] = None,
               event_type: Optional[str] = None,
               limit: int = 100) -> List[AgentEvent]:
        """
        Replay events from the log for crash recovery or debugging.
        
        Args:
            from_event_id: Start replaying from this event ID (exclusive)
            event_type: Filter by event type
            limit: Maximum number of events to return
        """
        events = self._event_log
        
        if from_event_id:
            found_idx = None
            for i, e in enumerate(events):
                if e.id == from_event_id:
                    found_idx = i
                    break
            if found_idx is not None:
                events = events[found_idx + 1:]
        
        if event_type:
            events = [e for e in events if self._matches(event_type, e.type)]
        
        return events[-limit:]
    
    def get_event_log(self, last_n: int = 50) -> List[AgentEvent]:
        """Get the last N events from the log."""
        return self._event_log[-last_n:]
    
    @property
    def subscriber_count(self) -> int:
        """Total number of active subscriptions."""
        return sum(len(handlers) for handlers in self._subscribers.values())
    
    @staticmethod
    def _matches(pattern: str, event_type: str) -> bool:
        """Check if event type matches a subscription pattern."""
        if pattern == "*":
            return True
        if pattern == event_type:
            return True
        if pattern.endswith(".*"):
            prefix = pattern[:-2]
            return event_type.startswith(prefix + ".")
        return False
    
    @staticmethod
    async def _safe_call(handler: EventHandler, event: AgentEvent) -> None:
        """Call a handler with error isolation."""
        try:
            await handler(event)
        except Exception as e:
            logger.error(
                f"[EventBus] Handler error for '{event.type}': {e}",
                exc_info=True
            )
