"""
Git Mount API Router

Provides endpoints for mounting Git repositories and managing
virtual file system operations.
"""
import logging
import asyncio
import time
import base64
import hmac
import hashlib
import json
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, HTTPException, status, WebSocket, Query
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.api.rest.dependencies import get_db, get_current_user_dep
from src.infrastructure.auth.jwt_auth import TokenPayload, decode_token
from src.infrastructure.db.models.session_model import SessionModel
from src.infrastructure.db.models.task_model import TaskModel
from src.infrastructure.queue.redis_streams_broker import get_streams_broker
from src.infrastructure.security.crypto import encrypt_string
from src.infrastructure.storage.gvfs import get_gvfs, FileStatus
from src.services.memory.context import get_context_manager
from sqlalchemy import and_
from src.infrastructure.runtime.config import ALLOW_ANON_LOCAL
from src.infrastructure.auth.jwt_auth import JWT_SECRET

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/git", tags=["Git Mount"])


def _github_state_secret() -> bytes:
    if not JWT_SECRET:
        raise HTTPException(status_code=500, detail="JWT secret is not configured")
    return JWT_SECRET.encode("utf-8")


def create_signed_state(session_id: str) -> str:
    payload = {"session_id": session_id, "iat": int(time.time())}
    raw = json.dumps(payload, separators=(",", ":")).encode("utf-8")
    signature = hmac.new(_github_state_secret(), raw, hashlib.sha256).digest()
    return base64.urlsafe_b64encode(raw + b"." + signature).decode("utf-8")


def parse_signed_state(state: str) -> str:
    try:
        decoded = base64.urlsafe_b64decode(state.encode("utf-8"))
        raw, signature = decoded.rsplit(b".", 1)
        expected = hmac.new(_github_state_secret(), raw, hashlib.sha256).digest()
        if not hmac.compare_digest(signature, expected):
            raise ValueError("State signature mismatch")
        payload = json.loads(raw.decode("utf-8"))
        if int(time.time()) - int(payload.get("iat", 0)) > 600:
            raise ValueError("State expired")
        return str(payload["session_id"])
    except Exception as exc:
        raise HTTPException(status_code=400, detail="Invalid OAuth state") from exc


async def _require_session(session_id: str, user: TokenPayload, db: AsyncSession) -> None:
    """Ensure session exists and belongs to user's tenant."""
    result = await db.execute(
        select(SessionModel.id).where(
            and_(
                SessionModel.id == session_id,
                SessionModel.tenant_id == user.tenant_id,
            )
        )
    )
    if not result.scalar_one_or_none():
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not authorized or session not found")


# ──────────────────────────────────────────────────
# Request/Response Models
# ──────────────────────────────────────────────────

class MountRequest(BaseModel):
    session_id: str = Field(..., description="Session ID to mount repository to")
    repo_url: str = Field(..., description="Git repository URL (HTTPS or SSH)")
    branch: str = Field(default="main", description="Branch to checkout")
    commit_sha: Optional[str] = Field(default=None, description="Specific commit to checkout")
    auth_token: Optional[str] = Field(default=None, description="Git auth token (will be encrypted)")


class MountResponse(BaseModel):
    success: bool
    session_id: str
    repo_url: str
    branch: str
    commit_sha: Optional[str]
    virtual_root: str
    file_count: int
    message: str


class FileContentRequest(BaseModel):
    path: str = Field(..., description="File path relative to repo root")


class FileContentResponse(BaseModel):
    path: str
    content: Optional[str]
    size: int
    status: str
    sha: str
    is_binary: bool


class WriteFileRequest(BaseModel):
    path: str = Field(..., description="File path relative to repo root")
    content: str = Field(..., description="File content")
    encoding: str = Field(default="utf-8", description="Content encoding")


class WriteFileResponse(BaseModel):
    success: bool
    path: str
    status: str
    sha: str
    size: int


class DeleteFileRequest(BaseModel):
    path: str = Field(..., description="File path to delete")


class DiffRequest(BaseModel):
    path: str = Field(..., description="File path to get diff for")


class DiffResponse(BaseModel):
    path: str
    diff: Optional[str]
    old_size: int
    new_size: int


class ChangesResponse(BaseModel):
    modified: List[Dict[str, Any]]
    added: List[Dict[str, Any]]
    deleted: List[Dict[str, Any]]
    total_changes: int


class CommitRequest(BaseModel):
    message: str = Field(..., description="Commit message")
    author: Optional[str] = Field(default=None, description="Commit author (Name <email>)")


class CommitResponse(BaseModel):
    success: bool
    commit_sha: Optional[str]
    files_changed: int
    message: str


class TreeItem(BaseModel):
    path: str
    type: str  # file or directory
    status: str
    size: int


class TreeResponse(BaseModel):
    path: str
    items: List[TreeItem]
    total_files: int


# ──────────────────────────────────────────────────
# Routes
# ──────────────────────────────────────────────────

