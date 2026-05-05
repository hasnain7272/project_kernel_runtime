"""Tenant-scoped session lifecycle routes."""
from datetime import datetime, timezone
from typing import Any, Dict

from fastapi import APIRouter, Depends, status
from sqlalchemy import and_, select
from sqlalchemy.ext.asyncio import AsyncSession

from src.api.rest.dependencies import get_current_user_dep, get_db
from src.api.rest.routers.session_config import router as config_router
from src.api.rest.routers.session_models import SessionCreateRequest, SessionRenameRequest
from src.api.rest.routers.session_utils import get_or_create_workspace, get_session_or_404, prepare_workspaces, session_to_dict
from src.api.rest.routers.session_workspaces import router as workspaces_router
from src.infrastructure.auth.jwt_auth import TokenPayload
from src.infrastructure.db.models.session_model import SessionModel

router = APIRouter(prefix="/api/v1/sessions", tags=["Sessions"])


@router.post("/", status_code=status.HTTP_201_CREATED)
async def create_session(
    req: SessionCreateRequest,
    db: AsyncSession = Depends(get_db),
    user: TokenPayload = Depends(get_current_user_dep),
) -> Dict[str, Any]:
    workspace_rows = prepare_workspaces(req.workspaces, user.tenant_id)
    workspace_objs = [await get_or_create_workspace(db, user.tenant_id, data) for data in workspace_rows]
    session = SessionModel(
        tenant_id=user.tenant_id,
        organization_id=user.organization_id,
        user_id=user.user_id,
        name=req.name.strip()[:128],
        user_role=user.role,
        mode=req.mode,
    )
    session.workspaces = workspace_objs
    db.add(session)
    await db.commit()
    await db.refresh(session)
    return session_to_dict(session)


@router.get("/")
async def list_sessions(db: AsyncSession = Depends(get_db), user: TokenPayload = Depends(get_current_user_dep)) -> Dict[str, Any]:
    result = await db.execute(
        select(SessionModel).where(and_(SessionModel.tenant_id == user.tenant_id, SessionModel.is_active == True)).order_by(SessionModel.last_active_at.desc())
    )
    return {"sessions": [session_to_dict(session) for session in result.scalars().all()]}


@router.get("/{session_id}")
async def get_session(session_id: str, db: AsyncSession = Depends(get_db), user: TokenPayload = Depends(get_current_user_dep)) -> Dict[str, Any]:
    return session_to_dict(await get_session_or_404(db, session_id, user.tenant_id))


@router.patch("/{session_id}/name")
async def rename_session(
    session_id: str,
    req: SessionRenameRequest,
    db: AsyncSession = Depends(get_db),
    user: TokenPayload = Depends(get_current_user_dep),
) -> Dict[str, Any]:
    session = await get_session_or_404(db, session_id, user.tenant_id)
    session.name = req.name.strip()[:128]
    session.last_active_at = datetime.now(timezone.utc)
    await db.commit()
    return {"session_id": session_id, "name": session.name}


@router.delete("/{session_id}")
async def end_session(session_id: str, db: AsyncSession = Depends(get_db), user: TokenPayload = Depends(get_current_user_dep)) -> Dict[str, str]:
    session = await get_session_or_404(db, session_id, user.tenant_id)
    session.is_active = False
    await db.commit()
    return {"status": "ended", "session_id": session_id}


router.include_router(workspaces_router)
router.include_router(config_router)
