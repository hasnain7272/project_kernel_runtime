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

from sqlalchemy import select, and_
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
from src.services.billing.usage_tracker import usage_tracker

logger = logging.getLogger(__name__)

from src.tools.registry import get_all_tool_schemas

_broker = None

async def _get_broker():
    global _broker
    if _broker is None:
        _broker = await get_streams_broker()
    return _broker

def _get_tool_schemas():
    return get_all_tool_schemas()


async def _load_session_llm_config(db: AsyncSession, session_id: str, session: Any = None) -> Dict[str, Any]:
    """
    BYOK Resolution Order:
    1. SessionModel.context (user-configured via Settings UI)
    2. Environment variables (host-level fallback)
    3. Empty — will trigger a user-friendly error
    """
    if session is None:
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

        # LiteLLM provider routing: when using a custom base_url, litellm
        # just forwards requests to that URL using OpenAI-compatible protocol.
        # The model name should be sent as-is (the API knows its own model IDs).
        # We only add a litellm prefix when there's NO base_url, so litellm
        # can auto-route to the correct provider.
        #
        # With base_url: model stays as-is (e.g. 'nvidia/nemotron-3-super-120b-a12b')
        # Without base_url: add prefix for litellm routing (e.g. 'nvidia_nim/model')

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

        # --- Load session with tenant isolation ---
        tenant_id = event.get("tenant_id")
        if tenant_id:
            session_result = await db.execute(
                select(SessionModel).where(
                    and_(
                        SessionModel.id == session_id,
                        SessionModel.tenant_id == tenant_id,
                    )
                )
            )
        else:
            session_result = await db.execute(
                select(SessionModel).where(SessionModel.id == session_id)
            )
        session = session_result.scalar_one_or_none()
        if not session:
            logger.error(f"[Brain] Session {session_id} not found or unauthorized (tenant={tenant_id})")
            error_msg = "⚠️ Session not found or unauthorized."
            await persist_message(db, session_id, "system", error_msg, task_id=task_id)
            await broker.publish(f"task_log:{task_id}", {"event_type": "TASK_RESOLVED"})
            await db.commit()
            return
        # Use tenant_id from the loaded session to ensure correctness
        tenant_id = session.tenant_id

        # --- Circuit Breaker (prevents infinite ReAct loops) ---
        task_conditions = [TaskModel.id == task_id, TaskModel.session_id == session_id]
        if tenant_id:
            task_conditions.append(TaskModel.tenant_id == tenant_id)
        task_result = await db.execute(select(TaskModel).where(and_(*task_conditions)))
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

        # 2. Publish initial thinking log
        await broker.publish(f"task_log:{task_id}", {
            "status": "thinking",
            "message": "Analyzing request..."
        })

        # Build full context from DB (includes all prior tool results)
        messages = await build_llm_context(db, session_id, task_id, session=session)
        tools = _get_tool_schemas()

        # --- BYOK: Load dynamic LLM config from session ---
        llm_config = await _load_session_llm_config(db, session_id, session=session)
        
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

        # Provider routing: LiteLLM needs custom_llm_provider to select protocol.
        # When api_base is set → endpoint is OpenAI-compatible, use 'openai' provider
        # and keep model name as-is (it's the API's model ID, not a litellm prefix).
        # When api_base is NOT set → litellm auto-routes by model prefix.
        model_name = llm_config["model"]
        if completion_kwargs.get("api_base"):
            # Custom endpoint — OpenAI-compatible, model name stays as-is
            completion_kwargs["custom_llm_provider"] = "openai"
        elif "/" in model_name:
            # No custom base URL — let litellm route by prefix
            completion_kwargs["custom_llm_provider"] = model_name.split("/")[0]
        else:
            completion_kwargs["custom_llm_provider"] = "openai"

        logger.info(f"[Brain] LLM config → model={llm_config['model']}, base_url={llm_config.get('base_url', 'auto')}, provider={completion_kwargs.get('custom_llm_provider')}")
        
        # --- SaaS Billing: Quota Check ---
        from src.services.billing.usage_tracker import usage_tracker, QuotaExceededError
        try:
            await usage_tracker.check_quota(db, tenant_id)
        except QuotaExceededError as e:
            error_msg = f"\x1b[38;5;196m[QUOTA EXCEEDED]\x1b[0m {str(e)}"
            await broker.publish(f"task_log:{task_id}", error_msg.encode("utf-8"))
            await persist_message(db, session_id, "system", error_msg, task_id=task_id)
            await broker.publish(f"task_log:{task_id}", {"event_type": "TASK_RESOLVED"})
            await db.commit()
            return

        if not await self._circuit_breaker.can_execute():
            error_msg = "\x1b[38;5;196m[CIRCUIT BREAKER OPEN]\x1b[0m LLM service temporarily unavailable. Please try again later."
            await broker.publish(f"task_log:{task_id}", error_msg.encode("utf-8"))
            await persist_message(db, session_id, "assistant", error_msg, task_id=task_id)
            await broker.publish(f"task_log:{task_id}", {"event_type": "TASK_RESOLVED"})
            await db.commit()
            return

        # 4. Completion call
        await broker.publish(f"task_log:{task_id}", {
            "status": "thinking",
            "message": "Generating response..."
        })
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
                await broker.publish(f"task_log:{task_id}", {
                    "event": "reasoning",
                    "text": reasoning
                })

            if delta.content:
                collected_content.append(delta.content)
                await broker.publish(f"task_log:{task_id}", {
                    "event": "token",
                    "text": delta.content
                })
            
            if delta.tool_calls:
                for tc in delta.tool_calls:
                    idx = tc.index
                    if idx not in tool_calls_dict:
                        tool_calls_dict[idx] = {"id": tc.id, "type": tc.type, "function": {"name": "", "arguments": ""}}
                    
                    if tc.function:
                        if tc.function.name:
                            tool_calls_dict[idx]["function"]["name"] += tc.function.name
                        if tc.function.arguments:
                            tool_calls_dict[idx]["function"]["arguments"] += tc.function.arguments

        # SaaS Billing: Track usage telemetry
        final_usage = getattr(response, "usage", None)
        if final_usage:
            import asyncio
            asyncio.create_task(usage_tracker.track_llm_usage(
                session_id=session_id,
                tenant_id=tenant_id,
                task_id=task_id,
                model=llm_config["model"],
                usage=final_usage
            ))

        full_content = "".join(collected_content)
        
        if full_content:
            await broker.publish(f"task_log:{task_id}", b"\r\n")
            
            try:
                from src.services.memory.semantic_memory import semantic_memory
                await semantic_memory.index_event(
                    session_id=session_id,
                    tenant_id=tenant_id,
                    event_type="thought",
                    content=full_content,
                    task_id=task_id
                )
            except Exception as mem_err:
                logger.error(f"[Brain] Failed to index thought: {mem_err}")

        # --- Tool calls → emit to execution_queue ---
        if tool_calls_dict:
            await persist_message(
                db, session_id, "assistant",
                full_content,
                task_id=task_id,
                tool_calls=list(tool_calls_dict.values())
            )
            
            combined_calls = list(tool_calls_dict.values())
            
            for tc in combined_calls:
                await broker.publish(f"task_log:{task_id}", {
                    "event": "tool_start",
                    "name": tc['function']['name'],
                    "args": tc['function']['arguments']
                })
                from src.infrastructure.observability.tracing import milestones
                milestones.milestone("Action Dispatched", {"tool": tc['function']['name']})
                
                await broker.publish("execution_queue", {
                    "event_type": "EXECUTE_TOOL",
                    "task_id": task_id,
                    "session_id": session_id,
                    "tool": {
                        "id": tc["id"],
                        "name": tc["function"]["name"],
                        "args": json.loads(tc["function"]["arguments"]),
                    },
                    "tenant_id": tenant_id,
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