@router.post("/mount", response_model=MountResponse)
async def mount_repository(
    req: MountRequest,
    db: AsyncSession = Depends(get_db),
    user: TokenPayload = Depends(get_current_user_dep),
):
    """
    Mount a Git repository to a session.
    
    The repository will be cloned and managed in a virtual filesystem
    separate from the working tree. Changes are tracked per-session.
    """
    # Verify session belongs to tenant
    await _require_session(req.session_id, user, db)
    
    try:
        gvfs = await get_gvfs()
        
        # Encrypt auth token if provided
        encrypted_token = None
        if req.auth_token:
            encrypted_token = encrypt_string(req.auth_token)
        
        # Mount repository
        mount = await gvfs.mount_repository(
            session_id=req.session_id,
            repo_url=req.repo_url,
            branch=req.branch,
            commit_sha=req.commit_sha,
            auth_token=encrypted_token
        )
        
        return MountResponse(
            success=True,
            session_id=req.session_id,
            repo_url=mount.repo_url,
            branch=mount.branch,
            commit_sha=mount.commit_sha,
            virtual_root=mount.virtual_root,
            file_count=len(mount.files),
            message=f"Successfully mounted {req.repo_url}@{req.branch}"
        )
        
    except Exception as e:
        logger.error(f"[GitMount] Mount failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to mount repository: {str(e)}"
        )


