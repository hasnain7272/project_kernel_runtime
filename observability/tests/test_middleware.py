"""
Tests for middleware components.
"""

import pytest
from unittest.mock import Mock, patch, AsyncMock
from fastapi import Request, Response
from fastapi.testclient import TestClient

from project_kernel_runtime.observability.middleware import (
    ObservabilityMiddleware,
    MetricsMiddleware,
    LoggingMiddleware,
    SecurityMiddleware,
    setup_middleware
)


class TestObservabilityMiddleware:
    """Test cases for observability middleware."""
    
    @pytest.mark.asyncio
    async def test_middleware_success(self):
        """Test middleware with successful request."""
        # Create mock request and response
        mock_request = Mock(spec=Request)
        mock_request.method = "GET"
        mock_request.url = Mock()
        mock_request.url.path = "/test"
        mock_request.headers = {"user-agent": "test-agent"}
        mock_request.client = Mock()
        mock_request.client.host = "127.0.0.1"
        
        mock_response = Mock(spec=Response)
        mock_response.status_code = 200
        
        # Create mock call_next function
        async def mock_call_next(request):
            return mock_response
        
        # Create middleware instance
        middleware = ObservabilityMiddleware()
        
        # Mock tracer
        with patch('project_kernel_runtime.observability.middleware.get_tracer') as mock_get_tracer:
            mock_tracer = Mock()
            mock_span = Mock()
            mock_span.get_span_context.return_value = Mock()
            mock_span.get_span_context.return_value.trace_id = "test-trace-id"
            mock_span.get_span_context.return_value.span_id = "test-span-id"
            mock_tracer.start_span.return_value.__enter__.return_value = mock_span
            mock_get_tracer.return_value = mock_tracer
            
            # Mock logging
            with patch('project_kernel_runtime.observability.middleware.log_api_request') as mock_log_api:
                # Execute middleware
                response = await middleware.dispatch(mock_request, mock_call_next)
                
                # Verify response
                assert response == mock_response
                
                # Verify tracer was called
                mock_tracer.start_span.assert_called_once()
                mock_span.set_attribute.assert_called()
                mock_span.set_status.assert_called_once_with("OK")
                
                # Verify logging was called
                mock_log_api.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_middleware_error(self):
        """Test middleware with failed request."""
        # Create mock request
        mock_request = Mock(spec=Request)
        mock_request.method = "POST"
        mock_request.url = Mock()
        mock_request.url.path = "/test"
        mock_request.headers = {"user-agent": "test-agent"}
        mock_request.client = Mock()
        mock_request.client.host = "127.0.0.1"
        
        # Create mock call_next function that raises an exception
        async def mock_call_next(request):
            raise ValueError("Test error")
        
        # Create middleware instance
        middleware = ObservabilityMiddleware()
        
        # Mock tracer
        with patch('project_kernel_runtime.observability.middleware.get_tracer') as mock_get_tracer:
            mock_tracer = Mock()
            mock_span = Mock()
            mock_span.get_span_context.return_value = Mock()
            mock_span.get_span_context.return_value.trace_id = "test-trace-id"
            mock_span.get_span_context.return_value.span_id = "test-span-id"
            mock_tracer.start_span.return_value.__enter__.return_value = mock_span
            mock_get_tracer.return_value = mock_tracer
            
            # Mock logging
            with patch('project_kernel_runtime.observability.middleware.log_api_request') as mock_log_api:
                # Execute middleware and expect exception
                with pytest.raises(ValueError, match="Test error"):
                    await middleware.dispatch(mock_request, mock_call_next)
                
                # Verify tracer was called
                mock_tracer.start_span.assert_called_once()
                mock_span.set_attribute.assert_called()
                mock_span.set_status.assert_called_once_with("ERROR")
                
                # Verify logging was called
                mock_log_api.assert_called_once()


class TestMetricsMiddleware:
    """Test cases for metrics middleware."""
    
    @pytest.mark.asyncio
    async def test_metrics_middleware_success(self):
        """Test metrics middleware with successful request."""
        # Create mock request and response
        mock_request = Mock(spec=Request)
        mock_response = Mock(spec=Response)
        mock_response.status_code = 200
        
        # Create mock call_next function
        async def mock_call_next(request):
            return mock_response
        
        # Create middleware instance
        middleware = MetricsMiddleware()
        
        # Mock metrics
        with patch('project_kernel_runtime.observability.middleware.get_request_counter') as mock_counter:
            with patch('project_kernel_runtime.observability.middleware.get_request_duration_histogram') as mock_histogram:
                mock_counter_instance = Mock()
                mock_histogram_instance = Mock()
                mock_counter.return_value = mock_counter_instance
                mock_histogram.return_value = mock_histogram_instance
                
                # Execute middleware
                response = await middleware.dispatch(mock_request, mock_call_next)
                
                # Verify response
                assert response == mock_response
                
                # Verify metrics were called
                mock_counter_instance.add.assert_called_once_with(1)
                mock_histogram_instance.record.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_metrics_middleware_error(self):
        """Test metrics middleware with failed request."""
        # Create mock request
        mock_request = Mock(spec=Request)
        
        # Create mock call_next function that raises an exception
        async def mock_call_next(request):
            raise ValueError("Test error")
        
        # Create middleware instance
        middleware = MetricsMiddleware()
        
        # Mock metrics
        with patch('project_kernel_runtime.observability.middleware.get_request_counter') as mock_counter:
            with patch('project_kernel_runtime.observability.middleware.get_request_duration_histogram') as mock_histogram:
                mock_counter_instance = Mock()
                mock_histogram_instance = Mock()
                mock_counter.return_value = mock_counter_instance
                mock_histogram.return_value = mock_histogram_instance
                
                # Execute middleware and expect exception
                with pytest.raises(ValueError, match="Test error"):
                    await middleware.dispatch(mock_request, mock_call_next)
                
                # Verify metrics were called
                mock_counter_instance.add.assert_called_once_with(1)
                mock_histogram_instance.record.assert_called_once()


