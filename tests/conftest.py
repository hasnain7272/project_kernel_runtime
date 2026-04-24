"""Pytest configuration and fixtures."""
import asyncio
import pytest
import pytest_asyncio
from unittest.mock import AsyncMock, MagicMock, patch

from src.infrastructure.db.session import engine, init_db, AsyncSessionLocal
from sqlalchemy import text

@pytest_asyncio.fixture(autouse=True)
async def db_cleanup():
    """Clean database between tests to prevent locking issues."""
    # Drop all tables and recreate them
    async with engine.begin() as conn:
        # Get all table names
        result = await conn.execute(text("SELECT name FROM sqlite_master WHERE type='table'"))
        tables = result.fetchall()
        # Drop each table
        for table in tables:
            await conn.execute(text(f"DROP TABLE IF EXISTS {table[0]}"))
    # Recreate tables
    await init_db()

@pytest_asyncio.fixture
async def async_client():
    """Async HTTP client for API tests."""
    from httpx import AsyncClient
    from src.api.fastapi_gateway import app
    async with AsyncClient(app=app, base_url="http://test") as client:
        yield client


@pytest.fixture
def mock_db():
    """Mock database session."""
    return AsyncMock()


@pytest.fixture
def mock_broker():
    """Mock message broker."""
    broker = AsyncMock()
    broker.publish = AsyncMock(return_value="msg-id-123")
    broker.subscribe = AsyncMock()
    return broker


@pytest.fixture
def sample_session_id():
    """Sample session ID for tests."""
    return "test-session-123"


@pytest.fixture
def sample_task_id():
    """Sample task ID for tests."""
    return "test-task-456"


@pytest.fixture
def mock_llm_response():
    """Sample LLM API response."""
    return {
        "choices": [{
            "message": {
                "content": "I'll help you with that task.",
                "tool_calls": []
            }
        }]
    }


@pytest_asyncio.fixture
async def async_client():
    """Async HTTP client for API tests."""
    from httpx import AsyncClient
    from src.api.fastapi_gateway import app
    async with AsyncClient(app=app, base_url="http://test") as client:
        yield client


@pytest.fixture
def mock_db():
    """Mock database session."""
    return AsyncMock()


@pytest.fixture
def mock_broker():
    """Mock message broker."""
    broker = AsyncMock()
    broker.publish = AsyncMock(return_value="msg-id-123")
    broker.subscribe = AsyncMock()
    return broker


@pytest.fixture
def sample_session_id():
    """Sample session ID for tests."""
    return "test-session-123"


@pytest.fixture
def sample_task_id():
    """Sample task ID for tests."""
    return "test-task-456"


@pytest.fixture
def mock_llm_response():
    """Sample LLM API response."""
    return {
        "choices": [{
            "message": {
                "content": "I'll help you with that task.",
                "tool_calls": []
            }
        }]
    }