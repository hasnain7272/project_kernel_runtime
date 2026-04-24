"""End-to-end integration tests."""
import pytest
import pytest_asyncio
import asyncio
from httpx import AsyncClient, ASGITransport
from sqlalchemy.ext.asyncio import AsyncSession

from src.api.fastapi_gateway import app
from src.infrastructure.db.session import AsyncSessionLocal, init_db


@pytest_asyncio.fixture
async def client():
    """Async HTTP client."""
    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test"
    ) as ac:
        yield ac


@pytest_asyncio.fixture
async def db():
    """Database session."""
    async with AsyncSessionLocal() as session:
        # Create tables
        await init_db()
        # Start a transaction
        trans = await session.begin()
        yield session
        # Rollback the transaction
        await trans.rollback()


class TestHealth:
    """Health check tests."""
    
    @pytest.mark.asyncio
    async def test_health_endpoint(self, client):
        """Health endpoint returns OK."""
        response = await client.get("/health")
        assert response.status_code == 200
        assert response.json()["status"] == "ok"


class TestSessions:
    """Session CRUD tests."""
    
    @pytest.mark.asyncio
    async def test_create_session(self, client):
        """Create session returns session ID."""
        # Register a user to get a token
        import uuid
        unique_id = uuid.uuid4().hex
        register_resp = await client.post(
            "/api/v1/auth/register",
            json={"email": f"test_{unique_id}@example.com", "password": "testpassword", "name": "Test User"}
        )
        assert register_resp.status_code == 201
        token = register_resp.json()["access_token"]
        
        # Create session with token
        response = await client.post(
            "/api/v1/sessions/",
            json={"name": "Test Session", "workspaces": [{"type": "local", "path": "."}]},
            headers={"Authorization": f"Bearer {token}"}
        )
        assert response.status_code == 201
        data = response.json()
        assert "id" in data
    
    @pytest.mark.asyncio
    async def test_list_sessions(self, client):
        """List sessions returns array."""
        # Register a user to get a token
        import uuid
        unique_id = uuid.uuid4().hex
        register_resp = await client.post(
            "/api/v1/auth/register",
            json={"email": f"test2_{unique_id}@example.com", "password": "testpassword", "name": "Test User 2"}
        )
        assert register_resp.status_code == 201
        token = register_resp.json()["access_token"]

        # First create a session so the list is not empty
        await client.post(
            "/api/v1/sessions/",
            json={"name": "Test Session", "workspaces": [{"type": "local", "path": "."}]},
            headers={"Authorization": f"Bearer {token}"}
        )

        response = await client.get(
            "/api/v1/sessions/",
            headers={"Authorization": f"Bearer {token}"}
        )
        assert response.status_code == 200
        data = response.json()
        assert "sessions" in data
        assert isinstance(data["sessions"], list)


class TestTasks:
    """Task execution tests."""
    
    @pytest.mark.asyncio
    async def test_create_task_requires_session(self, client, db):
        """Task creation requires valid session."""
        # First create a session
        session_resp = await client.post(
            "/api/v1/sessions/",
            json={"name": "Test Session"}
        )
        session_id = session_resp.json()["id"]
        
        # Then create a task
        response = await client.post(
            "/api/v1/tasks/",
            json={
                "session_id": session_id,
                "description": "Test task"
            }
        )
        assert response.status_code == 202
        data = response.json()
        assert "task_id" in data
        assert data["status"] == "accepted"


class TestGitHub:
    """GitHub integration tests."""
    
    @pytest.mark.asyncio
    async def test_github_auth_redirect(self, client, db, monkeypatch):
        """GitHub auth returns redirect."""
        # Set environment variables for GitHub OAuth
        monkeypatch.setenv("GITHUB_CLIENT_ID", "test_client_id")
        monkeypatch.setenv("GITHUB_CLIENT_SECRET", "test_client_secret")
        # Register a user to get a token
        import uuid
        unique_id = uuid.uuid4().hex
        register_resp = await client.post(
            "/api/v1/auth/register",
            json={"email": f"test_{unique_id}@example.com", "password": "testpassword", "name": "Test User"}
        )
        assert register_resp.status_code == 201
        token = register_resp.json()["access_token"]
    
        # First create a session
        session_resp = await client.post(
            "/api/v1/sessions/",
            json={"name": "Test Session"},
            headers={"Authorization": f"Bearer {token}"}
        )
        assert session_resp.status_code == 201
        session_id = session_resp.json()["id"]
    
        response = await client.get(
            "/api/v1/github/auth",
            params={"session_id": session_id},
            follow_redirects=False
        )
        assert response.status_code == 307
        assert "github.com" in response.headers["location"]
    
    @pytest.mark.asyncio
    async def test_github_repos_requires_auth(self, client, db):
        """GitHub repos requires connection."""
        response = await client.get(
            "/api/v1/github/repos",
            params={"session_id": "test-session"}
        )
        assert response.status_code == 404


class TestWorkspace:
    """Workspace API tests."""
    
    @pytest.mark.asyncio
    async def test_list_workspace(self, client):
        """List workspace files."""
        response = await client.get("/api/v1/workspace/files")
        assert response.status_code == 200
        data = response.json()
        assert "files" in data


class TestSecurity:
    """Security tests."""
    
    @pytest.mark.asyncio
    async def test_path_traversal_blocked(self, client):
        """Path traversal is blocked."""
        response = await client.post(
            "/api/v1/workspace/read",
            json={"filepath": "../etc/passwd"}
        )
        assert response.status_code in [400, 403, 422]
    
    @pytest.mark.asyncio
    async def test_cors_headers_present(self, client):
        """CORS headers are present."""
        response = await client.options(
            "/health", 
            headers={"Origin": "http://localhost:5173"}
        )
        assert "access-control-allow-origin" in response.headers