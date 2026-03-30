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
    user_role: str = "developer"
    risk_mode: str = "auto"  # auto, ask, bypass
    workspace_path: str = "."
    environment: Dict[str, str] = field(default_factory=dict)
    enabled_features: List[str] = field(default_factory=lambda: ["mcp", "skills", "llms", "a2a"])


# ============================================================================
# Tool Executor
# ============================================================================

class ToolExecutor:
    """
    Central pipeline for all tool execution.
    
    Every tool call goes through:
    1. Governance gate — check if the tool is allowed
    2. Sandbox routing — run in sandbox if required
    3. Execution — call the actual tool
    4. Audit + Event — log and publish result
    """
    
    def __init__(self, governance=None, sandbox=None, event_bus=None, mcp_bridge=None):
        self._tools: Dict[str, Any] = {}  # name -> BaseTool instance
        self.governance = governance
        self.sandbox = sandbox
        self.event_bus = event_bus
        self.mcp_bridge = mcp_bridge
        logger.info("[ToolExecutor] Initialized")
    
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
                    error=f"Governance denied: tool '{tool_call.name}' not allowed in mode '{context.execution_mode}' for role '{context.user_role}'",
                )
                await self._emit_event("tool.error", tool_call, result)
                return result
            elif decision == PolicyDecision.REQUIRE_APPROVAL:
                result = ToolResult(
                    tool_call_id=tool_call.id,
                    tool_name=tool_call.name,
                    success=False,
                    error=f"Approval required: tool '{tool_call.name}' needs human approval",
                    metadata={"requires_approval": True},
                )
                await self._emit_event("governance.approval_required", tool_call, result)
                return result
        
        # ── Step 2: Emit tool.called event ──
        await self._emit_event("tool.called", tool_call, None)
        
        # ── Step 3: Route and execute ──
        try:
            if "__" in tool_call.name and getattr(self, "mcp_bridge", None):
                # Execute via MCP bridge
                server_name, mcp_tool_name = tool_call.name.split("__", 1)
                result_data = await self.mcp_bridge.call_tool(
                    server_name, mcp_tool_name, tool_call.arguments
                )
                result = ToolResult(
                    tool_call_id=tool_call.id,
                    tool_name=tool_call.name,
                    success=True,
                    output=result_data,
                )
            elif tool_call.name in self._tools:
                # Execute builtin tool
                tool = self._tools[tool_call.name]
                
                if tool_call.requires_sandbox and self.sandbox:
                    # Route through sandbox
                    output = await self.sandbox.execute_tool(tool, tool_call.arguments, context)
                else:
                    # Direct execution
                    output = await tool.execute(tool_call.arguments, context)
                
                result = ToolResult(
                    tool_call_id=tool_call.id,
                    tool_name=tool_call.name,
                    success=True,
                    output=output,
                )
            else:
                result = ToolResult(
                    tool_call_id=tool_call.id,
                    tool_name=tool_call.name,
                    success=False,
                    error=f"Unknown tool: '{tool_call.name}'. Available: {list(self._tools.keys())}",
                )
        
        except asyncio.TimeoutError:
            result = ToolResult(
                tool_call_id=tool_call.id,
                tool_name=tool_call.name,
                success=False,
                error=f"Tool '{tool_call.name}' timed out after {context.environment.get('timeout', '300')}s",
            )
        except Exception as e:
            result = ToolResult(
                tool_call_id=tool_call.id,
                tool_name=tool_call.name,
                success=False,
                error=f"Tool execution error: {type(e).__name__}: {str(e)}",
            )
            logger.error(f"[ToolExecutor] Error executing '{tool_call.name}': {e}", exc_info=True)
        
        # ── Step 4: Record timing and emit result ──
        result.duration_ms = (time.time() - start_time) * 1000
        
        event_type = "tool.result" if result.success else "tool.error"
        await self._emit_event(event_type, tool_call, result)
        
        return result
    
    async def execute_batch(self, tool_calls: List[ToolCall],
                            context: ExecutionContext) -> List[ToolResult]:
        """Execute multiple independent tool calls concurrently."""
        tasks = [self.execute(tc, context) for tc in tool_calls]
        return await asyncio.gather(*tasks)
    
    async def _check_governance(self, tool_call: ToolCall,
                                 context: ExecutionContext) -> PolicyDecision:
        """Check governance policy for a tool call."""
        try:
            # 1. Feature Gate for MCP
            if "__" in tool_call.name:
                if "mcp" not in context.enabled_features:
                    logger.warning(f"[Governance] DENIED: MCP tools are disabled for this session.")
                    return PolicyDecision.DENY

            tool = self._tools.get(tool_call.name)
            mutability = getattr(tool, 'mutability', ToolMutability.READ_ONLY) if tool else ToolMutability.READ_ONLY
            
            decision = self.governance.check_permission(
                tool_name=tool_call.name,
                context=context,
                mutability=str(mutability),
            )
            
            if decision == PolicyDecision.DENY:
                return PolicyDecision.DENY
            
            # Check if tool requires approval
            if hasattr(self.governance, 'requires_approval'):
                if self.governance.requires_approval(tool_call.name):
                    return PolicyDecision.REQUIRE_APPROVAL
            
            return decision
        except Exception as e:
            logger.warning(f"[ToolExecutor] Governance check failed: {e}")
            return PolicyDecision.DENY  # Fail closed
    
    async def _emit_event(self, event_type: str, tool_call: ToolCall,
                           result: Optional[ToolResult]) -> None:
        """Emit an event through the event bus."""
        if not self.event_bus:
            return
        
        try:
            from .event_bus import AgentEvent
            payload = {
                "tool_name": tool_call.name,
                "arguments": tool_call.arguments,
            }
            if result:
                payload["success"] = result.success
                payload["duration_ms"] = result.duration_ms
                if result.error:
                    payload["error"] = result.error
            
            event = AgentEvent(
                type=event_type,
                payload=payload,
                source="tool_executor",
                session_id=tool_call.session_id,
                task_id=tool_call.task_id,
            )
            await self.event_bus.publish(event)
        except Exception as e:
            logger.debug(f"[ToolExecutor] Failed to emit event: {e}")
