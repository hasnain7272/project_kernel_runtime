"""
Chat Router — Multi-tenant messaging to BrainWorker.

- Tenant-scoped sessions
- Per-tenant rate limiting
- Tenant context in all DB queries
"""
from typing import Dict, Any

from fastapi import APIRouter, Depends, HTTPException, status, Header
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.api.rest.dependencies import (
    get_db,
    get_broker_dep,
    get_current_user_dep,
    check_rate_limit,
)
from src.infrastructure.auth.jwt_auth import TokenPayload
from src.infrastructure.db.models.task_model import TaskModel
from src.infrastructure.db.models.message_model import MessageModel
from src.infrastructure.db.models.session_model import SessionModel
from src.domain.entities.task import TaskStatus

router = APIRouter(prefix="/api/v1/chat", tags=["Chat"])


class ChatRequest(BaseModel):
    session_id: str
    message: str
    files: list[dict] = []
    shadow_mode: bool = False
    active_model_id: str | None = None


@router.post("/", status_code=status.HTTP_202_ACCEPTED)
async def send_chat_message(
    req: ChatRequest,
    db: AsyncSession = Depends(get_db),
    broker=Depends(get_broker_dep),
    user: TokenPayload = Depends(get_current_user_dep),
) -> Dict[str, Any]:
    """
    Accepts a user message, creates a task, and dispatches
    to the brain worker via the event queue.
    """
    await check_rate_limit(user)
    
    # Verify session belongs to tenant
    auth_check = await db.execute(
        select(SessionModel).where(
            SessionModel.id == req.session_id,
            SessionModel.tenant_id == user.tenant_id,
        )
    )
    session = auth_check.scalar_one_or_none()
    if not session:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Not authorized or session not found")
        
    # Update shadow mode and active model ID in session context
    context = dict(session.context) if session.context else {}
    context["shadow_mode"] = req.shadow_mode
    if req.active_model_id:
        context["active_model_id"] = req.active_model_id
    session.context = context
    db.add(session)
    
    # Create task with tenant_id
    task = TaskModel(
        tenant_id=user.tenant_id,
        session_id=req.session_id,
        description=req.message,
        status=TaskStatus.PENDING.value,
    )
    db.add(task)
    await db.commit()
    await db.refresh(task)

    # Dispatch with tenant context
    await broker.publish(
        "task_queue",
        {
            "event_type": "AGENT_THINK",
            "task_id": task.id,
            "session_id": req.session_id,
            "description": req.message,
        },
        tenant_id=user.tenant_id,
    )

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
    user: TokenPayload = Depends(get_current_user_dep),
) -> Dict[str, Any]:
    """Returns conversation history for session (tenant-scoped)."""
    auth_check = await db.execute(
        select(SessionModel.id).where(
            SessionModel.id == session_id,
            SessionModel.tenant_id == user.tenant_id,
        )
    )
    if not auth_check.scalar_one_or_none():
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Not authorized or session not found")

    result = await db.execute(
        select(MessageModel)
        .where(
            MessageModel.session_id == session_id,
            MessageModel.tenant_id == user.tenant_id,
        )
        .order_by(MessageModel.sequence.asc())
        .limit(limit)
    )
    rows = result.scalars().all()
    return {
        "session_id": session_id,
        "messages": [
            {
                "id": str(r.id),
                "role": r.role,
                "content": r.content,
                "tool_calls": _parse_tool_calls(r.tool_calls),
                "tool_call_id": r.tool_call_id,
                "metadata": _parse_json_field(r.extra_metadata),
                "created_at": r.created_at.isoformat(),
            }
            for r in rows
        ],
    }


def _parse_json_field(raw):
    if not raw:
        return {}
    if isinstance(raw, dict):
        return raw
    try:
        import json
        return json.loads(raw)
    except Exception:
        return {}


class ApprovalRequest(BaseModel):
    message_id: str
    decision: str  # "approved" or "denied"


@router.post("/{session_id}/approve")
async def approve_tool_call(
    session_id: str,
    req: ApprovalRequest,
    db: AsyncSession = Depends(get_db),
    broker=Depends(get_broker_dep),
    user: TokenPayload = Depends(get_current_user_dep),
) -> Dict[str, Any]:
    """Handles human-in-the-loop approval for restricted tools."""
    # 1. Fetch the message to get tool details from metadata
    msg_result = await db.execute(
        select(MessageModel).where(
            MessageModel.id == req.message_id,
            MessageModel.session_id == session_id,
            MessageModel.tenant_id == user.tenant_id
        )
    )
    message = msg_result.scalar_one_or_none()
    if not message or not message.extra_metadata or message.extra_metadata.get("status") != "NEEDS_APPROVAL":
        raise HTTPException(404, "Pending approval request not found")

    if req.decision == "denied":
        message.extra_metadata = {**message.extra_metadata, "status": "DENIED"}
        db.add(message)
        await db.commit()
        return {"status": "denied"}

    # 2. Mark as approved and re-dispatch
    tool_name = message.extra_metadata.get("tool_name")
    tool_args = message.extra_metadata.get("args", {})
    tool_args["__approved__"] = True # Injection flag for PolicyEngine
    
    message.extra_metadata = {**message.extra_metadata, "status": "APPROVED"}
    db.add(message)
    await db.commit()

    await broker.publish(
        "execution_queue",
        {
            "event_type": "EXECUTE_TOOL",
            "task_id": message.task_id,
            "session_id": session_id,
            "tool": {
                "name": tool_name,
                "args": tool_args,
                "id": message.tool_call_id
            }
        },
        tenant_id=user.tenant_id
    )

    return {"status": "dispatched"}



def _parse_tool_calls(raw):
    return _parse_json_field(raw)
