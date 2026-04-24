"""
Sessions Router — Production-Grade Multi-Tenant Session Management

Supports:
- Multiple workspace bindings per session (local folders + git repos)
- BYOK (Bring Your Own Key) model configuration
- Tenant-scoped CRUD with JWT authorization
"""
import uuid
from typing import Any, Dict, List, Optional
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy import select, and_, update, delete, exists
from sqlalchemy.ext.asyncio import AsyncSession

from src.api.rest.dependencies import get_db, get_current_user_dep
from src.infrastructure.auth.jwt_auth import TokenPayload
from src.infrastructure.db.models.session_model import SessionModel
from src.infrastructure.db.models.workspace_model import WorkspaceModel
from src.infrastructure.security.crypto import encrypt_string, decrypt_string
from src.infrastructure.runtime.paths import workspace_root
from src.infrastructure.db.models.session_workspace import session_workspace

router = APIRouter(prefix="/api/v1/sessions", tags=["Sessions"])


# ── Request / Response Schemas ───────────────────────────


class WorkspaceBinding(BaseModel):
    """A workspace attached to a session."""
    type: str = Field(..., pattern="^(local|git)$", description="'local' or 'git'")
    path: Optional[str] = Field(None, description="Absolute path for local folders")
    url: Optional[str] = Field(None, description="Git clone URL for repos")
    branch: str = Field("main", description="Git branch (default: main)")
    slug: Optional[str] = Field(None, description="Filesystem slug (auto-generated if empty)")


class SessionCreateRequest(BaseModel):
    name: str = "New Session"
    workspaces: List[WorkspaceBinding] = Field(
        default_factory=list,
        description="Workspace bindings (local folders or git repos)",
    )
    mode: str = "web"


class SessionConfigRequest(BaseModel):
    model: Optional[str] = None
    api_key: Optional[str] = None
    base_url: Optional[str] = None
    extra_body: Optional[Dict[str, Any]] = None


class SessionRenameRequest(BaseModel):
    name: str


class WorkspaceAddRequest(BaseModel):
    workspace: WorkspaceBinding


# ── Helpers ──────────────────────────────────────────────


def _make_slug(ws: WorkspaceBinding) -> str:
    """Generate a filesystem-safe slug for a workspace."""
    if ws.slug:
        return ws.slug
    if ws.type == "local" and ws.path:
        # Use last folder name
        import pathlib
        return pathlib.PurePath(ws.path).name.lower().replace(" ", "-")[:64]
    if ws.type == "git" and ws.url:
        # Extract repo name from URL
        name = ws.url.rstrip("/").split("/")[-1]
        if name.endswith(".git"):
            name = name[:-4]
        return name.lower().replace(" ", "-")[:64]
    return f"workspace-{uuid.uuid4().hex[:8]}"


def _prepare_workspaces(
    workspaces: List[WorkspaceBinding], tenant_id: str
) -> list[dict]:
    """Validate and normalize workspace bindings."""
    result = []
    for ws in workspaces:
        slug = _make_slug(ws)

        # Local workspaces are always managed under the tenant root.
        ws_root = workspace_root() / f"tenant_{tenant_id}" / slug
        ws_root.mkdir(parents=True, exist_ok=True)

        entry = {
            "type": ws.type,
            "slug": slug,
            "branch": ws.branch,
            "name": slug,
        }
        if ws.type == "local":
            entry["path"] = str(ws_root)
        elif ws.type == "git":
            entry["url"] = ws.url
        result.append(entry)
    return result


def _session_to_dict(s: SessionModel) -> Dict[str, Any]:
    """Serialize a session to API response."""
    return {
        "id": s.id,
        "name": s.name,
        "tenant_id": s.tenant_id,
        "user_id": s.user_id,
        "mode": s.mode,
        "user_role": s.user_role,
        "workspaces": [
            {
                "type": ws.type,
                "slug": ws.slug,
                "name": ws.name,
                "path": ws.path,
                "url": ws.url,
                "branch": ws.branch,
            }
            for ws in (s.workspaces or [])
        ],
        "is_active": s.is_active,
        "created_at": s.created_at.isoformat() if s.created_at else None,
        "last_active_at": s.last_active_at.isoformat() if s.last_active_at else None,
    }


# ── Routes ───────────────────────────────────────────────


