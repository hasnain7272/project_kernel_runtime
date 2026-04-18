"""
Tasks router.
"""
import asyncio
import logging
from typing import Any, Dict

from fastapi import APIRouter, Depends, HTTPException, Query, WebSocket, WebSocketDisconnect, status
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.api.rest.dependencies import get_broker_dep, get_current_user, get_db, resolve_current_user
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
    current_user: str = Depends(get_current_user),
) -> Dict[str, Any]:
    auth_result = await db.execute(
        select(SessionModel.id).where(
            SessionModel.id == req.session_id,
            SessionModel.user_id == current_user,
        )
    )
    if not auth_result.scalar_one_or_none():
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Not authorized or session not found")

    task = TaskModel(
        session_id=req.session_id,
        description=req.description,
        status=TaskStatus.PENDING.value,
    )
    db.add(task)
    await db.commit()
    await db.refresh(task)

    await broker.publish("task_queue", {
        "event_type": "AGENT_THINK",
        "task_id": task.id,
        "session_id": req.session_id,
        "description": req.description,
    })
    return {"status": "accepted", "task_id": task.id}


@router.get("/")
async def list_tasks(
    db: AsyncSession = Depends(get_db),
    current_user: str = Depends(get_current_user),
) -> Dict[str, Any]:
    result = await db.execute(
        select(TaskModel)
        .join(SessionModel, TaskModel.session_id == SessionModel.id)
        .where(SessionModel.user_id == current_user)
        .order_by(TaskModel.created_at.desc())
        .limit(50)
    )
    rows = result.scalars().all()
    return {
        "tasks": [
            {
                "id": t.id,
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
):
    current_user = tenant_id.strip() if tenant_id and tenant_id.strip() else "local"
    
    from src.infrastructure.db.session import AsyncSessionLocal
    from src.infrastructure.queue.redis_streams_broker import get_streams_broker

    async with AsyncSessionLocal() as db:
        # Fix: Also match by task_id alone - user might be session owner
        auth_result = await db.execute(
            select(TaskModel.id, SessionModel.user_id)
            .join(SessionModel, TaskModel.session_id == SessionModel.id)
            .where(TaskModel.id == task_id)
        )
        row = auth_result.one_or_none()
        
        if not row:
            await websocket.close(code=4404)
            return
            
        _, task_owner = row
        
        # Allow if user matches OR if using local (dev mode) AND task exists
        if current_user != task_owner and current_user != "local":
            logger.warning(f"[WS Auth] Forbidden: task_id={task_id}, current_user={current_user}, owner={task_owner}")
            await websocket.close(code=4403)
            return

    await websocket.accept()
    broker = await get_streams_broker()
    stream_name = f"task_log:{task_id}"

    # Polling-based real-time stream (works with both Redis and LocalBroker)
    async def stream_poller():
        seen_ids = set()
        while True:
            try:
                if hasattr(broker, "_streams") and stream_name in broker._streams:
                    queue = broker._streams[stream_name]
                    while not queue.empty():
                        try:
                            msg = queue.get_nowait()
                            msg_id = getattr(msg, "id", str(id(msg)))
                            if msg_id not in seen_ids:
                                seen_ids.add(msg_id)
                                data = getattr(msg, "data", {})
                                if isinstance(data, bytes):
                                    data = data.decode("utf-8", errors="replace")
                                # Send as text for proper streaming display
                                if isinstance(data, dict):
                                    await websocket.send_json(data)
                                else:
                                    await websocket.send_text(str(data))
                        except asyncio.QueueEmpty:
                            break
                await asyncio.sleep(0.1)
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.warning(f"[WS] Polling error: {e}")
                await asyncio.sleep(0.5)

    listener_task = asyncio.create_task(stream_poller())
    try:
        while True:
            data = await websocket.receive_text()
            if data.strip() == "\x03":
                await broker.publish(f"task_action:{task_id}", {"action": "interrupt"})
    except WebSocketDisconnect:
        pass
    finally:
        listener_task.cancel()
