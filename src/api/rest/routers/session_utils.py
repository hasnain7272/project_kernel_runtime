"""Shared session helpers."""
import uuid
from typing import Any, Dict, List

from fastapi import HTTPException, status
from sqlalchemy import and_, select
from sqlalchemy.ext.asyncio import AsyncSession

from src.api.rest.routers.session_models import WorkspaceBinding
from src.infrastructure.db.models.session_model import SessionModel
from src.infrastructure.db.models.workspace_model import WorkspaceModel
from src.infrastructure.runtime.paths import workspace_root


def session_to_dict(session: SessionModel) -> Dict[str, Any]:
    return {
        "id": session.id,
        "name": session.name,
        "tenant_id": session.tenant_id,
        "user_id": session.user_id,
        "mode": session.mode,
        "user_role": session.user_role,
        "workspaces": [workspace_to_dict(ws) for ws in (session.workspaces or [])],
        "is_active": session.is_active,
        "created_at": session.created_at.isoformat() if session.created_at else None,
        "last_active_at": session.last_active_at.isoformat() if session.last_active_at else None,
    }


def workspace_to_dict(ws: WorkspaceModel) -> Dict[str, Any]:
    return {"type": ws.type, "slug": ws.slug, "name": ws.name, "path": ws.path, "url": ws.url, "branch": ws.branch}


async def get_session_or_404(db: AsyncSession, session_id: str, tenant_id: str) -> SessionModel:
    result = await db.execute(select(SessionModel).where(and_(SessionModel.id == session_id, SessionModel.tenant_id == tenant_id)))
    session = result.scalar_one_or_none()
    if not session:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Session not found")
    return session


def make_slug(ws: WorkspaceBinding) -> str:
    if ws.slug:
        return ws.slug
    if ws.type == "local" and ws.path:
        import pathlib

        return pathlib.PurePath(ws.path).name.lower().replace(" ", "-")[:64]
    if ws.type == "git" and ws.url:
        name = ws.url.rstrip("/").split("/")[-1]
        return (name[:-4] if name.endswith(".git") else name).lower().replace(" ", "-")[:64]
    return f"workspace-{uuid.uuid4().hex[:8]}"


def prepare_workspaces(workspaces: List[WorkspaceBinding], tenant_id: str) -> list[dict]:
    rows = []
    for ws in workspaces or [WorkspaceBinding(type="local")]:
        slug = make_slug(ws)
        ws_root = workspace_root() / f"tenant_{tenant_id}" / slug
        ws_root.mkdir(parents=True, exist_ok=True)
        row = {"type": ws.type, "slug": slug, "branch": ws.branch, "name": slug}
        if ws.type == "local":
            row["path"] = str(ws_root)
        if ws.type == "git":
            row["url"] = ws.url
        rows.append(row)
    return rows


async def get_or_create_workspace(db: AsyncSession, tenant_id: str, data: dict) -> WorkspaceModel:
    result = await db.execute(select(WorkspaceModel).where(and_(WorkspaceModel.tenant_id == tenant_id, WorkspaceModel.slug == data["slug"])))
    workspace = result.scalar_one_or_none()
    if workspace:
        return workspace
    workspace = WorkspaceModel(
        tenant_id=tenant_id,
        slug=data["slug"],
        name=data.get("name", data["slug"]),
        type=data["type"],
        path=data.get("path"),
        url=data.get("url"),
        branch=data.get("branch", "main"),
    )
    db.add(workspace)
    return workspace
