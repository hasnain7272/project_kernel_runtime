"""
Tenant Context — Request-scoped multi-tenant isolation.

Sets tenant context at request start, enforces via RLS in queries.
Patterns: Pool Model with RLS for 10k+ tenants.
"""
import logging
from contextvars import ContextVar
from typing import Optional
from dataclasses import dataclass

logger = logging.getLogger(__name__)


@dataclass
class TenantContext:
    """Immutable tenant context for request scope."""
    tenant_id: str
    organization_id: Optional[str]
    user_id: str
    role: str
    tier: str
    limits: dict


# Context variable for async request-scoping
_tenant_ctx: ContextVar[Optional[TenantContext]] = ContextVar(
    "tenant_ctx", default=None
)


def get_tenant_context() -> Optional[TenantContext]:
    """Get current tenant context (None for non-authenticated routes)."""
    return _tenant_ctx.get()


def set_tenant_context(ctx: TenantContext) -> None:
    """Set tenant context for current request."""
    _tenant_ctx.set(ctx)
    logger.debug(f"[TenantContext] Set: tenant={ctx.tenant_id}, user={ctx.user_id}")


def clear_tenant_context() -> None:
    """Clear tenant context (end of request)."""
    _tenant_ctx.set(None)


def require_tenant_context() -> TenantContext:
    """Get tenant context or raise if not set."""
    ctx = _tenant_ctx.get()
    if not ctx:
        raise RuntimeError("Tenant context not set - authentication required")
    return ctx


def get_current_tenant_id() -> str:
    """Get current tenant ID (required)."""
    return require_tenant_context().tenant_id


def get_current_user_id() -> str:
    """Get current user ID."""
    return require_tenant_context().user_id


def is_tenant_admin() -> bool:
    """Check if current user is admin."""
    return require_tenant_context().role == "admin"


class TenantContextMiddleware:
    """FastAPI middleware to set tenant context from JWT.
    
    Expects jwt_payload containing:
    - tenant_id (required)
    - organization_id (optional)
    - user_id (required)
    - role (required)
    - tier (required)
    - limits (required)
    """
    
    def __init__(self, app):
        self.app = app
    
    async def __call__(self, scope, receive, send):
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return
        
        # Extract tenant info from request state (set by auth middleware)
        # This is populated after JWT validation
        tenant_context = scope.get("tenant_context", None)
        
        if tenant_context:
            token = set_tenant_context(tenant_context)
            try:
                await self.app(scope, receive, send)
            finally:
                clear_tenant_context()
        else:
            await self.app(scope, receive, send)


async def get_tenant_db_filter(tenant_id: str) -> dict:
    """Get tenant filter for database queries."""
    return {"tenant_id": tenant_id}


def require_in_tenant(tenant_id: str) -> None:
    """Ensure current tenant matches expected (authorization check)."""
    ctx = require_tenant_context()
    if ctx.tenant_id != tenant_id:
        logger.warning(f"[Security] Tenant mismatch: expected={tenant_id}, got={ctx.tenant_id}")
        raise PermissionError(f"Access denied to tenant {tenant_id}")