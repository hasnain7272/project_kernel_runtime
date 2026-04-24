"""
JWT Authentication with Tenant Context.

Supports:
- JWT access/refresh tokens
- Per-tenant API keys
- Multi-tenant authorization

Pattern: JWT contains tenant_id, org_id, user_id, role.
"""
import logging
import os
import secrets
import time
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Optional

try:
    import jwt
    JWT_AVAILABLE = True
except ImportError:
    JWT_AVAILABLE = False
    jwt = None

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials

logger = logging.getLogger(__name__)


JWT_SECRET = os.environ.get("JWT_SECRET", os.environ.get("APP_SECRET_KEY", ""))
JWT_ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 60 * 24  # 24 hours
REFRESH_TOKEN_EXPIRE_DAYS = 30
_LOCAL_JWT_SECRET = secrets.token_urlsafe(32)


def _require_jwt_secret() -> str:
    secret = JWT_SECRET or _LOCAL_JWT_SECRET
    if not secret:
        raise RuntimeError("JWT secret is not configured")
    return secret


@dataclass
class TokenPayload:
    """JWT payload with tenant context."""
    tenant_id: str
    user_id: str
    email: str
    role: str
    tier: str
    limits: dict
    exp: int
    iat: int
    organization_id: Optional[str] = None


@dataclass
class AuthToken:
    """Authentication token pair."""
    access_token: str
    refresh_token: str
    expires_in: int
    token_type: str = "bearer"


def create_access_token(
    tenant_id: str,
    user_id: str,
    email: str,
    role: str = "developer",
    tier: str = "pro",
    organization_id: Optional[str] = None,
    limits: Optional[dict] = None,
) -> str:
    """Create JWT access token with tenant context."""
    if not JWT_AVAILABLE:
        raise RuntimeError("JWT support not available. Install PyJWT: pip install PyJWT")
    now = int(time.time())
    
    payload = {
        "tenant_id": tenant_id,
        "organization_id": organization_id,
        "user_id": user_id,
        "email": email,
        "role": role,
        "tier": tier,
        "limits": limits or {},
        "iat": now,
        "exp": now + (ACCESS_TOKEN_EXPIRE_MINUTES * 60),
        "type": "access",
    }
    
    return jwt.encode(payload, _require_jwt_secret(), algorithm=JWT_ALGORITHM)


def create_refresh_token(tenant_id: str, user_id: str) -> str:
    """Create refresh token."""
    if not JWT_AVAILABLE:
        raise RuntimeError("JWT support not available. Install PyJWT: pip install PyJWT")
    now = int(time.time())
    
    payload = {
        "tenant_id": tenant_id,
        "user_id": user_id,
        "iat": now,
        "exp": now + (REFRESH_TOKEN_EXPIRE_DAYS * 86400),
        "type": "refresh",
    }
    
    return jwt.encode(payload, _require_jwt_secret(), algorithm=JWT_ALGORITHM)


def decode_token(token: str) -> TokenPayload:
    """Decode and validate JWT token."""
    if not JWT_AVAILABLE:
        raise HTTPException(
            status.HTTP_500_INTERNAL_SERVER_ERROR,
            "JWT support is not available on this runtime",
        )
    try:
        payload = jwt.decode(token, _require_jwt_secret(), algorithms=[JWT_ALGORITHM])
        
        required = ["tenant_id", "user_id", "email", "role"]
        for field in required:
            if field not in payload:
                raise HTTPException(
                    status.HTTP_401_UNAUTHORIZED,
                    f"Missing required field: {field}"
                )
        
        return TokenPayload(
            tenant_id=payload["tenant_id"],
            organization_id=payload.get("organization_id"),
            user_id=payload["user_id"],
            email=payload["email"],
            role=payload["role"],
            tier=payload.get("tier", "pro"),
            limits=payload.get("limits", {}),
            exp=payload["exp"],
            iat=payload["iat"],
        )
    
    except jwt.ExpiredSignatureError:
        raise HTTPException(
            status.HTTP_401_UNAUTHORIZED,
            "Token has expired"
        )
    except jwt.InvalidTokenError as e:
        raise HTTPException(
            status.HTTP_401_UNAUTHORIZED,
            f"Invalid token: {str(e)}"
        )


async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(HTTPBearer()),
) -> TokenPayload:
    """Get current authenticated user from JWT."""
    return decode_token(credentials.credentials)


def get_optional_user(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(HTTPBearer(auto_error=False)),
) -> Optional[TokenPayload]:
    """Get user if authenticated, None otherwise."""
    if not credentials:
        return None
    try:
        return decode_token(credentials.credentials)
    except HTTPException:
        return None


def create_token_pair(
    tenant_id: str,
    user_id: str,
    email: str,
    role: str = "developer",
    tier: str = "pro",
    organization_id: Optional[str] = None,
    limits: Optional[dict] = None,
) -> AuthToken:
    """Create token pair (access + refresh)."""
    access = create_access_token(
        tenant_id, user_id, email, role, tier, organization_id, limits
    )
    refresh = create_refresh_token(tenant_id, user_id)
    
    return AuthToken(
        access_token=access,
        refresh_token=refresh,
        expires_in=ACCESS_TOKEN_EXPIRE_MINUTES * 60,
    )


def validate_api_key(api_key: str, expected_hash: str) -> bool:
    """Validate tenant API key."""
    import hashlib
    
    key_hash = hashlib.sha256(api_key.encode()).hexdigest()
    return key_hash == expected_hash


class TenantAuthMiddleware:
    """Middleware to extract tenant context from JWT/API key.
    
    Sets scope[tenant_context] for downstream handlers.
    """
    
    def __init__(self, app):
        self.app = app
    
    async def __call__(self, scope, receive, send):
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return
        
        # Extract auth header
        headers = dict(scope.get("headers", []))
        auth_header = headers.get(b"authorization", b"").decode()
        
        if auth_header.startswith("Bearer "):
            token = auth_header[7:]
            try:
                payload = decode_token(token)
                # Set tenant context in scope for downstream
                scope["tenant_context"] = payload
            except HTTPException:
                pass
        
        await self.app(scope, receive, send)