@router.post("/", status_code=status.HTTP_201_CREATED)
async def create_session(
    req: SessionCreateRequest,
    db: AsyncSession = Depends(get_db),
    user: TokenPayload = Depends(get_current_user_dep),
) -> Dict[str, Any]:
    """Create a new session with workspace bindings."""
    workspaces = _prepare_workspaces(req.workspaces, user.tenant_id)

    # If no workspaces provided, create a default one
    if not workspaces:
        default_slug = f"workspace-{uuid.uuid4().hex[:8]}"
        ws_root = workspace_root() / f"tenant_{user.tenant_id}" / default_slug
        ws_root.mkdir(parents=True, exist_ok=True)
        workspaces = [{"type": "local", "slug": default_slug, "path": str(ws_root), "branch": "main"}]

    # Create or get workspace entries and link to session
    workspace_objs = []
    for ws_data in workspaces:
        # Check if workspace already exists
        result = await db.execute(
            select(WorkspaceModel).where(
                and_(
                    WorkspaceModel.tenant_id == user.tenant_id,
                    WorkspaceModel.slug == ws_data["slug"]
                )
            )
        )
        existing_ws = result.scalar_one_or_none()
        
        if existing_ws:
            workspace_objs.append(existing_ws)
        else:
            # Create new workspace
            new_ws = WorkspaceModel(
                tenant_id=user.tenant_id,
                slug=ws_data["slug"],
                name=ws_data.get("name", ws_data["slug"]),
                type=ws_data["type"],
                path=ws_data.get("path"),
                url=ws_data.get("url"),
                branch=ws_data.get("branch", "main"),
            )
            db.add(new_ws)
            workspace_objs.append(new_ws)

    # Create session without mounted_folders (use workspaces relationship)
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
    return _session_to_dict(session)


@router.get("/")
async def list_sessions(
    db: AsyncSession = Depends(get_db),
    user: TokenPayload = Depends(get_current_user_dep),
) -> Dict[str, Any]:
    """List active sessions for the current tenant."""
    result = await db.execute(
        select(SessionModel).where(
            and_(
                SessionModel.tenant_id == user.tenant_id,
                SessionModel.is_active == True,
            )
        ).order_by(SessionModel.last_active_at.desc())
    )
    rows = result.scalars().all()
    return {"sessions": [_session_to_dict(s) for s in rows]}


@router.get("/{session_id}")
async def get_session(
    session_id: str,
    db: AsyncSession = Depends(get_db),
    user: TokenPayload = Depends(get_current_user_dep),
) -> Dict[str, Any]:
    """Get a single session by ID."""
    session = await _get_session_or_404(db, session_id, user.tenant_id)
    return _session_to_dict(session)


@router.patch("/{session_id}/name")
async def rename_session(
    session_id: str,
    req: SessionRenameRequest,
    db: AsyncSession = Depends(get_db),
    user: TokenPayload = Depends(get_current_user_dep),
) -> Dict[str, Any]:
    """Rename a session."""
    session = await _get_session_or_404(db, session_id, user.tenant_id)
    session.name = req.name.strip()[:128]
    session.last_active_at = datetime.now(timezone.utc)
    await db.commit()
    return {"session_id": session_id, "name": session.name}


# ── Workspace Management ────────────────────────────────


@router.post("/{session_id}/workspaces")
async def add_workspace(
    session_id: str,
    req: WorkspaceAddRequest,
    db: AsyncSession = Depends(get_db),
    user: TokenPayload = Depends(get_current_user_dep),
) -> Dict[str, Any]:
    """Add a workspace (local folder or git repo) to an existing session."""
    session = await _get_session_or_404(db, session_id, user.tenant_id)

    new_ws_data = _prepare_workspaces([req.workspace], user.tenant_id)
    if not new_ws_data:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Invalid workspace binding")

    ws_data = new_ws_data[0]
    # Check if workspace already exists
    result = await db.execute(
        select(WorkspaceModel).where(
            and_(
                WorkspaceModel.tenant_id == user.tenant_id,
                WorkspaceModel.slug == ws_data["slug"]
            )
        )
    )
    existing_ws = result.scalar_one_or_none()
    
    if not existing_ws:
        # Create new workspace
        existing_ws = WorkspaceModel(
            tenant_id=user.tenant_id,
            slug=ws_data["slug"],
            name=ws_data.get("name", ws_data["slug"]),
            type=ws_data["type"],
            path=ws_data.get("path"),
            url=ws_data.get("url"),
            branch=ws_data.get("branch", "main"),
        )
        db.add(existing_ws)

    # Add to session's workspaces
    current = list(session.workspaces or [])
    existing_slugs = {ws.slug for ws in current}
    if existing_ws.slug not in existing_slugs:
        current.append(existing_ws)
        session.workspaces = current

    session.last_active_at = datetime.now(timezone.utc)
    await db.commit()
    await db.refresh(session)
    return _session_to_dict(session)


