"""
Git Mount — Shared Models & Helpers

Common Pydantic models and utility functions used across git mount sub-routers.
"""
import logging
import time
import base64
import hmac
import hashlib
import json
from typing import Any, Dict, List, Optional

from fastapi import HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy import select, and_
from sqlalchemy.ext.asyncio import AsyncSession

from src.infrastructure.auth.jwt_auth import TokenPayload, JWT_SECRET
from src.infrastructure.db.models.session_model import SessionModel

logger = logging.getLogger(__name__)


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


async def require_session(session_id: str, user: TokenPayload, db: AsyncSession) -> None:
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


# ── Request/Response Models ──

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
    type: str
    status: str
    size: int

class TreeResponse(BaseModel):
    path: str
    items: List[TreeItem]
    total_files: int
