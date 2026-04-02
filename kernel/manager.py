"""
Manager - Let LLM decide everything
No hardcoded routing - model decides conversation vs tool use
"""

import json
import logging
from enum import Enum
from typing import Any, Dict, List
from uuid import uuid4

logger = logging.getLogger(__name__)

MAX_TASKS = 3


class AgentType(str, Enum):
    MANAGER = "manager"
    CODER = "coder"
    RESEARCHER = "researcher"
    REVIEWER = "reviewer"
    TESTER = "tester"


class SubTask:
    def __init__(self, id: str = None, description: str = "", 
                 agent_type: AgentType = AgentType.CODER):
        self.id = id or f"st_{uuid4().hex[:6]}"
        self.description = description[:100]
        self.agent_type = agent_type
        self.status = "pending"
        self.result = None


class ManagerAgent:
    """Let LLM decide - no hardcoded logic"""
    
    SYSTEM_PROMPT = """You are a coding assistant. Decide what to do:
- For greetings: respond naturally
- For questions: answer or use tools if needed
- For tasks: use appropriate tools

Don't ask for permission - just do it."""
    
    def __init__(self, llm_provider, tool_executor, event_bus=None):
        self.llm = llm_provider
        self.tool_executor = tool_executor
        self.event_bus = event_bus
        
    async def _emit(self, event: str, data: Dict):
        if self.event_bus:
            try:
                await self.event_bus.emit_and_publish(event, data, source="manager")
            except: pass
        
    async def execute(self, task: str, session_id: str = None,
                      context: Dict = None) -> Dict:
        context = context or {}
        available_tools = context.get("tools", [])
        workspace = context.get("workspace_path", ".")
        
        await self._emit("agent.thinking", {"status": "thinking", "task": task[:30]})
        
        # Get tool schemas if tools available
        tool_schemas = self._get_tool_schemas(available_tools) if available_tools else None
        
        # Ask LLM to decide - conversation or tools
        response = await self._llm_chat(task, tool_schemas)
        
        # If LLM used tools - execute them
        if response.tool_calls:
            results = await self._execute_tools(response.tool_calls, workspace)
            result_text = "\n".join(str(r) for r in results)
            return {"status": "completed", "response": result_text, "results": {}}
        
        # No tools - return LLM response
        return {"status": "completed", "response": response.content or "Done", "results": {}}
    
    async def _llm_chat(self, task: str, tools: List = None):
        from project_kernel_runtime.cognition.llm_provider import LLMMessage
        messages = [
            LLMMessage(role="system", content=self.SYSTEM_PROMPT),
            LLMMessage(role="user", content=task)
        ]
        return await self.llm.complete(messages=messages, tools=tools, task_type="auto")
    
    def _get_tool_schemas(self, available: List[str]) -> List[Dict]:
        from .universal_tools import get_all_tools
        all_tools = get_all_tools()
        filtered = [t for t in all_tools if t.name in available]
        return [{"type": "function", "function": {
            "name": t.name, "description": t.description, "parameters": t.input_schema
        }} for t in filtered]
    
    async def _execute_tools(self, tool_calls, workspace: str) -> List[str]:
        results = []
        for tc in tool_calls:
            func = tc.get("function", {})
            name = func.get("name", "")
            args = json.loads(func.get("arguments", "{}"))
            result = await self._run_tool(name, args, workspace)
            results.append(result)
        return results
    
    async def _run_tool(self, name: str, args: Dict, workspace: str) -> str:
        from .tool_executor import ToolCall, ExecutionContext
        tc = ToolCall(name=name, arguments=args)
        ctx = ExecutionContext(workspace_path=workspace, enforce_skill_scope=False)
        res = await self.tool_executor.execute(tc, ctx)
        return str(res.output) if res.success else f"Error: {res.error}"


_manager = None

def get_manager(llm, tool_executor, event_bus=None):
    global _manager
    if _manager is None:
        _manager = ManagerAgent(llm, tool_executor, event_bus)
    return _manager