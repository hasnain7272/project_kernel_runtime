"""
Agent Swarm v3 — Production Multi-Agent Orchestration

Production-grade swarm with:
- LLM-driven task decomposition (not keyword matching)
- True dependency-aware execution (DAG-based)
- Per-agent retry and error recovery
- Inter-agent result passing
- Adaptive agent selection based on capabilities
- Real-time progress emission
"""

import asyncio
import json
import logging
import time
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Callable, Dict, List, Optional, Set
from uuid import uuid4

logger = logging.getLogger(__name__)

MAX_SUBTASK_ITERATIONS = 8
MAX_DECOMPOSE_RETRIES = 2
PARALLEL_BATCH_SIZE = 4


class AgentRole(str, Enum):
    ARCHITECT = "architect"
    CODER = "coder"
    REVIEWER = "reviewer"
    TESTER = "tester"
    RESEARCHER = "researcher"


@dataclass
class SwarmAgent:
    name: str
    role: AgentRole
    capabilities: List[str]
    system_prompt: str = ""
    status: str = "idle"
    task_count: int = 0
    success_count: int = 0
    error_count: int = 0
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "role": self.role.value,
            "capabilities": self.capabilities,
            "status": self.status,
            "task_count": self.task_count,
            "success_count": self.success_count,
            "error_count": self.error_count,
        }


@dataclass
class SubTask:
    id: str = field(default_factory=lambda: f"st_{uuid4().hex[:6]}")
    description: str = ""
    assigned_agent: Optional[str] = None
    required_role: AgentRole = AgentRole.CODER
    required_skills: List[str] = field(default_factory=list)
    dependencies: List[str] = field(default_factory=list)
    status: str = "pending"
    result: Any = None
    error: Optional[str] = None
    retry_count: int = 0
    context_from_deps: Dict[str, str] = field(default_factory=dict)


@dataclass
class SwarmResult:
    swarm_id: str
    subtask_results: Dict[str, Any] = field(default_factory=dict)
    status: str = "completed"
    total_subtasks: int = 0
    successful: int = 0
    failed: int = 0
    skipped: int = 0
    duration_ms: float = 0.0
    summary: str = ""


DEFAULT_AGENTS = [
    SwarmAgent(
        name="Architect",
        role=AgentRole.ARCHITECT,
        capabilities=["read_file", "search_files", "list_directory", "web_search", "git_status", "git_diff"],
        system_prompt=(
            "You are a Software Architect. Analyze requirements, understand existing code structure, "
            "and produce a clear implementation plan. Read files to understand the codebase before "
            "recommending changes. Be specific about what files to modify and how."
        ),
    ),
    SwarmAgent(
        name="Coder",
        role=AgentRole.CODER,
        capabilities=["read_file", "write_file", "edit_file", "bash_execute", "search_files", "list_directory"],
        system_prompt=(
            "You are a Senior Developer. Implement changes precisely and efficiently. "
            "Read files before editing. Use edit_file for small changes, write_file for new files. "
            "Verify changes with bash_execute when possible. Make minimal, focused changes."
        ),
    ),
    SwarmAgent(
        name="Reviewer",
        role=AgentRole.REVIEWER,
        capabilities=["read_file", "search_files", "git_diff", "git_status", "list_directory"],
        system_prompt=(
            "You are a Code Reviewer. Review code for bugs, security issues, performance problems, "
            "and style inconsistencies. Read the actual code before reviewing. "
            "Provide specific, actionable feedback with line references when possible."
        ),
    ),
    SwarmAgent(
        name="Tester",
        role=AgentRole.TESTER,
        capabilities=["read_file", "write_file", "bash_execute", "search_files", "list_directory"],
        system_prompt=(
            "You are a QA Engineer. Write and run tests to verify correctness. "
            "Read existing test files to understand the testing patterns. "
            "Create tests that cover edge cases. Report pass/fail results clearly."
        ),
    ),
    SwarmAgent(
        name="Researcher",
        role=AgentRole.RESEARCHER,
        capabilities=["web_search", "web_fetch", "read_file", "search_files"],
        system_prompt=(
            "You are a Technical Researcher. Gather information from the web and codebase "
            "to answer questions and inform decisions. Cite sources. Distinguish between "
            "confirmed facts and speculation."
        ),
    ),
]


