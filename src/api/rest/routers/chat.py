"""
Chat Router — Bridges user messages to the BrainWorker via the broker.
"""
from typing import Dict, Any

from fastapi import APIRouter, Depends, status
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.api.rest.dependencies import get_db, get_broker_dep
from src.infrastructure.db.models.task_model import TaskModel
from src.infrastructure.db.models.message_model import MessageModel
from src.domain.entities.task import TaskStatus

router = APIRouter(prefix="/api/v1/chat", tags=["Chat"])


class ChatRequest(BaseModel):
    session_id: str
    message: str


@router.post("/", status_code=status.HTTP_202_ACCEPTED)
async def send_chat_message(
    req: ChatRequest,
    db: AsyncSession = Depends(get_db),
    broker=Depends(get_broker_dep),
) -> Dict[str, Any]:
    """
    Accepts a user message, creates a task, and dispatches
    it to the brain worker via the event queue.
    """
    # Create a task representing this chat interaction
    task = TaskModel(
        session_id=req.session_id,
        description=req.message,
        status=TaskStatus.PENDING.value,
    )
    db.add(task)
    await db.commit()
    await db.refresh(task)

    # Dispatch to the brain via broker
    await broker.publish("task_queue", {
        "event_type": "AGENT_THINK",
        "task_id": task.id,
        "session_id": req.session_id,
        "description": req.message,
    })

    return {
        "status": "accepted",
        "task_id": task.id,
        "message": "Message dispatched to agent.",
    }


@router.get("/{session_id}/history")
async def get_chat_history(
    session_id: str,
    limit: int = 50,
    db: AsyncSession = Depends(get_db),
) -> Dict[str, Any]:
    """Returns the persisted conversation history for a session."""
    result = await db.execute(
        select(MessageModel)
        .where(MessageModel.session_id == session_id)
        .order_by(MessageModel.sequence.asc())
        .limit(limit)
    )
    rows = result.scalars().all()
    return {
        "session_id": session_id,
        "messages": [
            {
                "role": r.role,
                "content": r.content,
                "created_at": r.created_at.isoformat(),
            }
            for r in rows
        ],
    }
