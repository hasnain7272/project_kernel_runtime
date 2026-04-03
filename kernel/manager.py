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
    """ADK/Codex style: Planner → delegates to Swarm or executes directly"""
    
    # Initialize swarm for complex tasks
    _swarm = None
    
    def _get_swarm(self, context):
        """Lazy init swarm - ADK style sub-agents"""
        if not self._swarm:
            from .swarm import AgentSwarm
            self._swarm = AgentSwarm(
                swarm_id=f"mgr_{id(self)}",
                llm_provider=self.llm,
                event_bus=self.event_bus,
                tool_executor=self.tool_executor
            )
        return self._swarm
    
    def __init__(self, llm_provider, tool_executor, event_bus=None):
        self.llm = llm_provider
        self.tool_executor = tool_executor
        self.event_bus = event_bus
        self._last_summary = None  # Rolling summary - builds incrementally
        self._summary_updated_at = None
        
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
        
        # Get conversation history with rolling compaction (true Codex style)
        conversation_history = []
        if session_id and context.get("session_manager"):
            session = context["session_manager"].get_session(session_id)
            if session and hasattr(session, "conversation_messages"):
                all_messages = session.conversation_messages
                
                # Small conversation - use all
                if len(all_messages) <= 6:
                    conversation_history = all_messages
                    self._last_summary = None  # Reset when conversation small
                else:
                    recent = all_messages[-3:]
                    
                    # Rolling: compact new messages against last summary
                    new_msgs = all_messages[:-3]
                    summary_text = await self._compact_incremental(new_msgs, self._last_summary)
                    self._last_summary = summary_text
                    
                    conversation_history = [{
                        "role": "system", 
                        "content": f"[Context: {summary_text}]"
                    }]
                    conversation_history.extend(recent)
        
        # Get tool schemas - if no tools, LLM gets None (no function definitions)
        # But ALWAYS use full context - like Claude/Codex/ADK
        tool_schemas = self._get_tool_schemas(available_tools) if available_tools else None
        
        # Always use full context - LLM receives tools + history + task + governance
        response = await self._llm_chat(task, tool_schemas, conversation_history, context)
        
        # If LLM used tools - decide: simple vs complex execution
        if response.tool_calls:
            count = len(response.tool_calls)
            session_id = context.get("session_id")
            sm = context.get("session_manager")
            
            # ADK style: Multi-step → delegate to Swarm for parallel execution + orchestration
            if count > 1:
                await self._emit("agent.thinking", {
                    "status": "delegating_to_swarm", 
                    "subtask_count": count,
                    "agents": ["Architect", "Coder", "Researcher", "Reviewer"]
                })
                
                swarm = self._get_swarm(context)
                swarm_result = await swarm.delegate_task(task, {
                    "workspace": workspace,
                    "tools": available_tools,
                    "task": task
                })
                
                # Get results from swarm
                results = list(swarm_result.subtask_results.values())
                result_text = "\n".join(str(r.get("result", r)) for r in results)
                
                await self._emit("agent.thinking", {
                    "status": "swarm_completed",
                    "swarm_id": swarm.swarm_id,
                    "results": len(results)
                })
                
                return {"status": "completed", "response": result_text, "results": swarm_result.subtask_results}
            
            # Single tool - execute directly (fast path)
            await self._emit("agent.thinking", {"status": "executing", "count": 1})
            results = await self._execute_tools(response.tool_calls, workspace, session_id, sm)
            result_text = "\n".join(str(r) for r in results)
            return {"status": "completed", "response": result_text, "results": {}}
        
        # No tools - return LLM conversational response
        return {"status": "completed", "response": response.content or "Done", "results": {}}

    async def _llm_chat(self, task: str, tools: List = None, history: List[Dict] = None,
                    context: Dict = None):
        from project_kernel_runtime.cognition.llm_provider import LLMMessage
        
        # Build governance context from session
        ctx = context or {}
        folders = ctx.get("folders", [])
        skills = ctx.get("skills", [])
        mcp = ctx.get("mcp_servers", [])
        workspace = ctx.get("workspace_path", ".")
        
        gov = self._build_env_context(folders, skills, mcp, workspace)
        
        messages = [LLMMessage(role="system", content=gov)]
        
        # Add conversation history for context
        if history:
            for msg in history:
                messages.append(LLMMessage(role=msg.get("role", "user"), content=msg.get("content", "")))
        
        messages.append(LLMMessage(role="user", content=task))
        return await self.llm.complete(messages=messages, tools=tools, task_type="auto")
    
    async def _compact_incremental(self, new_messages: List[Dict], prev_summary: str = None) -> str:
        """Rolling compaction - use ALL content, no truncation."""
        if not new_messages:
            return prev_summary or "new session"
        
        from project_kernel_runtime.cognition.llm_provider import LLMMessage
        
        system_prompt = "Summarize briefly: tasks done, tools used, outcomes."
        if prev_summary:
            system_prompt = f"Previous context: {prev_summary}\nAdd new:"
        
        summary_msgs = [LLMMessage(role="system", content=system_prompt)]
        
        # Use ALL messages - no truncation
        for msg in new_messages:
            summary_msgs.append(LLMMessage(
                role=msg.get("role", "user"),
                content=msg.get("content", "")
            ))
        
        try:
            result = await self.llm.complete(messages=summary_msgs, task_type="auto")
            return result.content[:300] if result.content else "context summaries complete"
        except:
            return "context from previous interactions"
    
    def _get_tool_schemas(self, available: List[str]) -> List[Dict]:
        from .universal_tools import get_all_tools
        all_tools = get_all_tools()
        filtered = [t for t in all_tools if t.name in available]
        return [{"type": "function", "function": {
            "name": t.name, "description": t.description, "parameters": t.input_schema
        }} for t in filtered]
    
    async def _execute_tools(self, tool_calls, workspace: str, session_id: str = None, session_manager = None) -> List[str]:
        results = []
        for i, tc in enumerate(tool_calls):
            func = tc.get("function", {})
            name = func.get("name", "")
            args = json.loads(func.get("arguments", "{}"))
            
            # Dynamic tool chaining - replace placeholders with previous results
            args_str = json.dumps(args)
            for prev_result in results:
                prev_str = str(prev_result)
                if "{{search_results}}" in args_str:
                    args_str = args_str.replace("{{search_results}}", prev_str)
                if "{{prev_result}}" in args_str:
                    args_str = args_str.replace("{{prev_result}}", prev_str)
            args = json.loads(args_str)
            
            # Emit status for each tool execution
            await self._emit("agent.thinking", {
                "status": "executing", 
                "tool": name,
                "args": args,
                "progress": f"tool {i+1}/{len(tool_calls)}"
            })
            
            result = await self._run_tool(name, args, workspace)
            results.append(result)
            
            # DEBUG: Emit result with raw value to see what happened
            await self._emit("agent.thinking", {
                "status": "result_raw",
                "tool": name,
                "result": str(result)[:500]
            })
            
            # Rolling compaction AFTER each tool (disable for now to debug)
            # if session_id and session_manager:
            #     session = session_manager.get_session(session_id)
            #     if session and hasattr(session, "conversation_messages"):
            #         new_msgs = session.conversation_messages[-3:] if len(session.conversation_messages) > 3 else session.conversation_messages
            #         self._last_summary = await self._compact_incremental(new_msgs, self._last_summary)
            
            # Emit result
            await self._emit("agent.thinking", {
                "status": "result",
                "tool": name,
                "result": str(result)[:200]
            })
        
        return results
    
    async def _run_tool(self, name: str, args: Dict, workspace: str, allowed_folders: List = None) -> str:
        from .tool_executor import ToolCall, ExecutionContext
        tc = ToolCall(name=name, arguments=args)
        # Pass allowed folders for governance - enforce path restrictions
        folders = allowed_folders or [workspace]
        ctx = ExecutionContext(
            workspace_path=workspace,
            enforce_skill_scope=False,
            allowed_folders=folders  # GOV: Enforce folder whitelist
        )
        res = await self.tool_executor.execute(tc, ctx)
        return str(res.output) if res.success else f"Error: {res.error}"

    def _build_env_context(self, folders, skills, mcp_servers, workspace):
        lines = [
            "=== AGENT GOVERNANCE (STRICT) ===",
            f"WORKSPACE: {workspace}"
        ]
        if folders:
            lines.append(f"ALLOWED FOLDERS: {', '.join(folders)}")
        else:
            lines.append(f"ALLOWED: {workspace} (default)")
        
        if skills:
            lines.append(f"SKILLS: {', '.join(skills)}")
        
        lines.extend([
            "",
            "RESTRICTIONS (MUST FOLLOW):",
            "- NEVER use paths like /home/, /root/, C:\\Windows",
            "- NEVER use paths OUTSIDE allowed folders above",
            f"- ONLY use paths that start with: {workspace}",
            "- If you need access to a new folder, ask user FIRST"
        ])
        return "\n".join(lines)

    async def _try_model_fallback(self, task_type):
        if self.llm and self.llm.should_use_external_api(task_type):
            return self.llm.get_model_for_task(task_type)
        return None


_manager = None

def get_manager(llm, tool_executor, event_bus=None):
    global _manager
    if _manager is None:
        _manager = ManagerAgent(llm, tool_executor, event_bus)
    return _manager