class AgentSwarm:
    """
    Production multi-agent swarm with LLM-driven decomposition and DAG execution.
    
    Pipeline:
    1. LLM decomposes task into subtasks with dependencies
    2. Subtasks assigned to best-fit agents
    3. Execute in dependency order (parallel where possible)
    4. Pass results between dependent subtasks
    5. Aggregate and summarize
    """
    
    def __init__(self, swarm_id: str = None, llm_provider=None, event_bus=None, tool_executor=None):
        self.swarm_id = swarm_id or f"swarm_{uuid4().hex[:8]}"
        self.agents: List[SwarmAgent] = [SwarmAgent(**a.__dict__) for a in DEFAULT_AGENTS]
        self.llm_provider = llm_provider
        self.event_bus = event_bus
        self.tool_executor = tool_executor
        self.active_tasks: Dict[str, SubTask] = {}
        self._task_history: List[SwarmResult] = []
        logger.info(f"[Swarm:{self.swarm_id}] Initialized with {len(self.agents)} agents")
    
    async def _emit(self, event_type: str, data: Dict):
        if self.event_bus:
            try:
                await self.event_bus.emit_and_publish(event_type, data, source=f"swarm:{self.swarm_id}")
            except Exception:
                pass
    
    async def delegate_task(self, task_description: str,
                            context: Dict[str, Any] = None) -> SwarmResult:
        """
        Full swarm execution pipeline.
        """
        import time
        start_time = time.time()
        ctx = context or {}
        
        await self._emit("agent.thinking", {
            "status": "swarm_decomposing",
            "task": task_description[:100],
            "swarm_id": self.swarm_id,
        })
        
        # Step 1: Decompose with retry
        subtasks = await self._decompose_with_retry(task_description, ctx)
        
        if not subtasks:
            return SwarmResult(
                swarm_id=self.swarm_id,
                status="failed",
                total_subtasks=0,
                failed=1,
                summary="Task decomposition failed",
            )
        
        await self._emit("agent.thinking", {
            "status": "swarm_assigning",
            "subtask_count": len(subtasks),
            "swarm_id": self.swarm_id,
        })
        
        # Step 2: Assign agents
        self._assign_agents(subtasks)
        
        # Step 3: Execute with dependency awareness
        results = await self._execute_dag(subtasks, ctx)
        
        # Step 4: Reset agent statuses
        for agent in self.agents:
            agent.status = "idle"
        
        # Step 5: Aggregate
        successful = sum(1 for r in results.values() if r.get("status") == "completed")
        failed = sum(1 for r in results.values() if r.get("status") == "failed")
        skipped = sum(1 for r in results.values() if r.get("status") == "skipped")
        
        summary = self._aggregate_summary(subtasks, results)
        
        swarm_result = SwarmResult(
            swarm_id=self.swarm_id,
            subtask_results=results,
            status="completed" if failed == 0 else "partial",
            total_subtasks=len(subtasks),
            successful=successful,
            failed=failed,
            skipped=skipped,
            duration_ms=(time.time() - start_time) * 1000,
            summary=summary,
        )
        
        self._task_history.append(swarm_result)
        
        await self._emit("agent.thinking", {
            "status": "swarm_completed",
            "swarm_id": self.swarm_id,
            "total": len(subtasks),
            "successful": successful,
            "failed": failed,
            "summary": summary[:300],
        })
        
        return swarm_result
    
    async def _decompose_with_retry(self, description: str,
                                     context: Dict) -> List[SubTask]:
        """LLM-driven decomposition with retry."""
        for attempt in range(MAX_DECOMPOSE_RETRIES + 1):
            try:
                subtasks = await self._llm_decompose(description, context)
                if subtasks:
                    return subtasks
            except Exception as e:
                logger.warning(f"[Swarm] Decompose attempt {attempt + 1} failed: {e}")
        
        logger.warning("[Swarm] LLM decomposition failed, using rule-based fallback")
        return self._rule_based_decompose(description)
    
    async def _llm_decompose(self, description: str, context: Dict) -> List[SubTask]:
        """
        Use LLM to decompose task into subtasks with dependencies.
        
        Returns list of SubTask objects with proper dependency graph.
        """
        if not self.llm_provider:
            return []
        
        from project_kernel_runtime.cognition.llm_provider import LLMMessage
        
        system_prompt = (
            "You are a task decomposition engine. Break down complex tasks into "
            "smaller, executable subtasks.\n\n"
            "Respond with ONLY a JSON array (no markdown, no code blocks):\n"
            "[\n"
            "  {\n"
            '    "description": "Clear description of what to do",\n'
            '    "role": "architect|coder|reviewer|tester|researcher",\n'
            '    "skills": ["tool_name1", "tool_name2"],\n'
            '    "dependencies": []\n'
            "  }\n"
            "]\n\n"
            "Rules:\n"
            "- 'dependencies' is a list of 0-based indices of subtasks this one depends on\n"
            "- First subtasks should have empty dependencies\n"
            "- Each subtask should be independently executable\n"
            "- Use the minimum number of subtasks needed\n"
            "- 'skills' should be actual tool names: read_file, write_file, edit_file, "
            "search_files, list_directory, bash_execute, git_status, git_diff, git_commit, "
            "git_log, web_search, web_fetch\n"
            "- Order matters: research before architecture, architecture before coding, "
            "coding before testing, testing before review"
        )
        
        messages = [
            LLMMessage(role="system", content=system_prompt),
            LLMMessage(role="user", content=f"Decompose this task: {description}"),
        ]
        
        response = await self.llm_provider.complete(messages=messages, tools=None, task_type="auto")
        
        tasks_json = self._extract_json_array(response.content or "")
        if not tasks_json:
            return []
        
        subtasks = []
        role_map = {
            "architect": AgentRole.ARCHITECT,
            "coder": AgentRole.CODER,
            "reviewer": AgentRole.REVIEWER,
            "tester": AgentRole.TESTER,
            "researcher": AgentRole.RESEARCHER,
        }
        
        for i, task_data in enumerate(tasks_json):
            if not isinstance(task_data, dict):
                continue
            
            role_str = task_data.get("role", "coder").lower()
            role = role_map.get(role_str, AgentRole.CODER)
            
            deps = task_data.get("dependencies", [])
            if isinstance(deps, list):
                dep_ids = []
                for d in deps:
                    if isinstance(d, int) and 0 <= d < i:
                        dep_ids.append(f"st_{d:03d}")
            else:
                dep_ids = []
            
            subtask = SubTask(
                id=f"st_{i:03d}",
                description=task_data.get("description", ""),
                required_role=role,
                required_skills=task_data.get("skills", []),
                dependencies=dep_ids,
            )
            subtasks.append(subtask)
        
        return subtasks if subtasks else []
    
    def _rule_based_decompose(self, description: str) -> List[SubTask]:
        """Fallback rule-based decomposition."""
        desc_lower = description.lower()
        subtasks = []
        
        if any(kw in desc_lower for kw in ["research", "find", "search", "learn", "investigate", "what is", "how to"]):
            subtasks.append(SubTask(
                id="st_000",
                description=f"Research and gather information: {description}",
                required_role=AgentRole.RESEARCHER,
                required_skills=["web_search", "web_fetch", "read_file"],
            ))
        
        if any(kw in desc_lower for kw in ["design", "architect", "plan", "structure", "analyze"]):
            dep_ids = [st.id for st in subtasks]
            subtasks.append(SubTask(
                id=f"st_{len(subtasks):03d}",
                description=f"Analyze and plan approach: {description}",
                required_role=AgentRole.ARCHITECT,
                required_skills=["read_file", "search_files", "list_directory"],
                dependencies=dep_ids,
            ))
        
        if any(kw in desc_lower for kw in ["implement", "code", "build", "create", "write", "add", "fix", "update", "make", "change", "modify"]):
            dep_ids = [st.id for st in subtasks if st.required_role in (AgentRole.RESEARCHER, AgentRole.ARCHITECT)]
            subtasks.append(SubTask(
                id=f"st_{len(subtasks):03d}",
                description=f"Implement: {description}",
                required_role=AgentRole.CODER,
                required_skills=["read_file", "write_file", "edit_file"],
                dependencies=dep_ids,
            ))
        
        if any(kw in desc_lower for kw in ["test", "verify", "validate", "check it works"]):
            dep_ids = [st.id for st in subtasks if st.required_role == AgentRole.CODER]
            subtasks.append(SubTask(
                id=f"st_{len(subtasks):03d}",
                description=f"Test and verify: {description}",
                required_role=AgentRole.TESTER,
                required_skills=["read_file", "write_file", "bash_execute"],
                dependencies=dep_ids if dep_ids else [st.id for st in subtasks],
            ))
        
        if any(kw in desc_lower for kw in ["review", "audit", "inspect", "check for"]):
            dep_ids = [st.id for st in subtasks]
            subtasks.append(SubTask(
                id=f"st_{len(subtasks):03d}",
                description=f"Review: {description}",
                required_role=AgentRole.REVIEWER,
                required_skills=["read_file", "git_diff", "search_files"],
                dependencies=dep_ids,
            ))
        
        if not subtasks:
            subtasks.append(SubTask(
                id="st_000",
                description=description,
                required_role=AgentRole.CODER,
                required_skills=["read_file", "write_file", "edit_file", "bash_execute"],
            ))
        
        return subtasks
    
    def _assign_agents(self, subtasks: List[SubTask]):
        """Assign each subtask to the best available agent."""
        assigned_roles: Dict[AgentRole, int] = {}
        
        for subtask in subtasks:
            agent = self._find_best_agent(subtask, assigned_roles)
            if agent:
                subtask.assigned_agent = agent.name
                agent.status = "working"
                agent.task_count += 1
                assigned_roles[subtask.required_role] = assigned_roles.get(subtask.required_role, 0) + 1
            else:
                subtask.assigned_agent = "Fallback"
    
    def _find_best_agent(self, subtask: SubTask,
                         assigned_roles: Dict[AgentRole, int]) -> Optional[SwarmAgent]:
        """Find best idle agent for subtask, allowing reuse if needed."""
        for agent in self.agents:
            if agent.role == subtask.required_role:
                return agent
        
        for agent in self.agents:
            has_skills = any(s in agent.capabilities for s in subtask.required_skills)
            if has_skills:
                return agent
        
        return self.agents[0] if self.agents else None
    
    async def _execute_dag(self, subtasks: List[SubTask],
                           context: Dict) -> Dict[str, Any]:
        """
        Execute subtasks respecting dependency order.
        Parallel execution for independent subtasks.
        """
        results: Dict[str, Any] = {}
        completed_ids: Set[str] = set()
        failed_ids: Set[str] = set()
        
        subtask_map = {st.id: st for st in subtasks}
        remaining = list(subtasks)
        
        while remaining:
            ready = []
            waiting = []
            
            for st in remaining:
                deps_met = all(d in completed_ids for d in st.dependencies)
                deps_failed = any(d in failed_ids for d in st.dependencies)
                
                if deps_failed:
                    st.status = "skipped"
                    st.error = "Dependency failed"
                    results[st.id] = {"status": "skipped", "error": "Dependency failed"}
                    failed_ids.add(st.id)
                elif deps_met:
                    ready.append(st)
                else:
                    waiting.append(st)
            
            if not ready:
                for st in waiting:
                    st.status = "skipped"
                    st.error = "Unresolvable dependencies"
                    results[st.id] = {"status": "skipped", "error": "Unresolvable dependencies"}
                break
            
            # Build context from dependencies
            for st in ready:
                st.context_from_deps = {}
                for dep_id in st.dependencies:
                    dep_result = results.get(dep_id, {})
                    dep_st = subtask_map.get(dep_id)
                    if dep_st and dep_st.result:
                        st.context_from_deps[dep_id] = str(dep_st.result)[:1000]
            
            # Execute ready subtasks in parallel (batched)
            for i in range(0, len(ready), PARALLEL_BATCH_SIZE):
                batch = ready[i:i + PARALLEL_BATCH_SIZE]
                
                tasks = [self._execute_subtask_with_retry(st, context) for st in batch]
                batch_results = await asyncio.gather(*tasks, return_exceptions=True)
                
                for st, result in zip(batch, batch_results):
                    if isinstance(result, Exception):
                        st.status = "failed"
                        st.error = str(result)
                        results[st.id] = {"status": "failed", "error": str(result)}
                        failed_ids.add(st.id)
                    elif isinstance(result, dict) and result.get("status") == "failed":
                        st.status = "failed"
                        st.error = result.get("error", "Unknown error")
                        results[st.id] = result
                        failed_ids.add(st.id)
                    else:
                        st.status = "completed"
                        st.result = result if isinstance(result, str) else result.get("result", "")
                        results[st.id] = {"status": "completed", "result": st.result}
                        completed_ids.add(st.id)
            
            remaining = waiting
        
        return results
    
    async def _execute_subtask_with_retry(self, subtask: SubTask,
                                           context: Dict) -> Any:
        """Execute subtask with automatic retry on failure."""
        max_retries = 2
        last_error = None
        
        for attempt in range(max_retries + 1):
            if attempt > 0:
                await self._emit("agent.thinking", {
                    "status": "swarm_retry",
                    "subtask": subtask.id,
                    "attempt": attempt + 1,
                    "error": str(last_error)[:200],
                })
            
            try:
                result = await self._execute_subtask(subtask, context)
                return result
            except Exception as e:
                last_error = e
                logger.warning(f"[Swarm] Subtask {subtask.id} attempt {attempt + 1} failed: {e}")
                await asyncio.sleep(1)
        
        return {"status": "failed", "error": f"Failed after {max_retries + 1} attempts: {str(last_error)}"}
    
    async def _execute_subtask(self, subtask: SubTask,
                                context: Dict) -> str:
        """Execute a single subtask with role-specific LLM loop."""
        subtask.status = "running"
        agent_name = subtask.assigned_agent or "Agent"
        agent_role = subtask.required_role
        workspace = context.get("workspace_path", ".")
        
        agent = next((a for a in self.agents if a.name == agent_name), None)
        system_prompt = agent.system_prompt if agent else (
            "You are a helpful coding assistant. Use tools to complete tasks."
        )
        
        if subtask.context_from_deps:
            dep_context = "\n".join(
                f"From {dep_id}: {ctx[:500]}"
                for dep_id, ctx in subtask.context_from_deps.items()
            )
            system_prompt += f"\n\nContext from previous steps:\n{dep_context}"
        
        system_prompt += f"\n\nWorkspace: {workspace}"
        
        await self._emit("agent.thinking", {
            "status": "swarm_executing",
            "agent": agent_name,
            "role": agent_role.value,
            "subtask": subtask.description[:100],
        })
        
        if not self.llm_provider:
            return f"[{agent_name}] Task acknowledged (no LLM available)"
        
        from project_kernel_runtime.cognition.llm_provider import LLMMessage
        
        conversation = [
            LLMMessage(role="system", content=system_prompt),
            LLMMessage(role="user", content=subtask.description),
        ]
        
        tools_for_agent = self._build_tool_schemas(subtask.required_skills)
        
        result_text = ""
        for iteration in range(MAX_SUBTASK_ITERATIONS):
            try:
                response = await self.llm_provider.complete(
                    messages=conversation,
                    tools=tools_for_agent if tools_for_agent else None,
                    task_type="code_generation",
                )
            except Exception as e:
                result_text = f"LLM error: {str(e)}"
                break
            
            if not response.tool_calls:
                result_text = response.content or "(no response)"
                break
            
            conversation.append(LLMMessage(
                role="assistant",
                content=response.content or "",
                tool_calls=response.tool_calls,
            ))
            
            for tc in response.tool_calls:
                func = tc.get("function", {})
                tool_name = func.get("name", "")
                raw_args = func.get("arguments", "{}")
                
                try:
                    args = json.loads(raw_args) if isinstance(raw_args, str) else (raw_args or {})
                except (json.JSONDecodeError, TypeError):
                    args = {}
                
                output = await self._execute_tool_call(tool_name, args, workspace, context)
                
                conversation.append(LLMMessage(
                    role="tool",
                    content=output[:2000],
                    tool_call_id=tc.get("id", ""),
                    name=tool_name,
                ))
            
            result_text = response.content or "Tools executed"
        
        subtask.status = "completed"
        
        if agent:
            agent.success_count += 1
        
        return f"[{agent_name}] {result_text}"
    
    async def _execute_tool_call(self, tool_name: str, args: Dict,
                                  workspace: str, context: Dict) -> str:
        """Execute a single tool call via tool_executor."""
        if not self.tool_executor:
            return f"Tool '{tool_name}' not available (no executor)"
        
        try:
            from .tool_executor import ToolCall, ExecutionContext
            
            tool_call = ToolCall(name=tool_name, arguments=args)
            exec_ctx = ExecutionContext(
                user_id="swarm",
                session_id=context.get("session_id", "swarm"),
                workspace_path=workspace,
                enabled_features=["skills", "llms", "mcp"],
                enforce_skill_scope=False,
            )
            
            result = await self.tool_executor.execute(tool_call, exec_ctx)
            return str(result.output) if result.success else f"Error: {result.error}"
        except Exception as e:
            return f"Tool execution error: {str(e)}"
    
    def _build_tool_schemas(self, skills: List[str]) -> List[Dict]:
        """Build tool schemas for a set of skill names."""
        if not self.tool_executor:
            return []
        
        schemas = []
        for skill_name in skills:
            tool = self.tool_executor.get_tool(skill_name)
            if tool:
                schemas.append({
                    "type": "function",
                    "function": {
                        "name": tool.name,
                        "description": tool.description,
                        "parameters": tool.input_schema,
                    }
                })
        
        if not schemas and self.tool_executor:
            all_tools = self.tool_executor.list_tools()
            schemas = [{
                "type": "function",
                "function": {
                    "name": t["name"],
                    "description": t["description"],
                    "parameters": t["input_schema"],
                }
            } for t in all_tools[:8]]
        
        return schemas
    
    def _aggregate_summary(self, subtasks: List[SubTask],
                           results: Dict[str, Any]) -> str:
        """Create a human-readable summary of swarm execution."""
        if not subtasks:
            return "No subtasks were created."
        
        completed = [st for st in subtasks if st.status == "completed"]
        failed = [st for st in subtasks if st.status == "failed"]
        skipped = [st for st in subtasks if st.status == "skipped"]
        
        parts = []
        
        if completed:
            parts.append(f"Completed {len(completed)} of {len(subtasks)} subtasks:")
            for st in completed:
                result_preview = str(st.result)[:150] if st.result else "done"
                parts.append(f"  [{st.assigned_agent}] {st.description[:80]}: {result_preview}")
        
        if failed:
            parts.append(f"\nFailed {len(failed)} subtasks:")
            for st in failed:
                parts.append(f"  [{st.assigned_agent}] {st.description[:80]}: {st.error or 'unknown error'}")
        
        if skipped:
            parts.append(f"\nSkipped {len(skipped)} subtasks (dependency failures)")
        
        return "\n".join(parts)
    
    def _extract_json_array(self, text: str) -> Optional[List]:
        """Extract JSON array from text."""
        text = text.strip()
        
        if text.startswith("```"):
            lines = text.split("\n")
            if lines[0].startswith("```"):
                lines = lines[1:]
            if lines and lines[-1].strip().startswith("```"):
                lines = lines[:-1]
            text = "\n".join(lines)
        
        try:
            parsed = json.loads(text)
            return parsed if isinstance(parsed, list) else None
        except json.JSONDecodeError:
            pass
        
        import re
        json_match = re.search(r'\[.*\]', text, re.DOTALL)
        if json_match:
            try:
                return json.loads(json_match.group())
            except json.JSONDecodeError:
                pass
        
        return None
    
    def get_swarm_status(self) -> List[Dict[str, Any]]:
        return [a.to_dict() for a in self.agents]
    
    def get_history(self) -> List[Dict[str, Any]]:
        return [
            {
                "swarm_id": r.swarm_id,
                "total": r.total_subtasks,
                "successful": r.successful,
                "failed": r.failed,
                "skipped": r.skipped,
                "duration_ms": r.duration_ms,
                "summary": r.summary[:200],
            }
            for r in self._task_history[-20:]
        ]
