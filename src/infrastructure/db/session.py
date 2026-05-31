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

# Production-grade pool configuration
_pool_config = {
    "pool_size": 20,           
    "max_overflow": 30,       
    "pool_timeout": 30,       
    "pool_recycle": 1800,     
    "pool_pre_ping": True,   
}

# Only apply pool config for PostgreSQL (not SQLite)
_is_postgres = "postgresql" in DATABASE_URL.lower()
engine_kwargs = {"echo": False}

from sqlalchemy import event

if _is_postgres:
    engine_kwargs.update(_pool_config)
    logger.info(f"[DB] Using PostgreSQL with pool_size=20, max_overflow=30")
else:
    logger.warning("[DB] Using SQLite - using StaticPool for concurrency safety")
    from sqlalchemy.pool import StaticPool
    engine_kwargs["connect_args"] = {"timeout": 30, "check_same_thread": False}
    engine_kwargs["poolclass"] = StaticPool

engine = create_async_engine(DATABASE_URL, **engine_kwargs)

if not _is_postgres:
    @event.listens_for(engine.sync_engine, "connect")
    def set_sqlite_pragma(dbapi_connection, connection_record):
        cursor = dbapi_connection.cursor()
        cursor.execute("PRAGMA journal_mode=WAL")
        cursor.execute("PRAGMA synchronous=NORMAL")
        cursor.execute("PRAGMA busy_timeout=30000")
        cursor.close()
from contextlib import asynccontextmanager

AsyncSessionLocal = async_sessionmaker(engine, expire_on_commit=False)
Base = declarative_base()

@asynccontextmanager
async def get_db_context():
    """Async context manager for DB sessions, for use outside FastAPI dependencies."""
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


def get_session_factory():
    """Returns the async sessionmaker."""
    return AsyncSessionLocal


def get_engine():
    """Returns the async engine."""
    return engine


async def init_db():
    """Create tables from registered models.
    
    For development (SQLite): Uses create_all + auto-migrate missing columns.
    For production (PostgreSQL): Use Alembic migrations instead:
        alembic upgrade head
    """
    from .models import session_model, task_model, message_model  # noqa
    from .models.tenant_model import TenantModel, OrganizationModel, UserModel  # noqa
    from .models.folder_model import FolderModel  # noqa
    from .models.workspace_model import WorkspaceModel  # noqa

    logger.info(f"[DB] Initializing DB. _is_postgres={_is_postgres}, DATABASE_URL={DATABASE_URL}")
    if _is_postgres:
        logger.warning(
            "[DB] PostgreSQL detected — use 'alembic upgrade head' for schema management. "
            "Skipping create_all to prevent drift."
        )
        return

    async with engine.begin() as conn:
        logger.info("Initializing database schema...")
        await conn.run_sync(Base.metadata.create_all)
        logger.info("Database schema created.")
        # Auto-migrate: add any missing columns to existing tables (SQLite only)
        await conn.run_sync(_auto_migrate_columns)
        logger.info("Auto-migration completed.")


def _auto_migrate_columns(connection):
    """Add missing columns to existing SQLite tables.
    
    SQLAlchemy's create_all() won't modify existing tables.
    This inspects each table and issues ALTER TABLE for any
    columns defined in the ORM that don't exist in the DB yet.
    """
    from sqlalchemy import inspect as sa_inspect, text

    inspector = sa_inspect(connection)
    
    for table_name, table in Base.metadata.tables.items():
        if not inspector.has_table(table_name):
            continue
        
        existing_cols = {col["name"] for col in inspector.get_columns(table_name)}
        
        for column in table.columns:
            if column.name not in existing_cols:
                # Determine SQL type and default
                col_type = column.type.compile(connection.dialect)
                default_val = "NULL"
                if column.default is not None:
                    # Attempt to get a literal value for common defaults
                    if hasattr(column.default, 'arg') and not callable(column.default.arg):
                        arg = column.default.arg
                        if isinstance(arg, (int, float)):
                            default_val = str(arg)
                        elif isinstance(arg, bool):
                            default_val = "1" if arg else "0"
                        else:
                            default_val = f"'{arg}'"
                    else:
                        # Fallback for complex defaults or callables
                        default_val = "0" if "INT" in str(col_type).upper() or "FLOAT" in str(col_type).upper() else "''"
                elif not column.nullable:
                    default_val = "0" if "INT" in str(col_type).upper() or "FLOAT" in str(col_type).upper() else "''"
                
                stmt = f'ALTER TABLE "{table_name}" ADD COLUMN "{column.name}" {col_type} DEFAULT {default_val}'
                logger.info(f"[DB Migration] {stmt}")
                connection.execute(text(stmt))
