"""
Tests for health check components.
"""

import pytest
from unittest.mock import Mock, patch, AsyncMock
from fastapi import FastAPI
from fastapi.testclient import TestClient

from project_kernel_runtime.observability.health import (
    HealthChecker,
    setup_health_check_routes,
    get_health_checker,
    register_custom_health_check
)


class TestHealthChecker:
    """Test cases for health checker."""
    
    def test_health_checker_initialization(self):
        """Test health checker initialization."""
        checker = HealthChecker()
        
        assert checker.start_time is not None
        assert len(checker.checks) > 0
        assert "database" in checker.checks
        assert "redis" in checker.checks
        assert "llm_provider" in checker.checks
        assert "mcp_server" in checker.checks
        assert "storage" in checker.checks
    
    def test_register_custom_check(self):
        """Test registering custom health check."""
        checker = HealthChecker()
        
        def custom_check():
            return True
        
        checker.register_check("custom", custom_check)
        
        assert "custom" in checker.checks
        assert checker.checks["custom"] == custom_check
    
    @pytest.mark.asyncio
    async def test_run_checks_all_healthy(self):
        """Test running all health checks when all are healthy."""
        checker = HealthChecker()
        
        # Mock all checks to return True
        for check_name in checker.checks:
            checker.checks[check_name] = AsyncMock(return_value=True)
        
        results = await checker.run_checks()
        
        assert results["status"] == "healthy"
        assert "checks" in results
        assert len(results["checks"]) == len(checker.checks)
        
        for check_name, check_result in results["checks"].items():
            assert check_result["status"] == "healthy"
    
    @pytest.mark.asyncio
    async def test_run_checks_some_unhealthy(self):
        """Test running health checks when some are unhealthy."""
        checker = HealthChecker()
        
        # Mock some checks to return False
        checker.checks["database"] = AsyncMock(return_value=False)
        checker.checks["redis"] = AsyncMock(return_value=True)
        checker.checks["llm_provider"] = AsyncMock(return_value=False)
        
        results = await checker.run_checks()
        
        assert results["status"] == "unhealthy"
        assert "checks" in results
        
        assert results["checks"]["database"]["status"] == "unhealthy"
        assert results["checks"]["redis"]["status"] == "healthy"
        assert results["checks"]["llm_provider"]["status"] == "unhealthy"
    
    @pytest.mark.asyncio
    async def test_run_checks_with_exception(self):
        """Test running health checks when one throws an exception."""
        checker = HealthChecker()
        
        # Mock one check to raise an exception
        checker.checks["database"] = AsyncMock(side_effect=Exception("Database error"))
        checker.checks["redis"] = AsyncMock(return_value=True)
        
        results = await checker.run_checks()
        
        assert results["status"] == "unhealthy"
        assert "checks" in results
        
        assert results["checks"]["database"]["status"] == "error"
        assert "error" in results["checks"]["database"]
        assert results["checks"]["database"]["error"] == "Database error"
        assert results["checks"]["redis"]["status"] == "healthy"
    
    @pytest.mark.asyncio
    async def test_default_checks(self):
        """Test default health check implementations."""
        checker = HealthChecker()
        
        # Test database check
        result = await checker._check_database()
        assert result is True
        
        # Test Redis check
        result = await checker._check_redis()
        assert result is True
        
        # Test LLM provider check
        result = await checker._check_llm_provider()
        assert result is True
        
        # Test MCP server check
        result = await checker._check_mcp_server()
        assert result is True
        
        # Test storage check
        result = await checker._check_storage()
        assert result is True


