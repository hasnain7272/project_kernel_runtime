"""
Git Mount — Core Routes (mount / unmount / tree)
"""
import logging
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from src.api.rest.dependencies import get_db, get_current_user_dep
from src.infrastructure.auth.jwt_auth import TokenPayload
from src.infrastructure.security.crypto import encrypt_string
from src.infrastructure.storage.gvfs import get_gvfs

from .git_mount_models import (
    require_session,
    MountRequest, MountResponse,
    TreeItem, TreeResponse,
)

logger = logging.getLogger(__name__)

router = APIRouter(tags=["Git Mount"])


@router.post("/mount", response_model=MountResponse)
async def mount_repository(
    req: MountRequest,
    db: AsyncSession = Depends(get_db),
    user: TokenPayload = Depends(get_current_user_dep),
):
    """Mount a Git repository to a session."""
    await require_session(req.session_id, user, db)
    try:
        gvfs = await get_gvfs()
        encrypted_token = encrypt_string(req.auth_token) if req.auth_token else None
        mount = await gvfs.mount_repository(
            session_id=req.session_id, repo_url=req.repo_url,
            branch=req.branch, commit_sha=req.commit_sha, auth_token=encrypted_token
        )
        return MountResponse(
            success=True, session_id=req.session_id, repo_url=mount.repo_url,
            branch=mount.branch, commit_sha=mount.commit_sha,
            virtual_root=mount.virtual_root, file_count=len(mount.files),
            message=f"Successfully mounted {req.repo_url}@{req.branch}"
        )
    except Exception as e:
        logger.error(f"[GitMount] Mount failed: {e}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))


@router.get("/mount/{session_id}/tree", response_model=TreeResponse)
async def get_file_tree(
    session_id: str, path: str = ".",
    db: AsyncSession = Depends(get_db),
    user: TokenPayload = Depends(get_current_user_dep),
):
    """Get file tree for mounted repository."""
    await require_session(session_id, user, db)
    try:
        gvfs = await get_gvfs()
        files = await gvfs.list_directory(session_id, path)
        items = [TreeItem(path=vf.path, type="file", status=vf.status.value, size=vf.size) for vf in files]
        return TreeResponse(path=path, items=items, total_files=len(items))
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except Exception as e:
        logger.error(f"[GitMount] Tree error: {e}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))


@router.post("/mount/{session_id}/unmount")
async def unmount_repository(
    session_id: str, persist: bool = True,
    db: AsyncSession = Depends(get_db),
    user: TokenPayload = Depends(get_current_user_dep),
):
    """Unmount repository from session."""
    await require_session(session_id, user, db)
    try:
        gvfs = await get_gvfs()
        await gvfs.unmount(session_id, persist=persist)
        return {"success": True, "message": f"Unmounted repository (persist={persist})"}
    except Exception as e:
        logger.error(f"[GitMount] Unmount error: {e}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))
