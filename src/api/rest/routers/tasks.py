"""
Tasks Router — Multi-tenant task dispatch and streaming.

Production patterns:
- Tasks scoped by tenant_id
- Session verification per tenant
- WebSocket with tenant context
"""
import asyncio
import logging
from typing import Any, Dict
from fastapi import APIRouter, Depends, HTTPException, Query, WebSocket, WebSocketDisconnect, status
from pydantic import BaseModel
from sqlalchemy import select, and_
from sqlalchemy.ext.asyncio import AsyncSession

from src.api.rest.dependencies import get_db, get_broker_dep, get_current_user_dep
from src.infrastructure.auth.jwt_auth import TokenPayload, decode_token
from src.domain.entities.task import TaskStatus
from src.infrastructure.db.models.session_model import SessionModel
from src.infrastructure.db.models.task_model import TaskModel
from src.infrastructure.runtime.config import ALLOW_ANON_LOCAL

router = APIRouter(prefix="/api/v1/tasks", tags=["Tasks"])
logger = logging.getLogger(__name__)


class TaskCreateRequest(BaseModel):
    session_id: str
    description: str


@router.post("/", status_code=status.HTTP_202_ACCEPTED)
async def dispatch_task(
    req: TaskCreateRequest,
    db: AsyncSession = Depends(get_db),
    broker=Depends(get_broker_dep),
    user: TokenPayload = Depends(get_current_user_dep),
) -> Dict[str, Any]:
    """Dispatch task to worker (tenant-scoped)."""
    auth_result = await db.execute(
        select(SessionModel.id).where(
            and_(
                SessionModel.id == req.session_id,
                SessionModel.tenant_id == user.tenant_id,
            )
        )
    )
    if not auth_result.scalar_one_or_none():
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Not authorized or session not found")

    task = TaskModel(
        tenant_id=user.tenant_id,
        session_id=req.session_id,
        description=req.description,
        status=TaskStatus.PENDING.value,
    )
    db.add(task)
    await db.commit()
    await db.refresh(task)

    await broker.publish(
        "task_queue",
        {
            "event_type": "AGENT_THINK",
            "task_id": task.id,
            "session_id": req.session_id,
            "description": req.description,
        },
        tenant_id=user.tenant_id,
    )
    return {"status": "accepted", "task_id": task.id}


@router.get("/")
async def list_tasks(
    db: AsyncSession = Depends(get_db),
    user: TokenPayload = Depends(get_current_user_dep),
) -> Dict[str, Any]:
    """List tasks for tenant."""
    result = await db.execute(
        select(TaskModel).where(
            TaskModel.tenant_id == user.tenant_id,
        ).order_by(TaskModel.created_at.desc()).limit(50)
    )
    rows = result.scalars().all()
    return {
        "tasks": [
            {
                "id": t.id,
                "tenant_id": t.tenant_id,
                "description": t.description,
                "status": t.status,
                "created_at": t.created_at.isoformat(),
            }
            for t in rows
        ]
    }


@router.websocket("/{task_id}/stream")
async def stream_task_logs(
    websocket: WebSocket,
    task_id: str,
    tenant_id: str = Query(None),
    token: str | None = Query(None),
):
    """WebSocket stream with tenant isolation."""
    from src.infrastructure.db.session import AsyncSessionLocal
    from src.infrastructure.queue.redis_streams_broker import get_streams_broker

    try:
        user = decode_token(token) if token else None
    except HTTPException:
        await websocket.close(code=4401)
        return

    if user is None and ALLOW_ANON_LOCAL:
        user = TokenPayload(
            tenant_id=tenant_id or "local",
            user_id="local",
            email="local@dev.local",
            role="developer",
            tier="pro",
            limits={"rpm": 60, "rph": 500},
            exp=0,
            iat=0,
            organization_id=None,
        )
    if user is None:
        await websocket.close(code=4401)
        return

    async with AsyncSessionLocal() as db:
        auth_result = await db.execute(
            select(TaskModel.id).where(
                and_(
                    TaskModel.id == task_id,
                    TaskModel.tenant_id == user.tenant_id,
                )
            )
        )
        row = auth_result.scalar_one_or_none()
        if not row:
            await websocket.close(code=4404)
            return

    await websocket.accept()
    broker = await get_streams_broker()
    stream_name = f"task_log:{task_id}"

    async def stream_handler(msg: Any):
        try:
            data = getattr(msg, "data", msg)
            if isinstance(data, dict):
                if data.get("tenant_id") and data.get("tenant_id") != user.tenant_id:
                    return
                data["tenant_id"] = user.tenant_id
                await websocket.send_json(data)
            else:
                await websocket.send_text(str(data))
        except Exception as e:
            logger.error(f"[WS] Send error: {e}")

    listener_task = asyncio.create_task(
        broker.subscribe_channel(stream_name, stream_handler)
    )
    try:
        while True:
            data = await websocket.receive_text()
            if data.strip() == "\x03":
                await broker.publish(
                    f"task_action:{task_id}",
                    {"action": "interrupt", "tenant_id": user.tenant_id},
                    tenant_id=user.tenant_id,
                )
    except WebSocketDisconnect:
        pass
    finally:
        listener_task.cancel()
