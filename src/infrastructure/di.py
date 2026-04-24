"""
Service Locator — Lightweight dependency access.

Instead of a full DI container that nobody uses, this provides
typed factory functions that are actually called by the codebase.
Easy to mock in tests via monkeypatch.
"""
from src.infrastructure.sandbox.docker_adapter import SandboxAdapter
from src.services.tool_execution.router import ToolExecutionRouter


def get_tool_router() -> ToolExecutionRouter:
    """Get tool execution router."""
    return ToolExecutionRouter()


def get_sandbox() -> SandboxAdapter:
    """Get sandbox adapter."""
    return SandboxAdapter()