class TestLoggingMiddleware:
    """Test cases for logging middleware."""
    
    @pytest.mark.asyncio
    async def test_logging_middleware_success(self):
        """Test logging middleware with successful request."""
        # Create mock request and response
        mock_request = Mock(spec=Request)
        mock_request.method = "GET"
        mock_request.url = Mock()
        mock_request.url.path = "/test"
        mock_request.headers = {"user-agent": "test-agent"}
        mock_request.client = Mock()
        mock_request.client.host = "127.0.0.1"
        
        mock_response = Mock(spec=Response)
        mock_response.status_code = 200
        mock_response.headers = {"content-type": "application/json"}
        
        # Create mock call_next function
        async def mock_call_next(request):
            return mock_response
        
        # Create middleware instance
        middleware = LoggingMiddleware()
        
        # Mock logger
        with patch('project_kernel_runtime.observability.middleware.get_logger') as mock_get_logger:
            mock_logger = Mock()
            mock_get_logger.return_value = mock_logger
            
            # Execute middleware
            response = await middleware.dispatch(mock_request, mock_call_next)
            
            # Verify response
            assert response == mock_response
            
            # Verify logging was called
            assert mock_logger.info.call_count == 2  # Request and response
            mock_logger.info.assert_any_call(
                "HTTP request received",
                extra={
                    "method": "GET",
                    "url": "/test",
                    "user_agent": "test-agent",
                    "client_host": "127.0.0.1"
                }
            )
            mock_logger.info.assert_any_call(
                "HTTP request processed",
                extra={
                    "method": "GET",
                    "url": "/test",
                    "status_code": 200,
                    "duration_ms": pytest.approx(0, rel=1.0)
                }
            )
    
    @pytest.mark.asyncio
    async def test_logging_middleware_error(self):
        """Test logging middleware with failed request."""
        # Create mock request
        mock_request = Mock(spec=Request)
        mock_request.method = "POST"
        mock_request.url = Mock()
        mock_request.url.path = "/test"
        mock_request.headers = {"user-agent": "test-agent"}
        mock_request.client = Mock()
        mock_request.client.host = "127.0.0.1"
        
        # Create mock call_next function that raises an exception
        async def mock_call_next(request):
            raise ValueError("Test error")
        
        # Create middleware instance
        middleware = LoggingMiddleware()
        
        # Mock logger
        with patch('project_kernel_runtime.observability.middleware.get_logger') as mock_get_logger:
            mock_logger = Mock()
            mock_get_logger.return_value = mock_logger
            
            # Execute middleware and expect exception
            with pytest.raises(ValueError, match="Test error"):
                await middleware.dispatch(mock_request, mock_call_next)
            
            # Verify logging was called
            assert mock_logger.info.call_count == 1  # Request only
            assert mock_logger.error.call_count == 1  # Error
            mock_logger.info.assert_called_with(
                "HTTP request received",
                extra={
                    "method": "POST",
                    "url": "/test",
                    "user_agent": "test-agent",
                    "client_host": "127.0.0.1"
                }
            )
            mock_logger.error.assert_called_with(
                "HTTP request failed",
                extra={
                    "method": "POST",
                    "url": "/test",
                    "error": "Test error",
                    "duration_ms": pytest.approx(0, rel=1.0)
                }
            )


class TestSecurityMiddleware:
    """Test cases for security middleware."""
    
    @pytest.mark.asyncio
    async def test_security_middleware_success(self):
        """Test security middleware with successful request."""
        # Create mock request and response
        mock_request = Mock(spec=Request)
        mock_request.method = "GET"
        mock_request.url = Mock()
        mock_request.url.path = "/test"
        mock_request.headers = {
            "user-agent": "test-agent",
            "content-type": "application/json",
            "content-length": "100"
        }
        mock_request.client = Mock()
        mock_request.client.host = "127.0.0.1"
        
        mock_response = Mock(spec=Response)
        mock_response.status_code = 200
        mock_response.headers = {"content-type": "application/json"}
        
        # Create mock call_next function
        async def mock_call_next(request):
            return mock_response
        
        # Create middleware instance
        middleware = SecurityMiddleware()
        
        # Mock logger
        with patch('project_kernel_runtime.observability.middleware.get_logger') as mock_get_logger:
            mock_logger = Mock()
            mock_get_logger.return_value = mock_logger
            
            # Execute middleware
            response = await middleware.dispatch(mock_request, mock_call_next)
            
            # Verify response
            assert response == mock_response
            
            # Verify logging was called
            assert mock_logger.info.call_count == 2  # Request and response
            mock_logger.info.assert_any_call(
                "Security check: HTTP request",
                extra={
                    "method": "GET",
                    "url": "/test",
                    "user_agent": "test-agent",
                    "client_host": "127.0.0.1",
                    "content_type": "application/json",
                    "content_length": "100"
                }
            )
            mock_logger.info.assert_any_call(
                "Security check: HTTP response",
                extra={
                    "method": "GET",
                    "url": "/test",
                    "status_code": 200,
                    "duration_ms": pytest.approx(0, rel=1.0),
                    "content_type": "application/json"
                }
            )


class TestMiddlewareSetup:
    """Test cases for middleware setup."""
    
    def test_setup_middleware(self):
        """Test middleware setup function."""
        app = Mock()
        
        with patch('project_kernel_runtime.observability.middleware.ObservabilityMiddleware') as mock_middleware:
            setup_middleware(app)
            
            # Verify middleware was added to app
            app.add_middleware.assert_called_once_with(mock_middleware)