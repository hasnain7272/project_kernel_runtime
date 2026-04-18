"""
Async SQL Database Session configuration.

Reads DATABASE_URL from environment. Defaults to SQLite for local venv dev.
Set DATABASE_URL=postgresql+asyncpg://user:pass@host/db for production.
"""
import logging
import os
from typing import AsyncGenerator

from sqlalchemy.ext.asyncio import (
    create_async_engine,
    async_sessionmaker,
    AsyncSession,
)
from sqlalchemy.orm import declarative_base

logger = logging.getLogger(__name__)

DATABASE_URL = os.environ.get(
    "DATABASE_URL",
    "sqlite+aiosqlite:///./kernel.db",
)

engine = create_async_engine(DATABASE_URL, echo=False)
AsyncSessionLocal = async_sessionmaker(engine, expire_on_commit=False)
Base = declarative_base()


async def get_db_session() -> AsyncGenerator[AsyncSession, None]:
    """Dependency — yields an isolated async DB session."""
    async with AsyncSessionLocal() as session:
        try:
            yield session
            await session.commit()
        except Exception as e:
            logger.error(f"DB session error: {e}")
            await session.rollback()
            raise
        finally:
            await session.close()


async def init_db():
    """Create all tables from registered models."""
    from .models import session_model, task_model, message_model  # noqa
    async with engine.begin() as conn:
        logger.info("Initializing database schema...")
        await conn.run_sync(Base.metadata.create_all)
