"""
Tasks Router — Task dispatch and real-time SSE streaming.
"""
import asyncio
from typing import Dict, Any, AsyncGenerator

from fastapi import APIRouter, Depends, status
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.api.rest.dependencies import get_db, get_broker_dep
from src.infrastructure.db.models.task_model import TaskModel
from src.domain.entities.task import TaskStatus

router = APIRouter(prefix="/api/v1/tasks", tags=["Tasks"])


class TaskCreateRequest(BaseModel):
    session_id: str
    description: str


@router.post("/", status_code=status.HTTP_202_ACCEPTED)
async def dispatch_task(
    req: TaskCreateRequest,
    db: AsyncSession = Depends(get_db),
    broker=Depends(get_broker_dep),
) -> Dict[str, Any]:
    """Create task and push to worker queue."""
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

    return {
        "status": "accepted",
        "task_id": task.id,
    }


@router.get("/")
async def list_tasks(
    db: AsyncSession = Depends(get_db),
) -> Dict[str, Any]:
    result = await db.execute(
        select(TaskModel).order_by(TaskModel.created_at.desc()).limit(50)
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


from fastapi import WebSocket, WebSocketDisconnect

@router.websocket("/{task_id}/stream")
async def stream_task_logs(websocket: WebSocket, task_id: str):
    """
    WebSocket endpoint — streams real-time execution bounds (bidirectional).
    """
    await websocket.accept()
    from src.infrastructure.queue.redis_broker import get_broker
    broker = get_broker()

    # We spawn a background listener to forward from Redis -> WebSocket
    async def redis_to_ws():
        try:
            if hasattr(broker, "get_queue"):
                queue = await broker.get_queue(f"task_log:{task_id}")
                while True:
                    msg = await asyncio.wait_for(queue.get(), timeout=3600)
                    if isinstance(msg, dict):
                        await websocket.send_json(msg)
                        if msg.get("event_type") == "TASK_RESOLVED":
                            break
                    elif isinstance(msg, bytes):
                        # ANSI log stream chunks (reasoning tokens / raw stdout)
                        await websocket.send_text(msg.decode("utf-8"))
                    else:
                        await websocket.send_text(str(msg))
        except asyncio.TimeoutError:
            await websocket.send_json({"event_type": "TIMEOUT"})
        except Exception as e:
            pass # handle silently on background cancel
            
    listener_task = asyncio.create_task(redis_to_ws())

    try:
        while True:
            data = await websocket.receive_text()
            # In MVP: we can handle interrupt signals here
            if data.strip() == "\x03":  # Ctrl+C
                 await broker.publish(f"task_action:{task_id}", {"action": "interrupt"})
    except WebSocketDisconnect:
        pass
    finally:
        listener_task.cancel()
