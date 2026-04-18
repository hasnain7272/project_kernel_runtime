"""
FastAPI dependencies.
"""
import os
from typing import AsyncGenerator

from fastapi import Header, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from src.infrastructure.db.session import get_db_session
from src.infrastructure.queue.redis_streams_broker import get_streams_broker
from src.infrastructure.runtime.config import ALLOW_ANON_LOCAL
from src.infrastructure.resilience.rate_limiter import RedisRateLimiter, RateLimitConfig, RateLimitStrategy

REDIS_URL = os.environ.get("REDIS_URL", "")

_rate_limiter = None

async def get_rate_limiter():
    global _rate_limiter
    if _rate_limiter is None and REDIS_URL:
        _rate_limiter = RedisRateLimiter(REDIS_URL)
    return _rate_limiter


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    async for session in get_db_session():
        yield session


async def get_broker_dep():
    return await get_streams_broker()


def resolve_current_user(tenant_id: str | None) -> str:
    if tenant_id and tenant_id.strip():
        return tenant_id.strip()
    if ALLOW_ANON_LOCAL:
        return "local"
    raise HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Missing X-Tenant-Id header.",
    )


async def get_current_user(x_tenant_id: str = Header(default=None)):
    return resolve_current_user(x_tenant_id)


async def check_rate_limit(user_id: str):
    """Rate limit check - returns None if allowed, raises HTTPException if blocked."""
    limiter = await get_rate_limiter()
    if limiter is None:
        return  # No Redis = no rate limiting
    
    config = RateLimitConfig(
        requests_per_minute=60,
        requests_per_hour=500,
        strategy=RateLimitStrategy.SLIDING_WINDOW,
    )
    
    status = await limiter.check_rate_limit(f"ratelimit:{user_id}", config)
    
    if not status.allowed:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail=f"Rate limit exceeded. Try again in {int(status.retry_after or 60)} seconds."
        )
