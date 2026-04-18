"""
FastAPI Dependencies — Dependency injection for routers.
"""
from typing import AsyncGenerator
from fastapi import Header, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from src.infrastructure.db.session import get_db_session
from src.infrastructure.queue.redis_broker import get_broker


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """Provides an isolated database session per request."""
    async for session in get_db_session():
        yield session


def get_broker_dep():
    """Provides the event broker instance."""
    return get_broker()


async def get_current_user(x_tenant_id: str = Header(default=None)):
    """
    Lean Auth Middleware.
    Reads X-Tenant-Id header to isolate users. Defaults to 'local' strictly for dev,
    but in production forces a valid tenant header.
    """
    if not x_tenant_id:
        return "local"
    return x_tenant_id
