"""
Git Mount — WebSocket Stream & Context Routes
"""
import logging
import asyncio
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, status, WebSocket, Query
from sqlalchemy.ext.asyncio import AsyncSession

from src.api.rest.dependencies import get_db, get_current_user_dep
from src.infrastructure.auth.jwt_auth import TokenPayload, decode_token
from src.infrastructure.queue.redis_streams_broker import get_streams_broker
from src.infrastructure.runtime.config import ALLOW_ANON_LOCAL
from src.services.memory.context import get_context_manager

from .git_mount_models import require_session

logger = logging.getLogger(__name__)

router = APIRouter(tags=["Git Mount"])


@router.websocket("/mount/{session_id}/files/stream")
async def file_changes_stream(
    websocket: WebSocket,
    session_id: str,
    tenant_id: str = Query(None),
    token: str | None = Query(None),
):
    """WebSocket for real-time file change notifications."""
    from src.infrastructure.db.session import AsyncSessionLocal

    try:
        user = decode_token(token) if token else None
    except HTTPException:
        await websocket.close(code=status.WS_1008_POLICY_VIOLATION)
        return

    if user is None and ALLOW_ANON_LOCAL:
        user = TokenPayload(
            tenant_id=tenant_id or "local", user_id="local",
            email="local@dev.local", role="developer", tier="pro",
            limits={"rpm": 60, "rph": 500}, exp=0, iat=0, organization_id=None,
        )
    if user is None:
        await websocket.close(code=status.WS_1008_POLICY_VIOLATION)
        return

    async with AsyncSessionLocal() as db:
        await require_session(session_id, user, db)

    await websocket.accept()
    broker = await get_streams_broker()
    channel = f"session:{session_id}:files"

    async def stream_handler(msg: Any):
        payload = getattr(msg, "data", msg)
        if isinstance(payload, dict):
            if payload.get("tenant_id") and payload.get("tenant_id") != user.tenant_id:
                return
            await websocket.send_json(payload)
            return
        await websocket.send_text(str(payload))

    listener_task = asyncio.create_task(broker.subscribe_channel(channel, stream_handler))
    try:
        while True:
            await websocket.receive_text()
    except Exception:
        pass
    finally:
        listener_task.cancel()
        try:
            await websocket.close()
        except Exception:
            pass


@router.get("/mount/{session_id}/context")
async def get_session_context(
    session_id: str, limit: int = 50,
    db: AsyncSession = Depends(get_db),
    user: TokenPayload = Depends(get_current_user_dep),
):
    """Get session context for UI."""
    await require_session(session_id, user, db)
    try:
        ctx_mgr = await get_context_manager()
        messages = await ctx_mgr.get_context_for_ui(session_id, limit=limit)
        return {"session_id": session_id, "messages": messages, "count": len(messages)}
    except Exception as e:
        logger.error(f"[GitMount] Context error: {e}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))


@router.post("/mount/{session_id}/context/search")
async def search_context(
    session_id: str, query: str,
    db: AsyncSession = Depends(get_db),
    user: TokenPayload = Depends(get_current_user_dep),
):
    """Search within session context."""
    await require_session(session_id, user, db)
    try:
        ctx_mgr = await get_context_manager()
        results = await ctx_mgr.search_context(session_id, query)
        return {"session_id": session_id, "query": query, "results": results, "count": len(results)}
    except Exception as e:
        logger.error(f"[GitMount] Search error: {e}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))
