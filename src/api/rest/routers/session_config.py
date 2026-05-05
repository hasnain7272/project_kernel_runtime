"""Session provider and credential config routes."""
from datetime import datetime, timezone
from typing import Any, Dict

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from src.api.rest.dependencies import get_current_user_dep, get_db
from src.api.rest.routers.session_models import SessionConfigRequest
from src.api.rest.routers.session_utils import get_session_or_404
from src.infrastructure.auth.jwt_auth import TokenPayload
from src.infrastructure.security.crypto import decrypt_string, encrypt_string

router = APIRouter()


@router.patch("/{session_id}/config")
async def update_session_config(
    session_id: str,
    req: SessionConfigRequest,
    db: AsyncSession = Depends(get_db),
    user: TokenPayload = Depends(get_current_user_dep),
) -> Dict[str, Any]:
    session = await get_session_or_404(db, session_id, user.tenant_id)
    ctx = dict(session.context or {})
    patch = req.model_dump(exclude_none=True)
    if patch.get("api_key"):
        patch["api_key"] = encrypt_string(patch["api_key"])
    if patch.get("github_token"):
        github_ctx = dict(ctx.get("github") or {})
        github_ctx["access_token"] = encrypt_string(patch.pop("github_token"))
        ctx["github"] = github_ctx
    ctx.update(patch)
    session.context = ctx
    session.last_active_at = datetime.now(timezone.utc)
    await db.commit()
    return {"session_id": session_id, "status": "config_updated", "active_config": active_config(ctx)}


@router.get("/{session_id}/config")
async def get_session_config(
    session_id: str,
    db: AsyncSession = Depends(get_db),
    user: TokenPayload = Depends(get_current_user_dep),
) -> Dict[str, Any]:
    session = await get_session_or_404(db, session_id, user.tenant_id)
    ctx = session.context or {}
    return {
        "model": ctx.get("model", ""),
        "base_url": ctx.get("base_url", ""),
        "api_key_masked": mask_secret(decrypt_string(ctx.get("api_key", "")) if ctx.get("api_key") else "", 8, 4),
        "github_token_masked": mask_secret(decrypt_string(ctx.get("github", {}).get("access_token", "")) if ctx.get("github", {}).get("access_token") else "", 4, 4),
        "extra_body": ctx.get("extra_body"),
    }


def active_config(ctx: dict) -> Dict[str, Any]:
    return {
        "model": ctx.get("model"),
        "base_url": ctx.get("base_url"),
        "has_api_key": bool(ctx.get("api_key")),
        "has_github_token": bool(ctx.get("github", {}).get("access_token")),
    }


def mask_secret(value: str, head: int, tail: int) -> str:
    if not value:
        return ""
    return f"{value[:head]}...{value[-tail:]}" if len(value) > head + tail else "••••"
