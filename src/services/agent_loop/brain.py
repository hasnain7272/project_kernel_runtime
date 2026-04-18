"""
The Cognition Worker (Brain)

Event-driven, single-shot. On each AGENT_THINK event:
1. Load BYOK config from SessionModel.context
2. Build context from DB
3. Call LLM with tool schemas (dynamic provider)
4. If tool_calls → persist + emit EXECUTE_TOOL for each
5. If plain text → persist + emit TASK_RESOLVED
6. ToolWorker will feed results back as AGENT_THINK (ReAct loop)
"""
import json
import logging
import os
import re
from typing import Dict, Any, List

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.infrastructure.llm.litellm_client import LLMClient
from src.infrastructure.queue.redis_streams_broker import get_streams_broker
from src.infrastructure.observability.tracing import traced, create_task_span
from src.infrastructure.db.models.task_model import TaskModel
from src.infrastructure.db.models.session_model import SessionModel
from src.infrastructure.resilience.circuit_breaker import CircuitBreaker, CircuitBreakerConfig, CircuitBreakerOpenError
from src.services.memory.context_builder import (
    build_llm_context,
    persist_message,
)

logger = logging.getLogger(__name__)

from src.tools.registry import get_all_tool_schemas

_broker = None

async def _get_broker():
    global _broker
    if _broker is None:
        _broker = await get_streams_broker()
    return _broker

def _extract_heuristic_tool_calls(text: str) -> List[Dict[str, Any]]:
    """
    NemoClaw Hybrid Parser:
    Extracts embedded JSON action payloads when the LLM outputs tool calls as plaintext.
    Uses balanced-brace matching instead of greedy regex for reliability.
    Validates extracted tool names against the actual registry.
    """
    calls = []
    
    # Get valid tool names from registry to validate against
    from src.tools.registry import get_tool_names
    valid_names = set(get_tool_names())
    
    # Find all top-level JSON objects using balanced brace matching
    json_blocks = _find_json_blocks(text)
    
    for block in json_blocks:
        try:
            parsed = json.loads(block)
            if not isinstance(parsed, dict):
                continue
            actions = parsed.get("actions")
            if not isinstance(actions, list):
                continue
            for act in actions:
                if not isinstance(act, dict):
                    continue
                action_name = act.get("action") or act.get("tool") or act.get("name")
                if action_name and action_name in valid_names:
                    args = {k: v for k, v in act.items() if k not in ["action", "tool", "name"]}
                    calls.append({
                        "type": "function",
                        "function": {
                            "name": action_name,
                            "arguments": json.dumps(args),
                        }
                    })
                elif action_name:
                    logger.warning(f"[HeuristicParser] Ignoring unknown tool '{action_name}' from text extraction")
        except (json.JSONDecodeError, ValueError):
            continue
    
    if calls:
        logger.info(f"[HeuristicParser] Extracted {len(calls)} tool calls from plaintext")
    return calls


def _find_json_blocks(text: str) -> List[str]:
    """Extract top-level JSON object strings using balanced brace matching."""
    blocks = []
    i = 0
    while i < len(text):
        if text[i] == '{':
            depth = 0
            start = i
            in_string = False
            escape = False
            for j in range(i, len(text)):
                ch = text[j]
                if escape:
                    escape = False
                    continue
                if ch == '\\':
                    escape = True
                    continue
                if ch == '"' and not escape:
                    in_string = not in_string
                if not in_string:
                    if ch == '{':
                        depth += 1
                    elif ch == '}':
                        depth -= 1
                        if depth == 0:
                            candidate = text[start:j+1]
                            if '"actions"' in candidate:
                                blocks.append(candidate)
                            i = j
                            break
        i += 1
    return blocks

def _get_tool_schemas():
    return get_all_tool_schemas()