class TestHealthCheckRoutes:
    """Test cases for health check routes."""
    
    def setup_method(self):
        """Setup test client."""
        self.app = FastAPI()
        setup_health_check_routes(self.app)
        self.client = TestClient(self.app)
    
    def test_health_check_endpoint(self):
        """Test basic health check endpoint."""
        with patch('project_kernel_runtime.observability.health.get_health_checker') as mock_get_checker:
            mock_checker = Mock()
            mock_get_checker.return_value = mock_checker
            
            # Mock healthy results
            mock_checker.run_checks = AsyncMock(return_value={
                "status": "healthy",
                "timestamp": 1234567890,
                "uptime_seconds": 100,
                "checks": {
                    "database": {"status": "healthy", "duration_ms": 10},
                    "redis": {"status": "healthy", "duration_ms": 5}
                }
            })
            
            response = self.client.get("/health")
            
            assert response.status_code == 200
            data = response.json()
            assert data["status"] == "healthy"
            assert "checks" in data
    
    def test_health_check_endpoint_unhealthy(self):
        """Test health check endpoint when service is unhealthy."""
        with patch('project_kernel_runtime.observability.health.get_health_checker') as mock_get_checker:
            mock_checker = Mock()
            mock_get_checker.return_value = mock_checker
            
            # Mock unhealthy results
            mock_checker.run_checks = AsyncMock(return_value={
                "status": "unhealthy",
                "timestamp": 1234567890,
                "uptime_seconds": 100,
                "checks": {
                    "database": {"status": "unhealthy", "duration_ms": 10},
                    "redis": {"status": "healthy", "duration_ms": 5}
                }
            })
            
            response = self.client.get("/health")
            
            assert response.status_code == 503
            data = response.json()
            assert data["status"] == "unhealthy"
    
    def test_readiness_check_endpoint(self):
        """Test readiness check endpoint."""
        with patch('project_kernel_runtime.observability.health.get_health_checker') as mock_get_checker:
            mock_checker = Mock()
            mock_get_checker.return_value = mock_checker
            
            # Mock ready results
            mock_checker.run_checks = AsyncMock(return_value={
                "status": "healthy",
                "timestamp": 1234567890,
                "uptime_seconds": 100,
                "checks": {
                    "database": {"status": "healthy", "duration_ms": 10},
                    "llm_provider": {"status": "healthy", "duration_ms": 15}
                }
            })
            
            response = self.client.get("/health/ready")
            
            assert response.status_code == 200
            data = response.json()
            assert data["status"] == "ready"
            assert "critical_checks" in data
    
    def test_readiness_check_not_ready(self):
        """Test readiness check endpoint when not ready."""
        with patch('project_kernel_runtime.observability.health.get_health_checker') as mock_get_checker:
            mock_checker = Mock()
            mock_get_checker.return_value = mock_checker
            
            # Mock not ready results
            mock_checker.run_checks = AsyncMock(return_value={
                "status": "healthy",
                "timestamp": 1234567890,
                "uptime_seconds": 100,
                "checks": {
                    "database": {"status": "healthy", "duration_ms": 10},
                    "llm_provider": {"status": "unhealthy", "duration_ms": 15}
                }
            })
            
            response = self.client.get("/health/ready")
            
            assert response.status_code == 503
            data = response.json()
            assert data["status"] == "not_ready"
    
    def test_liveness_check_endpoint(self):
        """Test liveness check endpoint."""
        response = self.client.get("/health/live")
        
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "alive"
        assert "uptime_seconds" in data
    
    def test_metrics_check_endpoint(self):
        """Test metrics check endpoint."""
        response = self.client.get("/health/metrics")
        
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"
        assert "metrics" in data


class TestHealthCheckFunctions:
    """Test cases for health check functions."""
    
    def test_get_health_checker(self):
        """Test getting health checker instance."""
        checker1 = get_health_checker()
        checker2 = get_health_checker()
        
        assert checker1 is checker2  # Should return the same instance
    
    def test_register_custom_health_check_function(self):
        """Test registering custom health check function."""
        with patch('project_kernel_runtime.observability.health.get_health_checker') as mock_get_checker:
            mock_checker = Mock()
            mock_get_checker.return_value = mock_checker
            
            def custom_check():
                return True
            
            register_custom_health_check("custom", custom_check)
            
            mock_checker.register_check.assert_called_once_with("custom", custom_check)