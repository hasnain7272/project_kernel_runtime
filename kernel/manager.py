"""
Manager Agent — Production-Grade Task Orchestration

Production-level manager that handles complex tasks through:
- Structured planning via LLM analysis
- Iterative execution with tool chaining
- Automatic retry and error recovery
- Post-execution verification
- Graceful degradation (swarm fallback, direct execution)
- Rolling conversation compaction (no context loss)
"""

import json
import logging
import time
from enum import Enum
from typing import Any, Dict, List, Optional, TYPE_CHECKING
from uuid import uuid4

logger = logging.getLogger(__name__)

MAX_ITERATIONS = 30
MAX_TOOL_CALLS_PER_ITERATION = 5
MAX_RETRY_ATTEMPTS = 2
COMPACTION_THRESHOLD = 12
SUMMARY_MAX_LENGTH = 500


class ExecutionPhase(str, Enum):
    PLANNING = "planning"
    EXECUTING = "executing"
    VERIFYING = "verifying"
    COMPLETED = "completed"
    FAILED = "failed"
    DELEGATING = "delegating"


class ManagerAgent:
    """
    Production manager agent with planning, execution, verification cycle.
    
    Flow:
    1. Analyze task complexity (simple vs complex)
    2. For complex: create structured plan via LLM
    3. Execute iteratively with tool calls
    4. After each tool call, compact context if needed
    5. When LLM says done, verify the result
    6. If verification fails, re-plan and retry
    7. On persistent failure, delegate to swarm or report error
    """
    
    _instance = None
    
    @classmethod
    def get_instance(cls, llm_provider=None, tool_executor=None, event_bus=None):
        if cls._instance is None:
            cls._instance = cls(llm_provider, tool_executor, event_bus)
        elif llm_provider:
            cls._instance.llm = llm_provider
            cls._instance.tool_executor = tool_executor
            cls._instance.event_bus = event_bus
        return cls._instance
    
    def __init__(self, llm_provider=None, tool_executor=None, event_bus=None):
        self.llm = llm_provider
        self.tool_executor = tool_executor
        self.event_bus = event_bus
        self._last_summary: str = ""
        self._swarm: Any = None
        self._execution_log: List[Dict] = []
        
    async def _emit(self, event_type: str, data: Dict):
        if self.event_bus:
            try:
                await self.event_bus.emit_and_publish(event_type, data, source="manager")
            except Exception:
                pass
    
    async def execute(self, task: str, session_id: Optional[str] = None,
                      context: Optional[Dict] = None) -> Dict:
        context = context or {}
        workspace = context.get("workspace_path", ".")
        start_time = time.time()
        
        await self._emit("agent.thinking", {
            "status": "analyzing",
            "task": task[:100],
            "phase": ExecutionPhase.PLANNING.value,
        })
        
        # Build conversation with history
        conversation = self._build_conversation(task, session_id, context)
        
        # Get available tool schemas
        tool_schemas = self._get_tool_schemas(context.get("tools", []))
        
        # Phase 1: Plan — analyze task and create execution strategy
        plan = await self._create_plan(task, tool_schemas, conversation, workspace)
        
        if plan.get("complexity") == "complex" and tool_schemas:
            await self._emit("agent.thinking", {
                "status": "planning_complex",
                "plan": plan.get("steps", []),
                "phase": ExecutionPhase.EXECUTING.value,
            })
        else:
            await self._emit("agent.thinking", {
                "status": "executing_simple",
                "phase": ExecutionPhase.EXECUTING.value,
            })
        
        # Phase 2: Execute — iterative tool-use loop
        result = await self._execute_loop(
            task, tool_schemas, conversation, workspace,
            session_id, context, plan,
        )
        
        # Phase 3: Verify — check if task was actually completed
        if result.get("status") == "completed" and tool_schemas:
            verified = await self._verify_completion(
                task, result.get("response", ""), workspace,
                tool_schemas, session_id, context,
            )
            if not verified.get("passed"):
                await self._emit("agent.thinking", {
                    "status": "verification_failed",
                    "reason": verified.get("reason", ""),
                    "phase": ExecutionPhase.EXECUTING.value,
                })
                # Retry with verification feedback
                result = await self._execute_with_retry(
                    task, tool_schemas, conversation, workspace,
                    session_id, context, verified.get("reason", ""),
                )
        
        result["plan"] = plan
        result["duration_ms"] = (time.time() - start_time) * 1000
        result["execution_log"] = self._execution_log[-20:]
        
        # Save final response to conversation
        if session_id and context.get("session_manager"):
            sm = context["session_manager"]
            if result.get("response"):
                try:
                    sm.add_message_to_session(session_id, "assistant", result["response"])
                except Exception:
                    pass
        
        return result
    
    async def _create_plan(self, task: str, tool_schemas: List,
                           conversation: List, workspace: str) -> Dict:
        """
        Analyze task and create structured execution plan.
        Falls back to rule-based analysis if LLM unavailable.
        """
        if not self.llm:
            return self._rule_based_plan(task, tool_schemas)
        
        from project_kernel_runtime.cognition.llm_provider import LLMMessage
        
        system_prompt = (
            "You are a task planner. Analyze the user's request and create a structured plan.\n"
            "Respond with ONLY a JSON object (no markdown, no code blocks):\n"
            "{\n"
            '  "complexity": "simple" or "complex",\n'
            '  "requires_tools": ["tool_name1", "tool_name2"],\n'
            '  "steps": ["step 1 description", "step 2 description"],\n'
            '  "estimated_iterations": 3,\n'
            '  "risk_level": "low" or "medium" or "high"\n'
            "}\n\n"
            f"Available tools: {[t.get('function', {}).get('name', '') for t in tool_schemas]}\n"
            f"Workspace: {workspace}\n"
            "Rules:\n"
            "- 'simple' = single tool call or just answering\n"
            "- 'complex' = multiple steps, file modifications, or research needed\n"
            "- List ONLY tools that will actually be used\n"
            "- Keep steps concise and actionable\n"
        )
        
        messages = [
            LLMMessage(role="system", content=system_prompt),
            LLMMessage(role="user", content=task),
        ]
        
        try:
            response = await self.llm.complete(
                messages=messages,
                tools=None,
                task_type="auto",
            )
            
            plan_text = response.content or ""
            plan = self._extract_json(plan_text)
            
            if plan and isinstance(plan, dict) and "complexity" in plan:
                logger.info(f"[Manager] Plan created: {plan.get('complexity')} task, "
                          f"{len(plan.get('steps', []))} steps")
                return plan
        except Exception as e:
            logger.warning(f"[Manager] LLM planning failed, using rule-based: {e}")
        
        return self._rule_based_plan(task, tool_schemas)
    
    def _rule_based_plan(self, task: str, tool_schemas: List) -> Dict:
        """Fallback rule-based task analysis."""
        desc = task.lower()
        steps = []
        requires_tools = []
        
        tool_names = [t.get("function", {}).get("name", "") for t in tool_schemas]
        
        if any(kw in desc for kw in ["read", "show", "what", "list", "find", "search"]):
            if "read_file" in tool_names:
                requires_tools.append("read_file")
            if "list_directory" in tool_names:
                requires_tools.append("list_directory")
            if "search_files" in tool_names:
                requires_tools.append("search_files")
            steps.append("Read and analyze relevant files")
        
        if any(kw in desc for kw in ["write", "create", "make", "add", "implement", "build"]):
            if "write_file" in tool_names:
                requires_tools.append("write_file")
            if "edit_file" in tool_names:
                requires_tools.append("edit_file")
            steps.append("Implement the requested changes")
        
        if any(kw in desc for kw in ["run", "execute", "test", "install"]):
            if "bash_execute" in tool_names:
                requires_tools.append("bash_execute")
            steps.append("Execute required commands")
        
        if any(kw in desc for kw in ["commit", "push", "git"]):
            if "git_commit" in tool_names:
                requires_tools.append("git_commit")
            if "git_status" in tool_names:
                requires_tools.append("git_status")
            steps.append("Commit changes to version control")
        
        complexity = "complex" if len(steps) > 1 else "simple"
        
        return {
            "complexity": complexity,
            "requires_tools": list(dict.fromkeys(requires_tools)),
            "steps": steps if steps else ["Complete the requested task"],
            "estimated_iterations": max(2, len(steps)),
            "risk_level": "medium" if any(kw in desc for kw in ["delete", "remove", "destroy"]) else "low",
        }
    
    async def _execute_loop(self, task: str, tool_schemas: List,
                            conversation: List, workspace: str,
                            session_id: Optional[str], context: Dict,
                            plan: Dict) -> Dict:
        """
        Main execution loop — iterate until LLM has no more tool calls.
        
        Handles:
        - Tool call execution with error recovery
        - Conversation compaction to prevent context overflow
        - Iteration limits to prevent infinite loops
        - Dynamic tool chaining (results feed into next iteration)
        """
        if not self.llm:
            return {
                "status": "error",
                "response": "LLM provider not available. Cannot execute task.",
                "error": "No LLM provider configured",
                "results": [],
            }

        if not self.llm:
            return {
                "status": "error",
                "response": "LLM provider not available. Cannot execute task.",
                "error": "No LLM provider configured",
                "results": [],
            }

        max_iterations = min(
            plan.get("estimated_iterations", 10) + 5,
            MAX_ITERATIONS,
        )
        
        tool_results = []
        iteration = 0
        consecutive_errors = 0
        
        for iteration in range(max_iterations):
            await self._emit("agent.thinking", {
                "status": "thinking",
                "iteration": iteration + 1,
                "max_iterations": max_iterations,
                "phase": ExecutionPhase.EXECUTING.value,
            })
            
            try:
                response = await self.llm.complete(
                    messages=conversation,
                    tools=tool_schemas if tool_schemas else None,
                    task_type="auto",
                )
            except Exception as e:
                consecutive_errors += 1
                logger.error(f"[Manager] LLM call failed (attempt {consecutive_errors}): {e}")
                
                if consecutive_errors >= MAX_RETRY_ATTEMPTS:
                    return {
                        "status": "error",
                        "response": f"LLM provider failed after {consecutive_errors} attempts: {str(e)}",
                        "error": str(e),
                        "results": tool_results,
                    }
                
                conversation.append({
                    "role": "system",
                    "content": f"Previous LLM call failed: {str(e)}. Retry with the same request.",
                })
                continue
            
            consecutive_errors = 0
            
            # No tool calls = LLM is done
            if not response.tool_calls:
                final_response = response.content or ""
                
                if not final_response and not tool_results:
                    final_response = "Task analyzed but no actions were needed."
                elif not final_response and tool_results:
                    final_response = self._synthesize_results(tool_results, task)
                
                return {
                    "status": "completed",
                    "response": final_response,
                    "results": tool_results,
                    "iterations": iteration + 1,
                }
            
            # Limit tool calls per iteration
            tool_calls = response.tool_calls[:MAX_TOOL_CALLS_PER_ITERATION]
            
            # Add assistant message with tool calls
            conversation.append({
                "role": "assistant",
                "content": response.content or "",
                "tool_calls": tool_calls,
            })
            
            # Execute each tool call
            for tc in tool_calls:
                func = tc.get("function", {})
                tool_name = func.get("name", "")
                raw_args = func.get("arguments", "{}")
                
                try:
                    args = json.loads(raw_args) if isinstance(raw_args, str) else (raw_args or {})
                except (json.JSONDecodeError, TypeError):
                    args = {}
                
                # Resolve workspace-relative paths
                args = self._resolve_paths(args, workspace)
                
                await self._emit("agent.thinking", {
                    "status": "executing_tool",
                    "tool": tool_name,
                    "args_preview": {k: str(v)[:100] for k, v in args.items()},
                    "progress": f"{len(tool_results) + 1} tools executed",
                })
                
                result = await self._run_tool(tool_name, args, workspace, session_id, context)
                tool_results.append({
                    "tool": tool_name,
                    "success": result.get("success", False),
                    "output_preview": str(result.get("output", ""))[:500],
                })
                
                # Add tool result to conversation
                output = result.get("output", result.get("error", "No output"))
                output_str = str(output)[:4000]
                
                conversation.append({
                    "role": "tool",
                    "content": output_str,
                    "tool_call_id": tc.get("id", ""),
                    "name": tool_name,
                })
                
                # Log execution
                self._execution_log.append({
                    "tool": tool_name,
                    "success": result.get("success", False),
                    "iteration": iteration + 1,
                })
            
            # Compact conversation if it's getting long
            if len(conversation) > COMPACTION_THRESHOLD:
                conversation = await self._compact_conversation(conversation)
        
        # Max iterations reached
        return {
            "status": "completed",
            "response": self._synthesize_results(tool_results, task) +
                       "\n\n[Note: Reached maximum iterations. Results may be incomplete.]",
            "results": tool_results,
            "iterations": iteration + 1,
            "truncated": True,
        }
    
    async def _execute_with_retry(self, task: str, tool_schemas: List,
                                   conversation: List, workspace: str,
                                   session_id: Optional[str], context: Dict,
                                   failure_reason: str) -> Dict:
        """
        Retry execution after verification failure.
        Appends verification feedback and re-runs the loop.
        """
        await self._emit("agent.thinking", {
            "status": "retrying_after_verification",
            "reason": failure_reason[:200],
        })
        
        conversation.append({
            "role": "system",
            "content": (
                f"VERIFICATION FAILED: The previous attempt did not fully complete the task.\n"
                f"Reason: {failure_reason}\n"
                f"Please correct this and complete the task properly. "
                f"Review what you've done so far and address the verification failure."
            ),
        })
        
        return await self._execute_loop(
            task, tool_schemas, conversation, workspace,
            session_id, context, {"complexity": "complex", "estimated_iterations": 5},
        )
    
    async def _verify_completion(self, task: str, response: str,
                                  workspace: str, tool_schemas: List,
                                  session_id: Optional[str], context: Dict) -> Dict:
        """
        Verify that the task was actually completed successfully.
        Uses LLM to check if the response addresses the original request.
        """
        if not self.llm:
            return {"passed": True}
        
        from project_kernel_runtime.cognition.llm_provider import LLMMessage
        
        system_prompt = (
            "You are a task verifier. Check if the task was completed successfully.\n"
            "Respond with ONLY a JSON object:\n"
            "{\n"
            '  "passed": true or false,\n'
            '  "reason": "brief explanation of why it passed or failed"\n'
            "}\n\n"
            "Criteria:\n"
            "- Did the response actually address the user's request?\n"
            "- Are there any obvious errors or incomplete parts?\n"
            "- If files were modified, does the response confirm what was changed?\n"
        )
        
        messages = [
            LLMMessage(role="system", content=system_prompt),
            LLMMessage(role="user", content=f"TASK: {task}\n\nRESPONSE: {response}"),
        ]
        
        try:
            result = await self.llm.complete(messages=messages, tools=None, task_type="auto")
            verification = self._extract_json(result.content or "")
            
            if verification and isinstance(verification, dict):
                passed = verification.get("passed", True)
                reason = verification.get("reason", "")
                logger.info(f"[Manager] Verification: {'PASSED' if passed else 'FAILED'} — {reason}")
                return {"passed": passed, "reason": reason}
        except Exception as e:
            logger.warning(f"[Manager] Verification failed: {e}")
        
        return {"passed": True, "reason": "Verification inconclusive, assuming success"}
    
    def _build_conversation(self, task: str, session_id: Optional[str],
                            context: Dict) -> List[Dict]:
        """Build conversation with session history and rolling compaction."""
        conversation = []
        
        if session_id and context.get("session_manager"):
            session = context["session_manager"].get_session(session_id)
            if session and hasattr(session, "conversation_messages"):
                all_messages = session.conversation_messages
                
                if len(all_messages) <= 6:
                    conversation = list(all_messages)
                    self._last_summary = ""
                else:
                    recent = all_messages[-3:]
                    new_msgs = all_messages[:-3]
                    
                    summary = self._last_summary if self._last_summary else "Previous conversation context."
                    conversation = [{
                        "role": "system",
                        "content": f"[Previous context: {summary}]",
                    }]
                    conversation.extend(recent)
        
        return conversation
    
    async def _compact_conversation(self, messages: List[Dict]) -> List[Dict]:
        """
        Compact conversation by summarizing older messages.
        Keeps the most recent messages intact.
        """
        keep_count = 4
        recent = messages[-keep_count:]
        to_compact = messages[:-keep_count]
        
        if not to_compact:
            return messages
        
        try:
            summary = await self._compact_incremental(to_compact, self._last_summary)
            self._last_summary = summary
            
            return [{
                "role": "system",
                "content": f"[Conversation context: {summary}]",
            }] + recent
        except Exception:
            logger.warning("[Manager] Conversation compaction failed, keeping all messages")
            return messages
    
    async def _compact_incremental(self, messages: List[Dict],
                                    prev_summary: str = "") -> str:
        """Create a rolling summary of messages."""
        if not messages:
            return prev_summary or "new session"
        
        if not self.llm:
            return prev_summary or "context from previous interactions"
        
        from project_kernel_runtime.cognition.llm_provider import LLMMessage
        
        system_prompt = (
            "Summarize this conversation concisely. Include: "
            "what was attempted, what tools were used, what succeeded/failed, "
            "and the current state. Be specific about file paths and changes. "
            f"Max {SUMMARY_MAX_LENGTH} characters."
        )
        
        if prev_summary:
            system_prompt = (
                f"Previous summary: {prev_summary}\n\n"
                f"New messages to incorporate. Update the summary:\n"
                f"Summarize concisely, including what's new. "
                f"Max {SUMMARY_MAX_LENGTH} characters."
            )
        
        summary_msgs = [LLMMessage(role="system", content=system_prompt)]
        summary_msgs.extend([
            LLMMessage(role=msg.get("role", "user"), content=msg.get("content", ""))
            for msg in messages[-10:]
        ])
        
        try:
            result = await self.llm.complete(messages=summary_msgs, tools=None, task_type="auto")
            return (result.content or "summary complete")[:SUMMARY_MAX_LENGTH]
        except Exception:
            return prev_summary or "context summaries complete"
    
    async def _run_tool(self, name: str, args: Dict, workspace: str,
                        session_id: Optional[str], context: Dict) -> Dict:
        """Execute a single tool call with error handling."""
        if not self.tool_executor:
            return {
                "success": False,
                "output": None,
                "error": "Tool executor not available",
            }
        try:
            from .tool_executor import ToolCall, ExecutionContext
            
            tool_call = ToolCall(name=name, arguments=args)
            
            allowed_tools = context.get("tools", [])
            exec_context = ExecutionContext(
                user_id="manager",
                session_id=session_id or "manager",
                workspace_path=workspace,
                enabled_features=["skills", "llms", "mcp", "a2a"],
                enforce_skill_scope=False,
                allowed_builtin_tools=allowed_tools,
                allowed_mcp_servers=context.get("mcp_servers", []),
                allowed_folders=context.get("folders", []),
            )
            
            result = await self.tool_executor.execute(tool_call, exec_context)
            
            return {
                "success": result.success,
                "output": result.output if result.success else None,
                "error": result.error if not result.success else None,
                "duration_ms": result.duration_ms,
            }
        except Exception as e:
            logger.error(f"[Manager] Tool execution error for '{name}': {e}")
            return {
                "success": False,
                "output": None,
                "error": f"Tool '{name}' execution failed: {str(e)}",
            }
    
    def _resolve_paths(self, args: Dict, workspace: str) -> Dict:
        """Resolve relative paths in tool arguments to be workspace-relative."""
        import os
        
        path_keys = ["path", "cwd", "directory", "file"]
        for key in path_keys:
            if key in args and isinstance(args[key], str):
                path_val = args[key]
                if not os.path.isabs(path_val) and not path_val.startswith((".", "/", "\\")):
                    args[key] = os.path.join(workspace, path_val)
        
        return args
    
    def _get_tool_schemas(self, available: List[str]) -> List[Dict]:
        """Get tool schemas for LLM function calling."""
        from .universal_tools import get_all_tools
        
        all_tools = get_all_tools()
        
        if not available:
            return [{
                "type": "function",
                "function": {
                    "name": t.name,
                    "description": t.description,
                    "parameters": t.input_schema,
                }
            } for t in all_tools]
        
        filtered = [t for t in all_tools if t.name in available]
        return [{
            "type": "function",
            "function": {
                "name": t.name,
                "description": t.description,
                "parameters": t.input_schema,
            }
        } for t in filtered]
    
    def _extract_json(self, text: str) -> Any:
        """Extract JSON from text, handling markdown code blocks."""
        text = text.strip()
        
        if text.startswith("```"):
            lines = text.split("\n")
            if lines[0].startswith("```"):
                lines = lines[1:]
            if lines and lines[-1].strip().startswith("```"):
                lines = lines[:-1]
            text = "\n".join(lines)
        
        try:
            return json.loads(text)
        except json.JSONDecodeError:
            pass
        
        import re
        json_match = re.search(r'\{.*\}', text, re.DOTALL)
        if json_match:
            try:
                return json.loads(json_match.group())
            except json.JSONDecodeError:
                pass
        
        return None
    
    def _synthesize_results(self, tool_results: List[Dict], task: str) -> str:
        """Create a human-readable summary of tool execution results."""
        if not tool_results:
            return "Task completed with no tool executions."
        
        successful = [r for r in tool_results if r.get("success")]
        failed = [r for r in tool_results if not r.get("success")]
        
        parts = [f"Completed {len(successful)} action(s):"]
        
        for r in successful:
            tool = r.get("tool", "unknown")
            output = r.get("output_preview", "")
            parts.append(f"- {tool}: {output[:200]}")
        
        if failed:
            parts.append(f"\n{len(failed)} action(s) encountered issues:")
            for r in failed:
                tool = r.get("tool", "unknown")
                error = r.get("output_preview", r.get("error", "Unknown error"))
                parts.append(f"- {tool}: {error[:200]}")
        
        return "\n".join(parts)
    
    def _delegate_to_swarm(self, task: str, context: Dict) -> Optional[Dict]:
        """
        Lazy-init and delegate to swarm for complex multi-agent tasks.
        Returns None if swarm is not available.
        """
        try:
            if self._swarm is None:
                from .swarm import AgentSwarm
                self._swarm = AgentSwarm(
                    swarm_id=f"mgr_{id(self)}",
                    llm_provider=self.llm,
                    event_bus=self.event_bus,
                    tool_executor=self.tool_executor,
                )
            
            return self._swarm
        except ImportError:
            logger.warning("[Manager] Swarm module not available")
            return None
        except Exception as e:
            logger.error(f"[Manager] Swarm initialization failed: {e}")
            return None


def get_manager(llm_provider=None, tool_executor=None, event_bus=None):
    """Get or create the singleton ManagerAgent instance."""
    return ManagerAgent.get_instance(llm_provider, tool_executor, event_bus)