@router.get("/mount/{session_id}/tree", response_model=TreeResponse)
async def get_file_tree(
    session_id: str,
    path: str = ".",
    db: AsyncSession = Depends(get_db),
    user: TokenPayload = Depends(get_current_user_dep),
):
    """
    Get file tree for mounted repository.
    
    Returns files with their virtual status (modified, added, deleted, etc.)
    """
    # Verify session belongs to tenant
    await _require_session(session_id, user, db)
    
    try:
        gvfs = await get_gvfs()
        files = await gvfs.list_directory(session_id, path)
        
        items = []
        for vfile in files:
            items.append(TreeItem(
                path=vfile.path,
                type="file",
                status=vfile.status.value,
                size=vfile.size
            ))
        
        return TreeResponse(
            path=path,
            items=items,
            total_files=len(items)
        )
        
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e)
        )
    except Exception as e:
        logger.error(f"[GitMount] Tree error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )


@router.post("/mount/{session_id}/read", response_model=FileContentResponse)
async def read_file(
    session_id: str,
    req: FileContentRequest,
    db: AsyncSession = Depends(get_db),
    user: TokenPayload = Depends(get_current_user_dep),
):
    """Read file content from virtual filesystem."""
    await _require_session(session_id, user, db)
    
    try:
        gvfs = await get_gvfs()
        vfile = await gvfs.read_file(session_id, req.path, load_content=True)
        
        if not vfile:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"File not found: {req.path}"
            )
        
        # Decode content for text files
        content = None
        if vfile.content and not vfile.is_binary:
            content = vfile.content.decode("utf-8", errors="replace")
        
        return FileContentResponse(
            path=vfile.path,
            content=content,
            size=vfile.size,
            status=vfile.status.value,
            sha=vfile.sha,
            is_binary=vfile.is_binary
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"[GitMount] Read error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )


@router.post("/mount/{session_id}/write", response_model=WriteFileResponse)
async def write_file(
    session_id: str,
    req: WriteFileRequest,
    db: AsyncSession = Depends(get_db),
    user: TokenPayload = Depends(get_current_user_dep),
):
    """Write file to virtual filesystem."""
    await _require_session(session_id, user, db)
    
    try:
        gvfs = await get_gvfs()
        
        content_bytes = req.content.encode(req.encoding)
        vfile = await gvfs.write_file(session_id, req.path, content_bytes)
        
        # Notify via broker for real-time sync
        broker = await get_streams_broker()
        await broker.publish(
            f"session:{session_id}:files",
            {
                "event": "file_changed",
                "path": vfile.path,
                "status": vfile.status.value,
                "size": vfile.size
            },
            tenant_id=user.tenant_id,
        )
        
        return WriteFileResponse(
            success=True,
            path=vfile.path,
            status=vfile.status.value,
            sha=vfile.sha,
            size=vfile.size
        )
        
    except Exception as e:
        logger.error(f"[GitMount] Write error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )


@router.post("/mount/{session_id}/delete")
async def delete_file(
    session_id: str,
    req: DeleteFileRequest,
    db: AsyncSession = Depends(get_db),
    user: TokenPayload = Depends(get_current_user_dep),
):
    """Delete file from virtual filesystem."""
    await _require_session(session_id, user, db)
    
    try:
        gvfs = await get_gvfs()
        success = await gvfs.delete_file(session_id, req.path)
        
        if not success:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"File not found: {req.path}"
            )
        
        # Notify
        broker = await get_streams_broker()
        await broker.publish(
            f"session:{session_id}:files",
            {
                "event": "file_deleted",
                "path": req.path
            },
            tenant_id=user.tenant_id,
        )
        
        return {"success": True, "message": f"Deleted {req.path}"}
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"[GitMount] Delete error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )


@router.get("/mount/{session_id}/changes", response_model=ChangesResponse)
async def get_changes(
    session_id: str,
    db: AsyncSession = Depends(get_db),
    user: TokenPayload = Depends(get_current_user_dep),
):
    """Get all changes in session relative to HEAD."""
    await _require_session(session_id, user, db)
    
    try:
        gvfs = await get_gvfs()
        changes = await gvfs.get_changes(session_id)
        
        return ChangesResponse(
            modified=[
                {"path": f.path, "sha": f.sha, "size": f.size}
                for f in changes["modified"]
            ],
            added=[
                {"path": f.path, "sha": f.sha, "size": f.size}
                for f in changes["added"]
            ],
            deleted=[
                {"path": f.path}
                for f in changes["deleted"]
            ],
            total_changes=len(changes["modified"]) + len(changes["added"]) + len(changes["deleted"])
        )
        
    except Exception as e:
        logger.error(f"[GitMount] Changes error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )


@router.post("/mount/{session_id}/diff", response_model=DiffResponse)
async def get_diff(
    session_id: str,
    req: DiffRequest,
    db: AsyncSession = Depends(get_db),
    user: TokenPayload = Depends(get_current_user_dep),
):
    """Get unified diff for a modified file."""
    await _require_session(session_id, user, db)
    
    try:
        gvfs = await get_gvfs()
        diff = await gvfs.get_diff(session_id, req.path)
        
        # Get file sizes
        vfile = await gvfs.read_file(session_id, req.path)
        old_size = len(vfile.head_content) if vfile and vfile.head_content else 0
        new_size = len(vfile.content) if vfile and vfile.content else 0
        
        return DiffResponse(
            path=req.path,
            diff=diff,
            old_size=old_size,
            new_size=new_size
        )
        
    except Exception as e:
        logger.error(f"[GitMount] Diff error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )


@router.post("/mount/{session_id}/commit", response_model=CommitResponse)
async def commit_changes(
    session_id: str,
    req: CommitRequest,
    db: AsyncSession = Depends(get_db),
    user: TokenPayload = Depends(get_current_user_dep),
):
    """
    Commit changes back to Git repository.
    
    Creates a new commit with all virtual changes.
    """
    await _require_session(session_id, user, db)
    
    try:
        gvfs = await get_gvfs()
        result = await gvfs.commit_changes(
            session_id=session_id,
            message=req.message,
            author=req.author
        )
        
        if result["success"]:
            return CommitResponse(
                success=True,
                commit_sha=result.get("commit_sha"),
                files_changed=result.get("files_changed", 0),
                message=f"Committed {result.get('files_changed', 0)} files"
            )
        else:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=result.get("error", "Commit failed")
            )
            
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"[GitMount] Commit error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )


@router.post("/mount/{session_id}/unmount")
async def unmount_repository(
    session_id: str,
    persist: bool = True,
    db: AsyncSession = Depends(get_db),
    user: TokenPayload = Depends(get_current_user_dep),
):
    """
    Unmount repository from session.
    
    If persist=True, session state is saved for resumption.
    If persist=False, all session data is cleaned up.
    """
    await _require_session(session_id, user, db)
    
    try:
        gvfs = await get_gvfs()
        await gvfs.unmount(session_id, persist=persist)
        
        return {
            "success": True,
            "message": f"Unmounted repository (persist={persist})"
        }
        
    except Exception as e:
        logger.error(f"[GitMount] Unmount error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )


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
            tenant_id=tenant_id or "local",
            user_id="local",
            email="local@dev.local",
            role="developer",
            tier="pro",
            limits={"rpm": 60, "rph": 500},
            exp=0,
            iat=0,
            organization_id=None,
        )
    if user is None:
        await websocket.close(code=status.WS_1008_POLICY_VIOLATION)
        return

    async with AsyncSessionLocal() as db:
        await _require_session(session_id, user, db)

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
    except WebSocketDisconnect:
        pass
    finally:
        listener_task.cancel()
        try:
            await websocket.close()
        except:
            pass


# ──────────────────────────────────────────────────
# Context Management Routes
# ──────────────────────────────────────────────────

@router.get("/mount/{session_id}/context")
async def get_session_context(
    session_id: str,
    limit: int = 50,
    db: AsyncSession = Depends(get_db),
    user: TokenPayload = Depends(get_current_user_dep),
):
    """Get session context for UI."""
    await _require_session(session_id, user, db)
    
    try:
        ctx_mgr = await get_context_manager()
        messages = await ctx_mgr.get_context_for_ui(session_id, limit=limit)
        
        return {
            "session_id": session_id,
            "messages": messages,
            "count": len(messages)
        }
        
    except Exception as e:
        logger.error(f"[GitMount] Context error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )


@router.post("/mount/{session_id}/context/search")
async def search_context(
    session_id: str,
    query: str,
    db: AsyncSession = Depends(get_db),
    user: TokenPayload = Depends(get_current_user_dep),
):
    """Search within session context."""
    await _require_session(session_id, user, db)
    
    try:
        ctx_mgr = await get_context_manager()
        results = await ctx_mgr.search_context(session_id, query)
        
        return {
            "session_id": session_id,
            "query": query,
            "results": results,
            "count": len(results)
        }
        
    except Exception as e:
        logger.error(f"[GitMount] Search error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )
