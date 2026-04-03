"""
Tool Executor — Central Tool Execution Pipeline

All tool calls flow through this pipeline:
  1. Governance check (is the tool allowed?)
  2. Sandbox routing (does it need isolation?)
  3. Execution (builtin, MCP, or sandboxed)
  4. Audit logging (record what happened)

Inspired by: Claude Code's tool architecture, OpenHands ActionExecutor
"""

import asyncio
import logging
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
from uuid import uuid4
from enum import Enum

logger = logging.getLogger(__name__)


# ============================================================================
# Data Models
# ============================================================================

class ToolMutability(str, Enum):
    """How a tool modifies the environment."""
    READ_ONLY = "read_only"
    WRITE = "write"
    EXECUTE = "execute"
    NETWORK = "network"


@dataclass
class ToolCall:
    """A request to execute a tool."""
    name: str
    arguments: Dict[str, Any]
    id: str = field(default_factory=lambda: str(uuid4()))
    session_id: Optional[str] = None
    task_id: Optional[str] = None
    user_id: str = "system"
    requires_sandbox: bool = False
    is_mcp_tool: bool = False
    mcp_server: Optional[str] = None
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    source: str = "agent"  # agent, tool, workflow, a2a


@dataclass
class ToolResult:
    """Result of a tool execution."""
    tool_call_id: str
    tool_name: str
    success: bool
    output: Any = None
    error: Optional[str] = None
    duration_ms: float = 0.0
    metadata: Dict[str, Any] = field(default_factory=dict)
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    source: str = "agent"  # agent, tool, workflow, a2a


class PolicyDecision(str, Enum):
    """Governance decision for a tool call."""
    ALLOW = "allow"
    DENY = "deny"
    REQUIRE_APPROVAL = "require_approval"


@dataclass
class ExecutionContext:
    """Context for tool execution."""
    session_id: str = ""
    task_id: str = ""
    user_id: str = "system"
    execution_mode: str = "build"
    user_role: str = "developer"
    risk_mode: str = "auto"  # auto, ask, bypass
    workspace_path: str = "."
    environment: Dict[str, Any] = field(default_factory=dict)
    enabled_features: List[str] = field(default_factory=lambda: ["mcp", "skills", "llms", "a2a"])
    enforce_skill_scope: bool = False
    allowed_builtin_tools: List[str] = field(default_factory=list)
    allowed_mcp_servers: List[str] = field(default_factory=list)
    allowed_folders: List[str] = field(default_factory=list)


# ============================================================================
# Tool Executor (Service Hub)
# ============================================================================

