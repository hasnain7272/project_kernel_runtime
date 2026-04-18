"""
Context Builder Service

Assembles the LLM's message history from the database.
Core dependency of the BrainWorker.
"""
import logging
from typing import List, Dict

from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from src.infrastructure.db.models.message_model import MessageModel

logger = logging.getLogger(__name__)

SYSTEM_PROMPT = (
    "You are Antigravity Agent, an autonomous software engineer. "
    "You have access to tools for reading files, writing files, "
    "and executing shell commands inside a secure sandbox. "
    "Think step-by-step. Use tools to gather information before acting. "
    "When a task is complete, respond with a clear summary."
)


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
    # Build WHERE clause FIRST, then order + limit
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
        {"role": "system", "content": SYSTEM_PROMPT}
    ]

    import os
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

    logger.debug(
        f"[ContextBuilder] {len(messages)} messages "
        f"for session={session_id}"
    )
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
    # Prevent race conditions by acquiring row lock on the Parent Session (PostgreSQL)
    try:
        from src.infrastructure.db.models.session_model import SessionModel
        await db.execute(
            select(SessionModel)
            .where(SessionModel.id == session_id)
            .with_for_update()
        )
    except Exception as e:
        # Fallback if SQLite driver doesn't support async locking gracefully
        logger.debug(f"Row lock not acquired: {e}")

    # O(1) sequence via MAX
    max_stmt = (
        select(func.coalesce(func.max(MessageModel.sequence), -1))
        .where(MessageModel.session_id == session_id)
    )
    result = await db.execute(max_stmt)
    next_seq = result.scalar() + 1

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