async def _load_session_llm_config(db: AsyncSession, session_id: str) -> Dict[str, Any]:
    """
    BYOK Resolution Order:
    1. SessionModel.context (user-configured via Settings UI)
    2. Environment variables (host-level fallback)
    3. Empty — will trigger a user-friendly error
    """
    result = await db.execute(
        select(SessionModel).where(SessionModel.id == session_id)
    )
    session = result.scalar_one_or_none()
    ctx = (session.context if session else None) or {}

    config: Dict[str, Any] = {}

    # Model resolution: session → env → default
    config["model"] = (
        ctx.get("model")
        or os.environ.get("LLM_MODEL")
        or "gpt-4o"
    )

    # API key resolution: session → env (supports NVIDIA, OpenAI, Anthropic)
    config["api_key"] = (
        ctx.get("api_key")
        or os.environ.get("OPENAI_API_KEY")
        or os.environ.get("NVIDIA_API_KEY")
        or os.environ.get("ANTHROPIC_API_KEY")
        or ""
    )

    # Base URL: session → env → None (litellm auto-detects)
    base_url = ctx.get("base_url") or os.environ.get("LLM_BASE_URL")
    if base_url:
        config["base_url"] = base_url

        # LiteLLM provider routing: when using a custom base_url (NVIDIA NIM,
        # Together, Groq, vLLM, etc.), litellm requires the model name to carry
        # a provider prefix so it knows which client protocol to use.
        # If the model doesn't already have a recognized litellm prefix,
        # prepend "openai/" since all these endpoints are OpenAI-compatible.
        KNOWN_PREFIXES = (
            "openai/", "anthropic/", "ollama/", "huggingface/",
            "together_ai/", "groq/", "bedrock/", "vertex_ai/",
            "azure/", "deepseek/", "mistral/",
        )
        model = config["model"]
        if not any(model.startswith(p) for p in KNOWN_PREFIXES):
            config["model"] = f"openai/{model}"

    # Extra body (for NVIDIA Nemotron reasoning, etc.)
    extra_body = ctx.get("extra_body")
    if extra_body and isinstance(extra_body, dict):
        config["extra_body"] = extra_body

    return config