@router.delete("/{session_id}/workspaces/{slug}")
async def remove_workspace(
    session_id: str,
    slug: str,
    db: AsyncSession = Depends(get_db),
    user: TokenPayload = Depends(get_current_user_dep),
) -> Dict[str, Any]:
    """Remove a workspace binding from a session."""
    session = await _get_session_or_404(db, session_id, user.tenant_id)

    current = list(session.workspaces or [])
    updated = [ws for ws in current if ws.slug != slug]
    if len(updated) == len(current):
        raise HTTPException(status.HTTP_404_NOT_FOUND, f"Workspace '{slug}' not found in session")

    session.workspaces = updated
    session.last_active_at = datetime.now(timezone.utc)
    await db.commit()
    await db.refresh(session)
    return _session_to_dict(session)


@router.get("/{session_id}/workspaces")
async def list_workspaces(
    session_id: str,
    db: AsyncSession = Depends(get_db),
    user: TokenPayload = Depends(get_current_user_dep),
) -> Dict[str, Any]:
    """List all workspace bindings for a session."""
    session = await _get_session_or_404(db, session_id, user.tenant_id)
    workspaces = session.workspaces or []
    return {
        "workspaces": [
            {
                "type": ws.type,
                "slug": ws.slug,
                "name": ws.name,
                "path": ws.path,
                "url": ws.url,
                "branch": ws.branch,
            }
            for ws in workspaces
        ]
    }


# ── BYOK Config ─────────────────────────────────────────


@router.patch("/{session_id}/config")
async def update_session_config(
    session_id: str,
    req: SessionConfigRequest,
    db: AsyncSession = Depends(get_db),
    user: TokenPayload = Depends(get_current_user_dep),
) -> Dict[str, Any]:
    """Update session BYOK configuration."""
    session = await _get_session_or_404(db, session_id, user.tenant_id)

    ctx = dict(session.context or {})
    patch = req.model_dump(exclude_none=True)

    if "api_key" in patch and patch["api_key"]:
        patch["api_key"] = encrypt_string(patch["api_key"])

    ctx.update(patch)
    session.context = ctx
    session.last_active_at = datetime.now(timezone.utc)
    await db.commit()
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
    user: TokenPayload = Depends(get_current_user_dep),
) -> Dict[str, Any]:
    """Get session BYOK configuration (API key masked)."""
    session = await _get_session_or_404(db, session_id, user.tenant_id)

    ctx = session.context or {}
    raw_key_enc = ctx.get("api_key", "")
    decrypted_key = decrypt_string(raw_key_enc) if raw_key_enc else ""
    masked = (
        f"{decrypted_key[:8]}...{decrypted_key[-4:]}"
        if len(decrypted_key) > 12
        else ("••••••" if decrypted_key else "")
    )

    return {
        "model": ctx.get("model", ""),
        "base_url": ctx.get("base_url", ""),
        "api_key_masked": masked,
        "extra_body": ctx.get("extra_body"),
    }


# ── Lifecycle ────────────────────────────────────────────


@router.delete("/{session_id}")
async def end_session(
    session_id: str,
    db: AsyncSession = Depends(get_db),
    user: TokenPayload = Depends(get_current_user_dep),
) -> Dict[str, str]:
    """End (deactivate) a session."""
    session = await _get_session_or_404(db, session_id, user.tenant_id)
    session.is_active = False
    await db.commit()
    return {"status": "ended", "session_id": session_id}


# ── Internal Helpers ─────────────────────────────────────


async def _get_session_or_404(
    db: AsyncSession, session_id: str, tenant_id: str
) -> SessionModel:
    """Fetch session with tenant isolation or raise 404."""
    result = await db.execute(
        select(SessionModel).where(
            and_(
                SessionModel.id == session_id,
                SessionModel.tenant_id == tenant_id,
            )
        )
    )
    session = result.scalar_one_or_none()
    if not session:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Session not found")
    return session
