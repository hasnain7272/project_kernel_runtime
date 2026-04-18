"""
Context Builder Service

Assembles the LLM's message history from the database.
Core dependency of the BrainWorker.
"""
import logging
import os
import platform
import datetime
from typing import List, Dict

from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from src.infrastructure.db.models.message_model import MessageModel

logger = logging.getLogger(__name__)


def get_dynamic_system_prompt() -> str:
    """Generates a highly-contextualized persona prompt with environment-aware boundaries."""
    os_name = platform.system()
    cwd = os.getcwd()
    now = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    
    # Check for sandbox mode (env set by DockerAdapter)
    sandbox_mode = os.environ.get("SANDBOX_MODE", "DOCKER" if os.environ.get("DOCKER_IMAGE") else "LOCAL")

    # Dynamically pull exact tool names from registry
    from src.tools.registry import get_tool_names
    available_tools = get_tool_names()
    tool_list = ", ".join(f'`{t}`' for t in available_tools) if available_tools else "`bash_execute`, `read_file`, `write_file`"
    
    return f"""You are the Unified Brain of the **project_kernel_runtime**, a production-grade agentic SaaS platform.
You operate as a senior software engineer within a secure, isolated sandbox: {sandbox_mode}.

[ENVIRONMENT]
- Host OS: {os_name}
- Sandbox: {sandbox_mode}
- Base Directory: {cwd}
- System Time: {now}
- Working Directory: /workspace (mounted from host workspace)

[AVAILABLE TOOLS]
You have EXACTLY these tools: {tool_list}
DO NOT invent or guess tool names.

[CONVERSATION]
- You have access to the full conversation history below
- Reference previous messages when user asks about things you've discussed
- Don't repeat questions the user already asked

[RULES OF ENGAGEMENT]
1. **ReAct Loop**: Think step-by-step before every action.
2. **Workspace Hygiene**: Use relative paths for the current workspace.
3. **Adaptive Execution**: If a tool fails (e.g. Docker missing), adapt your strategy to the {sandbox_mode} environment.
4. **Excellence**: Target high-performance, stable, and autonomous task resolution.
5. **Memory**: Remember what you've done in this conversation.
"""


async def build_llm_context(
    db: AsyncSession,
    session_id: str,
    task_id: str | None = None,
    max_turns: int = 40,
) -> List[Dict[str, str]]:
    """
    Pulls the last N conversation turns from the database
    and prepends the system prompt.
    """
    conditions = [MessageModel.session_id == session_id]
    if task_id:
        conditions.append(MessageModel.task_id == task_id)

    stmt = (
        select(MessageModel)
        .where(*conditions)
        .order_by(MessageModel.sequence.asc())
        .limit(max_turns)
    )

    result = await db.execute(stmt)
    rows = result.scalars().all()

    messages: List[Dict[str, str]] = [
        {"role": "system", "content": get_dynamic_system_prompt()}
    ]

    MAX_CHARS = 15000

    for row in rows:
        raw_content = row.content or ""
        
        if len(raw_content) > MAX_CHARS and row.role in ["tool", "assistant"]:
            cache_dir = os.path.abspath(os.path.join(os.getcwd(), "workspace", ".sandbox_cache"))
            os.makedirs(cache_dir, exist_ok=True)
            dump_path = os.path.join(cache_dir, f"context_dump_{row.id}.txt")
            
            with open(dump_path, "w", encoding="utf-8") as f:
                f.write(raw_content)
                
            head = raw_content[:5000]
            tail = raw_content[-5000:]
            clipped = len(raw_content) - 10000
            
            compacted_content = (
                f"{head}\n\n"
                f"...[{clipped} BYTES COMPACTED (SWE-Agent Strict Bounds)]...\n"
                f"[Full output paged to MemGPT Archival Disk: {dump_path}]\n\n"
                f"{tail}\n"
            )
            entry: Dict[str, str] = {"role": row.role, "content": compacted_content}
        else:
            entry: Dict[str, str] = {"role": row.role, "content": raw_content}
            
        if row.tool_call_id:
            entry["tool_call_id"] = row.tool_call_id
        messages.append(entry)

    return messages


async def persist_message(
    db: AsyncSession,
    session_id: str,
    role: str,
    content: str,
    task_id: str | None = None,
    tool_call_id: str | None = None,
) -> MessageModel:
    """Write a single conversation turn to the database."""
    try:
        from src.infrastructure.db.models.session_model import SessionModel
        await db.execute(
            select(SessionModel)
            .where(SessionModel.id == session_id)
            .with_for_update()
        )
    except Exception as e:
        logger.debug(f"Row lock not acquired: {e}")

    max_stmt = (
        select(func.coalesce(func.max(MessageModel.sequence), -1))
        .where(MessageModel.session_id == session_id)
    )
    result = await db.execute(max_stmt)
    next_seq = (result.scalar() or -1) + 1

    msg = MessageModel(
        session_id=session_id,
        task_id=task_id,
        role=role,
        content=content,
        tool_call_id=tool_call_id,
        sequence=next_seq,
    )
    db.add(msg)
    await db.flush()
    return msg
