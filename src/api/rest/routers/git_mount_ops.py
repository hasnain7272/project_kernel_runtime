"""
Git Mount — Git Operations (diff / changes / commit)
"""
import logging
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from src.api.rest.dependencies import get_db, get_current_user_dep
from src.infrastructure.auth.jwt_auth import TokenPayload
from src.infrastructure.storage.gvfs import get_gvfs

from .git_mount_models import (
    require_session,
    DiffRequest, DiffResponse,
    ChangesResponse,
    CommitRequest, CommitResponse,
)

logger = logging.getLogger(__name__)

router = APIRouter(tags=["Git Mount"])


@router.get("/mount/{session_id}/changes", response_model=ChangesResponse)
async def get_changes(
    session_id: str,
    db: AsyncSession = Depends(get_db),
    user: TokenPayload = Depends(get_current_user_dep),
):
    """Get all changes in session relative to HEAD."""
    await require_session(session_id, user, db)
    try:
        gvfs = await get_gvfs()
        changes = await gvfs.get_changes(session_id)
        return ChangesResponse(
            modified=[{"path": f.path, "sha": f.sha, "size": f.size} for f in changes["modified"]],
            added=[{"path": f.path, "sha": f.sha, "size": f.size} for f in changes["added"]],
            deleted=[{"path": f.path} for f in changes["deleted"]],
            total_changes=len(changes["modified"]) + len(changes["added"]) + len(changes["deleted"])
        )
    except Exception as e:
        logger.error(f"[GitMount] Changes error: {e}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))


@router.post("/mount/{session_id}/diff", response_model=DiffResponse)
async def get_diff(
    session_id: str, req: DiffRequest,
    db: AsyncSession = Depends(get_db),
    user: TokenPayload = Depends(get_current_user_dep),
):
    """Get unified diff for a modified file."""
    await require_session(session_id, user, db)
    try:
        gvfs = await get_gvfs()
        diff = await gvfs.get_diff(session_id, req.path)
        vfile = await gvfs.read_file(session_id, req.path)
        old_size = len(vfile.head_content) if vfile and vfile.head_content else 0
        new_size = len(vfile.content) if vfile and vfile.content else 0
        return DiffResponse(path=req.path, diff=diff, old_size=old_size, new_size=new_size)
    except Exception as e:
        logger.error(f"[GitMount] Diff error: {e}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))


@router.post("/mount/{session_id}/commit", response_model=CommitResponse)
async def commit_changes(
    session_id: str, req: CommitRequest,
    db: AsyncSession = Depends(get_db),
    user: TokenPayload = Depends(get_current_user_dep),
):
    """Commit changes back to Git repository."""
    await require_session(session_id, user, db)
    try:
        gvfs = await get_gvfs()
        result = await gvfs.commit_changes(session_id=session_id, message=req.message, author=req.author)
        if result["success"]:
            return CommitResponse(
                success=True, commit_sha=result.get("commit_sha"),
                files_changed=result.get("files_changed", 0),
                message=f"Committed {result.get('files_changed', 0)} files"
            )
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=result.get("error", "Commit failed"))
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"[GitMount] Commit error: {e}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))
