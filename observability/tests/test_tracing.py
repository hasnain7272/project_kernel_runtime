"""
Tests for tracing components.
"""

import pytest
from unittest.mock import Mock, patch
from opentelemetry import trace
from opentelemetry.sdk.trace import TracerProvider

from project_kernel_runtime.observability.tracing import (
    setup_tracing,
    get_tracer,
    trace_orchestrator_call,
    trace_api_call,
    trace_mcp_interaction,
    trace_async_operation
)


class TestTracing:
    """Test cases for tracing functionality."""
    
    def test_setup_tracing_with_console_export(self):
        """Test tracing setup with console export."""
        with patch('project_kernel_runtime.observability.tracing.trace.set_tracer_provider') as mock_set_provider:
            with patch('project_kernel_runtime.observability.tracing.trace.get_tracer') as mock_get_tracer:
                provider = setup_tracing(
                    service_name="test-service",
                    console_export=True
                )
                
                assert provider is not None
                mock_set_provider.assert_called_once()
                mock_get_tracer.assert_called_once_with("test-service")
    
    def test_setup_tracing_with_remote_endpoint(self):
        """Test tracing setup with remote endpoint."""
        with patch('project_kernel_runtime.observability.tracing.trace.set_tracer_provider') as mock_set_provider:
            with patch('project_kernel_runtime.observability.tracing.trace.get_tracer') as mock_get_tracer:
                provider = setup_tracing(
                    service_name="test-service",
                    endpoint="http://localhost:4318"
                )
                
                assert provider is not None
                mock_set_provider.assert_called_once()
                mock_get_tracer.assert_called_once_with("test-service")
    
    def test_get_tracer_not_initialized(self):
        """Test getting tracer when not initialized."""
        with patch('project_kernel_runtime.observability.tracing._tracer', None):
            with pytest.raises(RuntimeError, match="Tracing not initialized"):
                get_tracer()
    
    def test_trace_orchestrator_call_success(self):
        """Test tracing decorator for successful orchestrator call."""
        mock_tracer = Mock()
        mock_span = Mock()
        mock_tracer.start_span.return_value.__enter__.return_value = mock_span
        
        with patch('project_kernel_runtime.observability.tracing.get_tracer', return_value=mock_tracer):
            
            @trace_orchestrator_call
            def test_function():
                return "success"
            
            result = test_function()
            
            assert result == "success"
            mock_tracer.start_span.assert_called_once()
            mock_span.set_status.assert_called_once()
    
    def test_trace_orchestrator_call_failure(self):
        """Test tracing decorator for failed orchestrator call."""
        mock_tracer = Mock()
        mock_span = Mock()
        mock_tracer.start_span.return_value.__enter__.return_value = mock_span
        
        with patch('project_kernel_runtime.observability.tracing.get_tracer', return_value=mock_tracer):
            
            @trace_orchestrator_call
            def test_function():
                raise ValueError("test error")
            
            with pytest.raises(ValueError, match="test error"):
                test_function()
            
            mock_tracer.start_span.assert_called_once()
            mock_span.set_status.assert_called_once()
    
    def test_trace_api_call_success(self):
        """Test tracing decorator for successful API call."""
        mock_tracer = Mock()
        mock_span = Mock()
        mock_tracer.start_span.return_value.__enter__.return_value = mock_span
        
        with patch('project_kernel_runtime.observability.tracing.get_tracer', return_value=mock_tracer):
            
            @trace_api_call
            def test_function():
                class MockResponse:
                    status_code = 200
                return MockResponse()
            
            result = test_function()
            
            assert result.status_code == 200
            mock_tracer.start_span.assert_called_once()
            mock_span.set_status.assert_called_once()
    
    def test_trace_mcp_interaction_success(self):
        """Test tracing decorator for successful MCP interaction."""
        mock_tracer = Mock()
        mock_span = Mock()
        mock_tracer.start_span.return_value.__enter__.return_value = mock_span
        
        with patch('project_kernel_runtime.observability.tracing.get_tracer', return_value=mock_tracer):
            
            @trace_mcp_interaction
            def test_function():
                return "mcp_success"
            
            result = test_function()
            
            assert result == "mcp_success"
            mock_tracer.start_span.assert_called_once()
            mock_span.set_status.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_trace_async_operation_success(self):
        """Test tracing for successful async operation."""
        mock_tracer = Mock()
        mock_span = Mock()
        mock_tracer.start_span.return_value.__enter__.return_value = mock_span
        
        with patch('project_kernel_runtime.observability.tracing.get_tracer', return_value=mock_tracer):
            
            async def test_async_function():
                return "async_success"
            
            result = await trace_async_operation(
                "test-operation",
                test_async_function
            )
            
            assert result == "async_success"
            mock_tracer.start_span.assert_called_once()
            mock_span.set_status.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_trace_async_operation_failure(self):
        """Test tracing for failed async operation."""
        mock_tracer = Mock()
        mock_span = Mock()
        mock_tracer.start_span.return_value.__enter__.return_value = mock_span
        
        with patch('project_kernel_runtime.observability.tracing.get_tracer', return_value=mock_tracer):
            
            async def test_async_function():
                raise ValueError("async error")
            
            with pytest.raises(ValueError, match="async error"):
                await trace_async_operation(
                    "test-operation",
                    test_async_function
                )
            
            mock_tracer.start_span.assert_called_once()
            mock_span.set_status.assert_called_once()