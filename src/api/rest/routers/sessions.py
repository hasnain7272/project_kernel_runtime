"""
Sessions Router — CRUD lifecycle for agent sessions.
"""
import uuid
from typing import Dict, Any, List

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.api.rest.dependencies import get_db
from src.infrastructure.db.models.session_model import SessionModel

router = APIRouter(prefix="/api/v1/sessions", tags=["Sessions"])


class SessionCreateRequest(BaseModel):
    user_id: str = "local"
    workspace_path: str = "."
    mode: str = "web"
    name: str = "New Session"


@router.post("/", status_code=status.HTTP_201_CREATED)
async def create_session(
    req: SessionCreateRequest, db: AsyncSession = Depends(get_db)
) -> Dict[str, Any]:
    session = SessionModel(
        name=req.name,
        user_id=req.user_id,
        workspace_path=req.workspace_path,
        mode=req.mode,
    )
    db.add(session)
    await db.commit()
    await db.refresh(session)
    return {"session_id": session.id, "name": session.name, "status": "created"}


@router.get("/")
async def list_sessions(
    db: AsyncSession = Depends(get_db),
) -> Dict[str, Any]:
    result = await db.execute(
        select(SessionModel).where(SessionModel.is_active == True)
    )
    rows = result.scalars().all()
    return {
        "sessions": [
            {
                "id": s.id,
                "name": s.name,
                "user_id": s.user_id,
                "mode": s.mode,
                "created_at": s.created_at.isoformat(),
            }
            for s in rows
        ]
    }


@router.get("/{session_id}")
async def get_session(
    session_id: str, db: AsyncSession = Depends(get_db)
) -> Dict[str, Any]:
    result = await db.execute(
        select(SessionModel).where(SessionModel.id == session_id)
    )
    session = result.scalar_one_or_none()
    if not session:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Session not found")
    return {
        "id": session.id,
        "name": session.name,
        "user_id": session.user_id,
        "workspace_path": session.workspace_path,
        "mode": session.mode,
        "user_role": session.user_role,
        "is_active": session.is_active,
        "created_at": session.created_at.isoformat(),
    }


class SessionRenameRequest(BaseModel):
    name: str


@router.patch("/{session_id}/name")
async def rename_session(
    session_id: str,
    req: SessionRenameRequest,
    db: AsyncSession = Depends(get_db),
) -> Dict[str, Any]:
    result = await db.execute(
        select(SessionModel).where(SessionModel.id == session_id)
    )
    session = result.scalar_one_or_none()
    if not session:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Session not found")
    session.name = req.name.strip()[:64]  # Max 64 chars
    await db.commit()
    return {"session_id": session_id, "name": session.name}


class SessionConfigRequest(BaseModel):
    """BYOK — Bring Your Own Key. Per-session LLM provider configuration."""
    model: str | None = None
    api_key: str | None = None
    base_url: str | None = None
    extra_body: Dict[str, Any] | None = None


@router.patch("/{session_id}/config")
async def update_session_config(
    session_id: str,
    req: SessionConfigRequest,
    db: AsyncSession = Depends(get_db),
) -> Dict[str, Any]:
    """
    BYOK Config — Dynamically update the LLM provider settings for a session.
    Supports OpenAI, Anthropic, NVIDIA NIM, local Ollama, or any OpenAI-compatible endpoint.
    """
    result = await db.execute(
        select(SessionModel).where(SessionModel.id == session_id)
    )
    session = result.scalar_one_or_none()
    if not session:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Session not found")

    # Deep-merge incoming config into existing session context
    ctx = dict(session.context or {})
    patch = req.model_dump(exclude_none=True)
    ctx.update(patch)
    session.context = ctx

    await db.commit()
    await db.refresh(session)
    return {
        "session_id": session_id,
        "status": "config_updated",
        "active_config": {
            "model": ctx.get("model"),
            "base_url": ctx.get("base_url"),
            "has_api_key": bool(ctx.get("api_key")),
        },
    }


@router.get("/{session_id}/config")
async def get_session_config(
    session_id: str,
    db: AsyncSession = Depends(get_db),
) -> Dict[str, Any]:
    """Returns the current LLM config for a session (never exposes full API key)."""
    result = await db.execute(
        select(SessionModel).where(SessionModel.id == session_id)
    )
    session = result.scalar_one_or_none()
    if not session:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Session not found")

    ctx = session.context or {}
    raw_key = ctx.get("api_key", "")
    masked = f"{raw_key[:8]}...{raw_key[-4:]}" if len(raw_key) > 12 else ("••••••" if raw_key else "")

    return {
        "model": ctx.get("model", ""),
        "base_url": ctx.get("base_url", ""),
        "api_key_masked": masked,
        "extra_body": ctx.get("extra_body"),
    }


@router.delete("/{session_id}")
async def end_session(
    session_id: str, db: AsyncSession = Depends(get_db)
) -> Dict[str, str]:
    result = await db.execute(
        select(SessionModel).where(SessionModel.id == session_id)
    )
    session = result.scalar_one_or_none()
    if not session:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Session not found")
    session.is_active = False
    await db.commit()
    return {"status": "ended", "session_id": session_id}
