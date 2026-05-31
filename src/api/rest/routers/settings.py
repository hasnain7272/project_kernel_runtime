from typing import Dict, Any, List
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm.attributes import flag_modified

from src.api.rest.dependencies import get_db, get_current_user_dep
from src.infrastructure.auth.jwt_auth import TokenPayload
from src.infrastructure.db.models.tenant_model import TenantModel
from src.infrastructure.security.crypto import encrypt_string

router = APIRouter(prefix="/api/v1/settings", tags=["Settings"])

class BYOMConfig(BaseModel):
    id: str
    name: str
    provider: str | None = None
    model: str
    api_key: str
    base_url: str | None = None
    temperature: float | None = None
    top_p: float | None = None
    max_tokens: int | None = None

@router.post("/byok", response_model=Dict[str, Any])
async def save_byok(
    byom: BYOMConfig,
    db: AsyncSession = Depends(get_db),
    user: TokenPayload = Depends(get_current_user_dep)
):
    """
    Securely store BYOM configuration in the tenant's config.
    Overwrites the config with the same ID, or appends it.
    """
    result = await db.execute(select(TenantModel).where(TenantModel.id == user.tenant_id))
    tenant = result.scalar_one_or_none()
    
    if not tenant:
        raise HTTPException(status_code=404, detail="Tenant not found")
        
    config = dict(tenant.config) if tenant.config else {}
    byom_list: List[Dict[str, Any]] = config.get("byom_configs", [])
    
    payload = byom.model_dump()
    if byom.api_key:
        payload["api_key"] = encrypt_string(byom.api_key)

    # Check if exists, update or append. Empty API key means "keep existing key".
    exists = False
    for i, b in enumerate(byom_list):
        if b.get("id") == byom.id:
            if not byom.api_key:
                payload["api_key"] = b.get("api_key", "")
            byom_list[i] = payload
            exists = True
            break
            
    if not exists:
        byom_list.append(payload)
        
    config["byom_configs"] = byom_list
    tenant.config = config
    flag_modified(tenant, "config")
    
    db.add(tenant)
    await db.commit()
    
    return {"status": "success", "message": "BYOM config securely stored"}

@router.get("/byok", response_model=Dict[str, Any])
async def get_byok_list(
    db: AsyncSession = Depends(get_db),
    user: TokenPayload = Depends(get_current_user_dep)
):
    """
    Returns the list of configured models, BUT STRIPS THE API KEY.
    This ensures the UI never receives the plaintext API key back.
    """
    result = await db.execute(select(TenantModel).where(TenantModel.id == user.tenant_id))
    tenant = result.scalar_one_or_none()
    
    if not tenant:
        raise HTTPException(status_code=404, detail="Tenant not found")
        
    config = dict(tenant.config) if tenant.config else {}
    byom_list = config.get("byom_configs", [])
    
    # Strip API keys
    safe_list = []
    for b in byom_list:
        safe_list.append({
            "id": b.get("id"),
            "name": b.get("name"),
            "provider": b.get("provider"),
            "model": b.get("model"),
            "base_url": b.get("base_url"),
            "temperature": b.get("temperature"),
            "top_p": b.get("top_p"),
            "max_tokens": b.get("max_tokens"),
            "is_configured": bool(b.get("api_key"))
        })
        
    return {"status": "success", "data": safe_list}
