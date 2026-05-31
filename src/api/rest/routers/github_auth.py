"""GitHub OAuth Router - Premium session-based auth."""
import logging
from typing import Optional
from fastapi import APIRouter, Body, Depends, HTTPException, Query, status
from fastapi.responses import RedirectResponse
from pydantic import BaseModel
from sqlalchemy import select, and_
from sqlalchemy.ext.asyncio import AsyncSession
from src.api.rest.dependencies import get_db, get_current_user_dep
from src.infrastructure.auth.github_oauth import get_github_client
from src.infrastructure.auth.jwt_auth import TokenPayload
from src.infrastructure.db.models.session_model import SessionModel
from src.infrastructure.security.crypto import decrypt_string, encrypt_string
from src.api.rest.routers.git_mount import create_signed_state, parse_signed_state

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/v1/github", tags=["GitHub"])


class ConnectResponse(BaseModel):
    success: bool
    user: dict
    message: str


class ConnectRequest(BaseModel):
    code: str
    state: str
    redirect_uri: str = "http://localhost:5173/github/callback"


@router.get("/auth")
async def auth_redirect(
    session_id: str = Query(...),
    redirect_uri: str = Query("http://localhost:5173/github/callback"),
):
    """Redirect to GitHub OAuth."""
    try:
        client = get_github_client()
        state = create_signed_state(session_id)
        return RedirectResponse(url=client.get_auth_url(state, redirect_uri))
    except RuntimeError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/connect", response_model=ConnectResponse)
async def connect(
    payload: ConnectRequest | None = Body(default=None),
    code: str | None = Query(default=None),
    state: str | None = Query(default=None),
    redirect_uri: str | None = Query(default=None),
    db: AsyncSession = Depends(get_db),
    user: TokenPayload = Depends(get_current_user_dep),
):
    """Complete OAuth and store token in session."""
    try:
        client = get_github_client()
    except RuntimeError as e:
        raise HTTPException(status_code=400, detail=str(e))

    code = code or (payload.code if payload else None)
    state = state or (payload.state if payload else None)
    redirect_uri = redirect_uri or (payload.redirect_uri if payload else None) or "http://localhost:5173/github/callback"
    if not code or not state:
        raise HTTPException(status_code=400, detail="Missing OAuth code or state")

    try:
        github_user = await client.exchange_code(code, redirect_uri)
        session_id = parse_signed_state(state)
        result = await db.execute(
            select(SessionModel).where(
                and_(
                    SessionModel.id == session_id,
                    SessionModel.tenant_id == user.tenant_id,
                )
            )
        )
        session = result.scalar_one_or_none()
        if not session:
            raise HTTPException(status_code=404, detail="Session not found")

        ctx = dict(session.context or {})
        ctx["github"] = {
            "user_id": github_user.id,
            "login": github_user.login,
            "name": github_user.name,
            "email": github_user.email,
            "avatar_url": github_user.avatar_url,
            "access_token": encrypt_string(github_user.access_token),
        }
        session.context = ctx
        await db.commit()
        
        return ConnectResponse(
            success=True,
            user={"id": github_user.id, "login": github_user.login, 
                  "name": github_user.name, "avatar_url": github_user.avatar_url},
            message=f"Connected as {github_user.login}"
        )
    except Exception as e:
        logger.error(f"[GitHub] Connect failed: {e}")
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/repos")
async def list_repos(
    session_id: str = Query(...),
    page: int = Query(1),
    db: AsyncSession = Depends(get_db),
    user: TokenPayload = Depends(get_current_user_dep),
):
    """List user's repositories."""
    result = await db.execute(select(SessionModel).where(SessionModel.id == session_id))
    session = result.scalar_one_or_none()
    
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    
    # Verify tenant owns session
    if session.tenant_id != user.tenant_id:
        raise HTTPException(status_code=403, detail="Not authorized")
    
    ctx = session.context or {}
    token = ctx.get("github", {}).get("access_token")
    
    if not token:
        raise HTTPException(status_code=401, detail="GitHub not connected")
    
    try:
        client = get_github_client()
    except RuntimeError as e:
        raise HTTPException(status_code=400, detail=str(e))

    repos = await client.list_repos(_resolve_token(token), page)
    
    return {
        "repos": [{"id": r["id"], "name": r["name"], "full_name": r["full_name"],
                   "description": r.get("description"), "private": r["private"],
                   "updated_at": r["updated_at"]} for r in repos]
    }


@router.delete("/disconnect")
async def disconnect(
    session_id: str = Query(...),
    db: AsyncSession = Depends(get_db),
    user: TokenPayload = Depends(get_current_user_dep),
):
    """Remove GitHub connection."""
    result = await db.execute(select(SessionModel).where(SessionModel.id == session_id))
    session = result.scalar_one_or_none()
    
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    
    # Verify tenant owns session
    if session.tenant_id != user.tenant_id:
        raise HTTPException(status_code=403, detail="Not authorized")
    
    ctx = dict(session.context or {})
    if "github" in ctx:
        del ctx["github"]
        session.context = ctx
        await db.commit()
    
    return {"success": True, "message": "Disconnected"}


@router.get("/status")
async def status(
    session_id: str = Query(...),
    db: AsyncSession = Depends(get_db),
    user: TokenPayload = Depends(get_current_user_dep),
):
    """Return GitHub connection state without exposing credentials."""
    result = await db.execute(
        select(SessionModel).where(
            and_(
                SessionModel.id == session_id,
                SessionModel.tenant_id == user.tenant_id,
            )
        )
    )
    session = result.scalar_one_or_none()
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")

    github = (session.context or {}).get("github") or {}
    token = github.get("access_token")
    return {
        "connected": bool(token),
        "user": {
            "id": github.get("user_id"),
            "login": github.get("login"),
            "name": github.get("name"),
            "avatar_url": github.get("avatar_url"),
        } if token else None,
    }


def _resolve_token(token: str) -> str:
    if not token:
        return ""
    if token.startswith("gAAAA"):
        return decrypt_string(token)
    return token
