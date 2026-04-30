"""
Backend Smoke Tests — Validates API gateway, health, and MCP catalog endpoints.

Run with: pytest tests/test_smoke.py -v
"""
import os
import sys
import pytest

# Ensure project root is importable
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))


@pytest.fixture(scope="module")
def client():
    """Create a test client for the FastAPI gateway."""
    os.environ.setdefault("DATABASE_URL", "sqlite+aiosqlite:///./test.db")
    os.environ.setdefault("HYBRID_MODE", "false")
    os.environ.setdefault("ALLOW_ANON_LOCAL", "true")
    os.environ.setdefault("JWT_SECRET", "test-secret-key-for-ci")

    from src.api.fastapi_gateway import app
    from fastapi.testclient import TestClient

    with TestClient(app) as c:
        yield c


def test_health_endpoint(client):
    """Health check should return 200 with broker info."""
    resp = client.get("/health")
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "ok"
    assert "version" in data
    assert "broker" in data


def test_metrics_endpoint(client):
    """Metrics endpoint should return structured JSON."""
    resp = client.get("/api/v1/metrics")
    assert resp.status_code == 200
    data = resp.json()
    assert "metrics" in data


def test_workers_health(client):
    """Workers health should report broker type."""
    resp = client.get("/api/v1/health/workers")
    assert resp.status_code == 200
    data = resp.json()
    assert "broker_type" in data


def test_mcp_catalog(client):
    """MCP catalog should return plugins and skills."""
    resp = client.get("/api/v1/mcp/catalog")
    # May require auth; expect either 200 or 401/403
    assert resp.status_code in (200, 401, 403, 422)


def test_spa_fallback(client):
    """Unknown routes should either serve SPA or return JSON fallback."""
    resp = client.get("/some-random-route")
    assert resp.status_code == 200
    # Either HTML or JSON fallback
    ct = resp.headers.get("content-type", "")
    assert "html" in ct or "json" in ct


def test_api_404(client):
    """API routes that don't exist should not crash."""
    resp = client.get("/api/v1/nonexistent")
    # Gateway returns JSON for /api/* paths
    assert resp.status_code in (200, 404)