class ToolExecutor:
    """
    Central pipeline for all tool execution.
    Acts as a 'Service Hub' for inter-tool and workflow orchestration.
    """
    
    def __init__(self, governance=None, sandbox=None, event_bus=None, mcp_bridge=None):
        self._tools: Dict[str, Any] = {}  # name -> BaseTool instance
        self.governance = governance
        self.sandbox = sandbox
        self.event_bus = event_bus
        self.mcp_bridge = mcp_bridge
        logger.info("[ToolExecutor] Initialized as Service Hub")
    
    def register_tool(self, tool) -> None:
        """Register a tool implementation."""
        self._tools[tool.name] = tool
        logger.debug(f"[ToolExecutor] Registered tool: {tool.name}")
    
    def register_tools(self, tools: list) -> None:
        """Register multiple tool implementations."""
        for tool in tools:
            self.register_tool(tool)
    
    def get_tool(self, name: str):
        """Get a registered tool by name."""
        return self._tools.get(name)
    
    def list_tools(self) -> List[Dict[str, Any]]:
        """List all registered tools with their schemas."""
        tools = []
        for name, tool in self._tools.items():
            tools.append({
                "name": tool.name,
                "description": tool.description,
                "input_schema": tool.input_schema,
                "mutability": getattr(tool, 'mutability', 'read_only'),
                "requires_sandbox": getattr(tool, 'requires_sandbox', False),
            })
        return tools
    
    async def execute(self, tool_call: ToolCall, context: ExecutionContext) -> ToolResult:
        """
        Execute a tool call through the full pipeline.
        
        Pipeline: Governance → Sandbox → Execute → Audit
        With retry on transient failures and non-blocking approval.
        """
        import time
        start_time = time.time()
        
        # ── Step 1: Governance gate ──
        if self.governance:
            decision = await self._check_governance(tool_call, context)
            if decision == PolicyDecision.DENY:
                result = ToolResult(
                    tool_call_id=tool_call.id,
                    tool_name=tool_call.name,
                    success=False,
                    error=f"Governance denied: tool '{tool_call.name}' not allowed",
                    source=getattr(tool_call, "source", "agent")
                )
                await self._emit_event("tool.error", tool_call, result)
                return result
            
            if decision == PolicyDecision.REQUIRE_APPROVAL:
                approval_result = await self._wait_for_approval(tool_call, context)
                if not approval_result:
                    result = ToolResult(
                        tool_call_id=tool_call.id,
                        tool_name=tool_call.name,
                        success=False,
                        error=f"User rejected or timed out tool execution: {tool_call.name}",
                        source=getattr(tool_call, "source", "agent")
                    )
                    await self._emit_event("tool.error", tool_call, result)
                    return result
                
                logger.info(f"[ToolExecutor] Tool approved by human: {tool_call.name}")
        
        # ── Step 2: Emit tool.called event ──
        await self._emit_event("tool.called", tool_call, None)
        
        # ── Step 3: Route and execute with retry ──
        max_retries = 2
        last_error = None
        
        for attempt in range(max_retries + 1):
            try:
                result = await self._execute_tool(tool_call, context)
                result.duration_ms = (time.time() - start_time) * 1000
                result.source = getattr(tool_call, "source", "agent")
                await self._emit_event("tool.result" if result.success else "tool.error", tool_call, result)
                return result
            except Exception as e:
                last_error = e
                is_transient = self._is_transient_error(e)
                
                if is_transient and attempt < max_retries:
                    logger.warning(f"[ToolExecutor] Transient error on '{tool_call.name}' "
                                 f"(attempt {attempt + 1}/{max_retries + 1}): {e}")
                    await asyncio.sleep(0.5 * (attempt + 1))
                    continue
                
                result = ToolResult(
                    tool_call_id=tool_call.id,
                    tool_name=tool_call.name,
                    success=False,
                    error=f"Tool execution error after {attempt + 1} attempt(s): {str(e)}",
                    duration_ms=(time.time() - start_time) * 1000,
                    source=getattr(tool_call, "source", "agent"),
                )
                await self._emit_event("tool.error", tool_call, result)
                return result
    
    async def _wait_for_approval(self, tool_call: ToolCall,
                                  context: ExecutionContext) -> bool:
        """
        Non-blocking approval wait using asyncio.Event pattern.
        Falls back to polling with proper async sleep.
        """
        approval_id = await self.governance.request_approval(
            tool_call.id, tool_call.name, tool_call.arguments, context.user_id
        )
        
        await self._emit_event("governance.approval_required", tool_call, ToolResult(
            tool_call_id=tool_call.id,
            tool_name=tool_call.name,
            success=False,
            metadata={"approval_id": approval_id, "arguments": tool_call.arguments}
        ))
        
        approved = False
        timeout = 300
        waited = 0
        poll_interval = 0.5
        
        while waited < timeout:
            pending = self.governance._pending_approvals.get(approval_id, {})
            status = pending.get("status")
            
            if status == "approved":
                approved = True
                break
            if status == "rejected":
                approved = False
                break
            
            await asyncio.sleep(poll_interval)
            waited += poll_interval
        
        return approved
    
    async def _execute_tool(self, tool_call: ToolCall,
                             context: ExecutionContext) -> ToolResult:
        """Execute the actual tool call (extracted for retry support)."""
        context.environment["service_hub"] = self
        
        if "__" in tool_call.name and getattr(self, "mcp_bridge", None):
            server_name, mcp_tool_name = tool_call.name.split("__", 1)
            result_data = await self.mcp_bridge.call_tool(
                server_name, mcp_tool_name, tool_call.arguments
            )
            return ToolResult(
                tool_call_id=tool_call.id,
                tool_name=tool_call.name,
                success=True,
                output=result_data,
            )
        elif tool_call.name in self._tools:
            tool = self._tools[tool_call.name]
            
            if tool_call.requires_sandbox and self.sandbox:
                output = await self.sandbox.execute_tool(tool, tool_call.arguments, context)
            else:
                output = await tool.execute(tool_call.arguments, context)
            
            return ToolResult(
                tool_call_id=tool_call.id,
                tool_name=tool_call.name,
                success=True,
                output=output,
            )
        else:
            return ToolResult(
                tool_call_id=tool_call.id,
                tool_name=tool_call.name,
                success=False,
                error=f"Unknown tool: '{tool_call.name}'",
            )
    
    @staticmethod
    def _is_transient_error(error: Exception) -> bool:
        """Determine if an error is transient (retryable)."""
        error_str = str(error).lower()
        transient_keywords = [
            "timeout", "timed out", "connection", "refused",
            "temporarily", "busy", "locked", "rate limit",
            "too many", "unavailable", "interrupted",
        ]
        return any(kw in error_str for kw in transient_keywords)
    
    async def call_tool_internal(self, tool_name: str, arguments: Dict,
                                 context: ExecutionContext, source_tool: str) -> ToolResult:
        """
        Service Hub method for inter-tool calls.
        Called by a tool to execute another tool within the same session.
        """
        logger.info(f"[ServiceHub] Internal call: {source_tool} -> {tool_name}")
        call = ToolCall(
            name=tool_name,
            arguments=arguments,
            session_id=context.session_id,
            task_id=context.task_id,
            source=f"tool:{source_tool}"
        )
        return await self.execute(call, context)

    async def execute_batch(self, tool_calls: List[ToolCall],
                            context: ExecutionContext) -> List[ToolResult]:
        """Execute multiple tool calls concurrently."""
        tasks = [self.execute(tc, context) for tc in tool_calls]
        return await asyncio.gather(*tasks)
    
    async def _check_governance(self, tool_call: ToolCall,
                                 context: ExecutionContext) -> PolicyDecision:
        """Check governance policy for a tool call."""
        try:
            # Service Hub bypass: Tools in the same session can call each other if context allows
            if tool_call.source.startswith("tool:") and tool_call.session_id == context.session_id:
                # still check if the target tool is in the session's scope if enforced
                pass

            # 1. Feature Gate for MCP
            if "__" in tool_call.name:
                if "mcp" not in context.enabled_features:
                    return PolicyDecision.DENY
                server_name = tool_call.name.split("__", 1)[0]
                if context.allowed_mcp_servers and server_name not in context.allowed_mcp_servers:
                    return PolicyDecision.DENY
            elif context.enforce_skill_scope and tool_call.name not in context.allowed_builtin_tools:
                return PolicyDecision.DENY

            if not self.governance:
                return PolicyDecision.ALLOW

            tool = self._tools.get(tool_call.name)
            mutability = getattr(tool, 'mutability', ToolMutability.READ_ONLY) if tool else ToolMutability.READ_ONLY
            
            return self.governance.check_permission(
                tool_name=tool_call.name,
                context=context,
                mutability=str(mutability),
            )
        except Exception as e:
            logger.warning(f"[ToolExecutor] Governance check failed: {e}")
            return PolicyDecision.DENY
    
    async def _emit_event(self, event_type: str, tool_call: ToolCall,
                           result: Optional[ToolResult]) -> None:
        """Emit an event through the event bus and UI WebSocket."""
        try:
            payload = {
                "tool_name": tool_call.name,
                "arguments": tool_call.arguments,
                "source": getattr(tool_call, "source", "agent")
            }
            if result:
                payload["success"] = result.success
                payload["duration_ms"] = result.duration_ms
                if result.error:
                    payload["error"] = result.error
            
            # 1. Event Bus
            if self.event_bus:
                from .event_bus import AgentEvent
                event = AgentEvent(
                    type=event_type,
                    payload=payload,
                    source="tool_executor",
                    session_id=tool_call.session_id,
                    task_id=tool_call.task_id,
                )
                await self.event_bus.publish(event)
            
            # 2. UI WebSocket
            from project_kernel_runtime.services.ui_websocket import get_ui_websocket_handler
            handler = get_ui_websocket_handler()
            if handler:
                await handler.broadcaster.broadcast({
                    "type": "event",
                    "event_type": event_type,
                    "session_id": tool_call.session_id,
                    "data": payload
                })
        except Exception as e:
            logger.debug(f"[ToolExecutor] Event emit error: {e}")
