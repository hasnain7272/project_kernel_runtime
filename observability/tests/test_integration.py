"""
Integration tests for observability components.
"""

import pytest
from unittest.mock import Mock, patch, AsyncMock
from fastapi import FastAPI
from fastapi.testclient import TestClient

from project_kernel_runtime.observability import (
    setup_tracing,
    setup_metrics,
    setup_logging,
    setup_middleware,
    setup_health_check_routes
)


class TestObservabilityIntegration:
    """Integration tests for observability components."""
    
    def setup_method(self):
        """Setup test environment."""
        self.app = FastAPI()
        
        # Setup observability components
        setup_logging(level="INFO")
        setup_tracing(service_name="test-service", console_export=True)
        setup_metrics(service_name="test-service", console_export=True)
        setup_middleware(self.app)
        setup_health_check_routes(self.app)
        
        self.client = TestClient(self.app)
    
    @pytest.mark.asyncio
    async def test_full_integration(self):
        """Test full integration of observability components."""
        # Test health check endpoint
        response = self.client.get("/health")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] in ["healthy", "unhealthy"]
    
    def test_middleware_integration(self):
        """Test middleware integration with FastAPI."""
        # Create a test endpoint
        @self.app.get("/test")
        async def test_endpoint():
            return {"message": "test"}
        
        # Test the endpoint
        response = self.client.get("/test")
        assert response.status_code == 200
        assert response.json() == {"message": "test"}
    
    def test_health_check_integration(self):
        """Test health check integration."""
        # Test basic health check
        response = self.client.get("/health")
        assert response.status_code in [200, 503]
        
        # Test readiness check
        response = self.client.get("/health/ready")
        assert response.status_code in [200, 503]
        
        # Test liveness check
        response = self.client.get("/health/live")
        assert response.status_code == 200
        
        # Test metrics check
        response = self.client.get("/health/metrics")
        assert response.status_code == 200
    
    def test_error_handling_integration(self):
        """Test error handling integration."""
        # Create an endpoint that raises an error
        @self.app.get("/error")
        async def error_endpoint():
            raise ValueError("Test error")
        
        # Test the error endpoint
        response = self.client.get("/error")
        assert response.status_code == 500
    
    def test_tracing_integration(self):
        """Test tracing integration."""
        with patch('project_kernel_runtime.observability.middleware.get_tracer') as mock_get_tracer:
            mock_tracer = Mock()
            mock_span = Mock()
            mock_span.get_span_context.return_value = Mock()
            mock_span.get_span_context.return_value.trace_id = "test-trace-id"
            mock_span.get_span_context.return_value.span_id = "test-span-id"
            mock_tracer.start_span.return_value.__enter__.return_value = mock_span
            mock_get_tracer.return_value = mock_tracer
            
            # Create a test endpoint
            @self.app.get("/trace-test")
            async def trace_test():
                return {"message": "trace test"}
            
            # Test the endpoint
            response = self.client.get("/trace-test")
            assert response.status_code == 200
            assert response.json() == {"message": "trace test"}
            
            # Verify tracer was called
            mock_tracer.start_span.assert_called_once()
    
    def test_metrics_integration(self):
        """Test metrics integration."""
        with patch('project_kernel_runtime.observability.middleware.get_request_counter') as mock_counter:
            with patch('project_kernel_runtime.observability.middleware.get_request_duration_histogram') as mock_histogram:
                mock_counter_instance = Mock()
                mock_histogram_instance = Mock()
                mock_counter.return_value = mock_counter_instance
                mock_histogram.return_value = mock_histogram_instance
                
                # Create a test endpoint
                @self.app.get("/metrics-test")
                async def metrics_test():
                    return {"message": "metrics test"}
                
                # Test the endpoint
                response = self.client.get("/metrics-test")
                assert response.status_code == 200
                assert response.json() == {"message": "metrics test"}
                
                # Verify metrics were called
                mock_counter_instance.add.assert_called_once_with(1)
                mock_histogram_instance.record.assert_called_once()
    
    def test_logging_integration(self):
        """Test logging integration."""
        with patch('project_kernel_runtime.observability.middleware.get_logger') as mock_get_logger:
            mock_logger = Mock()
            mock_get_logger.return_value = mock_logger
            
            # Create a test endpoint
            @self.app.get("/log-test")
            async def log_test():
                return {"message": "log test"}
            
            # Test the endpoint
            response = self.client.get("/log-test")
            assert response.status_code == 200
            assert response.json() == {"message": "log test"}
            
            # Verify logging was called
            assert mock_logger.info.call_count >= 1
    
    def test_custom_health_check(self):
        """Test custom health check integration."""
        from project_kernel_runtime.observability.health import register_custom_health_check
        
        # Register a custom health check
        def custom_check():
            return True
        
        register_custom_health_check("custom", custom_check)
        
        # Test that the custom check is included in health check results
        response = self.client.get("/health")
        assert response.status_code == 200
        data = response.json()
        assert "checks" in data
        assert "custom" in data["checks"]


class TestObservabilityConfiguration:
    """Test observability configuration scenarios."""
    
    def test_configuration_with_remote_endpoint(self):
        """Test configuration with remote endpoints."""
        app = FastAPI()
        
        # Setup with remote endpoints
        setup_logging(level="DEBUG")
        setup_tracing(
            service_name="remote-test",
            endpoint="http://localhost:4318",
            console_export=False
        )
        setup_metrics(
            service_name="remote-test",
            endpoint="http://localhost:4318",
            console_export=False
        )
        
        # Should not raise any exceptions
        assert True
    
    def test_configuration_with_different_levels(self):
        """Test configuration with different log levels."""
        app = FastAPI()
        
        # Test different log levels
        for level in ["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]:
            app = FastAPI()
            setup_logging(level=level)
            setup_middleware(app)
            
            # Should not raise any exceptions
            assert True
    
    def test_configuration_with_multiple_services(self):
        """Test configuration with multiple service names."""
        service_names = ["service1", "service2", "service3"]
        
        for service_name in service_names:
            app = FastAPI()
            setup_logging(level="INFO")
            setup_tracing(service_name=service_name, console_export=True)
            setup_metrics(service_name=service_name, console_export=True)
            setup_middleware(app)
            
            # Should not raise any exceptions
            assert True