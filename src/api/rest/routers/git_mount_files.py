"""
Git Mount — File Operations (read / write / delete)
"""
import logging
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from src.api.rest.dependencies import get_db, get_current_user_dep
from src.infrastructure.auth.jwt_auth import TokenPayload
from src.infrastructure.queue.redis_streams_broker import get_streams_broker
from src.infrastructure.storage.gvfs import get_gvfs

from .git_mount_models import (
    require_session,
    FileContentRequest, FileContentResponse,
    WriteFileRequest, WriteFileResponse,
    DeleteFileRequest,
)

logger = logging.getLogger(__name__)

router = APIRouter(tags=["Git Mount"])


@router.post("/mount/{session_id}/read", response_model=FileContentResponse)
async def read_file(
    session_id: str, req: FileContentRequest,
    db: AsyncSession = Depends(get_db),
    user: TokenPayload = Depends(get_current_user_dep),
):
    """Read file content from virtual filesystem."""
    await require_session(session_id, user, db)
    try:
        gvfs = await get_gvfs()
        vfile = await gvfs.read_file(session_id, req.path, load_content=True)
        if not vfile:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"File not found: {req.path}")
        content = vfile.content.decode("utf-8", errors="replace") if vfile.content and not vfile.is_binary else None
        return FileContentResponse(
            path=vfile.path, content=content, size=vfile.size,
            status=vfile.status.value, sha=vfile.sha, is_binary=vfile.is_binary
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"[GitMount] Read error: {e}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))


@router.post("/mount/{session_id}/write", response_model=WriteFileResponse)
async def write_file(
    session_id: str, req: WriteFileRequest,
    db: AsyncSession = Depends(get_db),
    user: TokenPayload = Depends(get_current_user_dep),
):
    """Write file to virtual filesystem."""
    await require_session(session_id, user, db)
    try:
        gvfs = await get_gvfs()
        content_bytes = req.content.encode(req.encoding)
        vfile = await gvfs.write_file(session_id, req.path, content_bytes)
        broker = await get_streams_broker()
        await broker.publish(
            f"session:{session_id}:files",
            {"event": "file_changed", "path": vfile.path, "status": vfile.status.value, "size": vfile.size},
            tenant_id=user.tenant_id,
        )
        return WriteFileResponse(success=True, path=vfile.path, status=vfile.status.value, sha=vfile.sha, size=vfile.size)
    except Exception as e:
        logger.error(f"[GitMount] Write error: {e}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))


@router.post("/mount/{session_id}/delete")
async def delete_file(
    session_id: str, req: DeleteFileRequest,
    db: AsyncSession = Depends(get_db),
    user: TokenPayload = Depends(get_current_user_dep),
):
    """Delete file from virtual filesystem."""
    await require_session(session_id, user, db)
    try:
        gvfs = await get_gvfs()
        success = await gvfs.delete_file(session_id, req.path)
        if not success:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"File not found: {req.path}")
        broker = await get_streams_broker()
        await broker.publish(
            f"session:{session_id}:files",
            {"event": "file_deleted", "path": req.path},
            tenant_id=user.tenant_id,
        )
        return {"success": True, "message": f"Deleted {req.path}"}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"[GitMount] Delete error: {e}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))
