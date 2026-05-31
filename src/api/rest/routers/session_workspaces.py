"""Session workspace binding routes."""
from datetime import datetime, timezone
from typing import Any, Dict

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from src.api.rest.dependencies import get_current_user_dep, get_db
from src.api.rest.routers.session_models import WorkspaceAddRequest
from src.api.rest.routers.session_utils import get_or_create_workspace, get_session_or_404, prepare_workspaces, session_to_dict, workspace_to_dict
from src.infrastructure.auth.jwt_auth import TokenPayload
from src.infrastructure.security.crypto import encrypt_string
from src.infrastructure.storage.gvfs import get_gvfs

router = APIRouter()


@router.post("/{session_id}/workspaces")
async def add_workspace(
    session_id: str,
    req: WorkspaceAddRequest,
    db: AsyncSession = Depends(get_db),
    user: TokenPayload = Depends(get_current_user_dep),
) -> Dict[str, Any]:
    session = await get_session_or_404(db, session_id, user.tenant_id)
    data = prepare_workspaces([req.workspace], user.tenant_id)[0]
    workspace = await get_or_create_workspace(db, user.tenant_id, data)
    current = list(session.workspaces or [])
    if workspace.slug not in {ws.slug for ws in current}:
        session.workspaces = [*current, workspace]

    if data["type"] == "git" and data.get("url"):
        github_token = (session.context or {}).get("github", {}).get("access_token")
        if github_token and not github_token.startswith("gAAAA"):
            github_token = encrypt_string(github_token)
        gvfs = await get_gvfs()
        await gvfs.mount_repository(
            session_id=session_id,
            repo_url=data["url"],
            branch=data.get("branch") or "main",
            auth_token=github_token,
        )

    session.last_active_at = datetime.now(timezone.utc)
    await db.commit()
    await db.refresh(session)
    return session_to_dict(session)


@router.delete("/{session_id}/workspaces/{slug}")
async def remove_workspace(
    session_id: str,
    slug: str,
    db: AsyncSession = Depends(get_db),
    user: TokenPayload = Depends(get_current_user_dep),
) -> Dict[str, Any]:
    session = await get_session_or_404(db, session_id, user.tenant_id)
    current = list(session.workspaces or [])
    session.workspaces = [ws for ws in current if ws.slug != slug]
    if len(session.workspaces) == len(current):
        raise HTTPException(status.HTTP_404_NOT_FOUND, f"Workspace '{slug}' not found in session")
    session.last_active_at = datetime.now(timezone.utc)
    await db.commit()
    await db.refresh(session)
    return session_to_dict(session)


@router.get("/{session_id}/workspaces")
async def list_workspaces(
    session_id: str,
    db: AsyncSession = Depends(get_db),
    user: TokenPayload = Depends(get_current_user_dep),
) -> Dict[str, Any]:
    session = await get_session_or_404(db, session_id, user.tenant_id)
    return {"workspaces": [workspace_to_dict(ws) for ws in (session.workspaces or [])]}