class BrainWorker:
    def __init__(self):
        self.llm = LLMClient()
        self._circuit_breaker = CircuitBreaker(
            "llm-api",
            CircuitBreakerConfig(
                failure_threshold=5,
                success_threshold=2,
                timeout=30.0,
            )
        )

    @traced("brain.process_task_event")
    async def process_task_event(
        self, event: Dict[str, Any], db: AsyncSession
    ):
        task_id = event.get("task_id")
        session_id = event.get("session_id")
        description = event.get("description", "")
        trace_id = event.get("trace_id")
        broker = await _get_broker()
        
        from src.infrastructure.observability.tracing import milestones
        milestones.milestone("Thinking Start", {"task_id": task_id, "session_id": session_id})

        logger.info(f"[Brain] {task_id} — Reasoning step initiated in project_kernel_runtime")

        # --- Circuit Breaker (prevents infinite ReAct loops) ---
        task_result = await db.execute(select(TaskModel).where(TaskModel.id == task_id))
        task = task_result.scalar_one_or_none()
        
        MAX_ITERATIONS = 50   # Hard limit — enough for complex multi-file tasks
        WARN_THRESHOLD = 40   # Soft warning — tells agent to wrap up
        
        if task:
            task.iteration_count += 1
            
            if task.iteration_count > MAX_ITERATIONS:
                logger.warning(f"[Brain] CIRCUIT BREAKER hit for task {task_id} at {task.iteration_count} iterations")
                output = "⚠️ Maximum iterations reached. Wrapping up to prevent infinite loops. Please start a new message for further work."
                await persist_message(db, session_id, "assistant", output, task_id=task_id)
                broker = await _get_broker()
                await broker.publish(f"task_log:{task_id}", output.encode('utf-8'))
                await broker.publish(f"task_log:{task_id}", {"event_type": "TASK_RESOLVED"})
                await db.commit()
                return
            
            if task.iteration_count == WARN_THRESHOLD:
                # Inject a system nudge so the LLM knows to finish up
                await persist_message(
                    db, session_id, "system",
                    f"[SYSTEM] You have used {WARN_THRESHOLD} of {MAX_ITERATIONS} iterations. Wrap up your current task and provide a summary.",
                    task_id=task_id,
                )

        # Only persist user message on first entry (non-empty description)
        if description.strip():
            await persist_message(
                db, session_id, "user", description, task_id=task_id
            )

        # Build full context from DB (includes all prior tool results)
        messages = await build_llm_context(db, session_id, task_id)
        tools = _get_tool_schemas()

        # --- BYOK: Load dynamic LLM config from session ---
        llm_config = await _load_session_llm_config(db, session_id)
        
        from src.infrastructure.security.crypto import decrypt_string
        raw_key = decrypt_string(llm_config.get("api_key", ""))

        if not raw_key:
            # Graceful error — send to terminal and chat instead of crashing
            error_msg = (
                "\x1b[38;5;196m[CONFIG ERROR]\x1b[0m No API key configured.\r\n"
                "Click the ⚙ Settings icon in the top bar to configure your LLM provider.\r\n"
                "Supported: OpenAI, Anthropic, NVIDIA NIM, Ollama (local), or any OpenAI-compatible endpoint.\r\n"
            )
            await broker.publish(f"task_log:{task_id}", error_msg.encode("utf-8"))
            await persist_message(
                db, session_id, "assistant",
                "⚠️ No API key configured. Please open Settings (⚙) and enter your API key to start using the agent.",
                task_id=task_id,
            )
            await broker.publish(f"task_log:{task_id}", {"event_type": "TASK_RESOLVED"})
            await db.commit()
            return

        # Build litellm completion kwargs dynamically
        from litellm import acompletion

        completion_kwargs: Dict[str, Any] = {
            "model": llm_config["model"],
            "messages": messages,
            "tools": tools,
            "temperature": 0.0,
            "stream": True,
            "api_key": raw_key,
        }
        if llm_config.get("base_url"):
            completion_kwargs["api_base"] = llm_config["base_url"]
        if llm_config.get("extra_body"):
            completion_kwargs["extra_body"] = llm_config["extra_body"]

        logger.info(f"[Brain] LLM config → model={llm_config['model']}, base_url={llm_config.get('base_url', 'auto')}")

        if not await self._circuit_breaker.can_execute():
            error_msg = "\x1b[38;5;196m[CIRCUIT BREAKER OPEN]\x1b[0m LLM service temporarily unavailable. Please try again later."
            await broker.publish(f"task_log:{task_id}", error_msg.encode("utf-8"))
            await persist_message(db, session_id, "assistant", error_msg, task_id=task_id)
            await broker.publish(f"task_log:{task_id}", {"event_type": "TASK_RESOLVED"})
            await db.commit()
            return

        try:
            response = await self._circuit_breaker.protected(acompletion)(**completion_kwargs)
        except CircuitBreakerOpenError:
            error_msg = "\x1b[38;5;196m[CIRCUIT BREAKER OPEN]\x1b[0m LLM service temporarily unavailable. Please try again later."
            await broker.publish(f"task_log:{task_id}", error_msg.encode("utf-8"))
            await persist_message(db, session_id, "assistant", error_msg, task_id=task_id)
            await broker.publish(f"task_log:{task_id}", {"event_type": "TASK_RESOLVED"})
            await db.commit()
            return
        except Exception as llm_err:
            error_text = str(llm_err)
            logger.error(f"[Brain] LLM call failed: {error_text}")
            human_msg = f"⚠️ LLM Error: {error_text[:500]}"
            await broker.publish(f"task_log:{task_id}", f"\x1b[38;5;196m{human_msg}\x1b[0m\r\n".encode("utf-8"))
            await persist_message(db, session_id, "assistant", human_msg, task_id=task_id)
            await broker.publish(f"task_log:{task_id}", {"event_type": "TASK_RESOLVED"})
            await db.commit()
            return

        collected_content = []
        tool_calls_dict = {}

        # Broadcast start of thought
        model_label = llm_config["model"].split("/")[-1]
        await broker.publish(
            f"task_log:{task_id}",
            f"\x1b[38;5;46m[{model_label}] Thinking...\x1b[0m\r\n".encode("utf-8"),
        )

        async for chunk in response:
            delta = chunk.choices[0].delta

            # Handle reasoning_content (NVIDIA Nemotron / DeepSeek style)
            reasoning = getattr(delta, "reasoning_content", None)
            if reasoning:
                await broker.publish(f"task_log:{task_id}", f"\x1b[38;5;244m{reasoning}\x1b[0m".encode("utf-8"))

            if delta.content:
                collected_content.append(delta.content)
                # Stream the content token to the websocket terminal
                await broker.publish(f"task_log:{task_id}", delta.content.encode("utf-8"))
            
            if delta.tool_calls:
                for tc in delta.tool_calls:
                    idx = tc.index
                    if idx not in tool_calls_dict:
                        # Initialize cleanly. Do NOT pull tc.function.name here to avoid duplicating it below
                        tool_calls_dict[idx] = {"id": tc.id, "type": tc.type, "function": {"name": "", "arguments": ""}}
                    
                    if tc.function:
                        if tc.function.name:
                            tool_calls_dict[idx]["function"]["name"] += tc.function.name
                        if tc.function.arguments:
                            tool_calls_dict[idx]["function"]["arguments"] += tc.function.arguments

        full_content = "".join(collected_content)
        
        if full_content:
            await broker.publish(f"task_log:{task_id}", b"\r\n")

        # --- Tool calls → emit to execution_queue ---
        
        # 1. Check NemoClaw heuristic extraction first if native was empty
        heuristic_calls = []
        if not tool_calls_dict and full_content:
            heuristic_calls = _extract_heuristic_tool_calls(full_content)

        if tool_calls_dict or heuristic_calls:
            await persist_message(
                db, session_id, "assistant",
                full_content,
                task_id=task_id,
            )
            
            # Combine calls
            combined_calls = list(tool_calls_dict.values()) + heuristic_calls
            
            for tc in combined_calls:
                await broker.publish(f"task_log:{task_id}", f"\x1b[38;5;220m\r\n[Executing Tool: {tc['function']['name']}]\x1b[0m\r\n".encode("utf-8"))
                from src.infrastructure.observability.tracing import milestones
                milestones.milestone("Action Dispatched", {"tool": tc['function']['name']})
                
                await broker.publish("execution_queue", {
                    "event_type": "EXECUTE_TOOL",
                    "task_id": task_id,
                    "session_id": session_id,
                    "tool": {
                        "name": tc["function"]["name"],
                        "args": json.loads(tc["function"]["arguments"]),
                    },
                }, trace_id=trace_id)
                logger.info(f"[Brain] → EXECUTE: {tc['function']['name']}")
        else:
            # --- No tool call → final answer ---
            await persist_message(
                db, session_id, "assistant", full_content, task_id=task_id
            )
            await broker.publish("task_resolved", {
                "event_type": "TASK_RESOLVED",
                "task_id": task_id,
                "session_id": session_id,
                "output": full_content,
            }, trace_id=trace_id)
            # Also notify the websocket to close gracefully
            await broker.publish(f"task_log:{task_id}", {"event_type": "TASK_RESOLVED"})
            from src.infrastructure.observability.tracing import milestones
            milestones.milestone("Task Resolved", {"task_id": task_id})
            logger.info("[Brain] Task resolved in project_kernel_runtime.")

        await db.commit()
