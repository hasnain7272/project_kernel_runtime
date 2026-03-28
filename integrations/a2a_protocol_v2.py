"""
G-A2A Protocol V2 — Bridge Module (redirects to a2a_protocol.py)

This module preserves backward compatibility by re-exporting from
the unified a2a_protocol.py which now includes the GA2AMeshV2 class.
"""

from .a2a_protocol import (
    AgentCard,
    A2AHandler,
    A2ATask,
    A2ATaskState,
    A2AMessage,
    A2APart,
    A2AArtifact,
    GA2AMeshV2,
)

__all__ = [
    "AgentCard", "A2AHandler", "A2ATask", "A2ATaskState",
    "A2AMessage", "A2APart", "A2AArtifact", "GA2AMeshV2",
]
