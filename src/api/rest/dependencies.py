"""
FastAPI Dependencies — Dependency injection for routers.
"""
from typing import AsyncGenerator
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
