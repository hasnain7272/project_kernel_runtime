"""
Tests for metrics components.
"""

import pytest
from unittest.mock import Mock, patch
from opentelemetry import metrics
from opentelemetry.sdk.metrics import MeterProvider

from project_kernel_runtime.observability.metrics import (
    setup_metrics,
    get_meter,
    get_counter,
    get_histogram,
    get_up_down_counter,
    track_execution_time,
    track_api_request,
    track_task_execution
)


class TestMetrics:
    """Test cases for metrics functionality."""
    
    def test_setup_metrics_with_console_export(self):
        """Test metrics setup with console export."""
        with patch('project_kernel_runtime.observability.metrics.metrics.set_meter_provider') as mock_set_provider:
            with patch('project_kernel_runtime.observability.metrics.metrics.get_meter') as mock_get_meter:
                provider = setup_metrics(
                    service_name="test-service",
                    console_export=True
                )
                
                assert provider is not None
                mock_set_provider.assert_called_once()
                mock_get_meter.assert_called_once_with("test-service")
    
    def test_setup_metrics_with_remote_endpoint(self):
        """Test metrics setup with remote endpoint."""
        with patch('project_kernel_runtime.observability.metrics.metrics.set_meter_provider') as mock_set_provider:
            with patch('project_kernel_runtime.observability.metrics.metrics.get_meter') as mock_get_meter:
                provider = setup_metrics(
                    service_name="test-service",
                    endpoint="http://localhost:4318"
                )
                
                assert provider is not None
                mock_set_provider.assert_called_once()
                mock_get_meter.assert_called_once_with("test-service")
    
    def test_get_meter_not_initialized(self):
        """Test getting meter when not initialized."""
        with patch('project_kernel_runtime.observability.metrics._meter', None):
            with pytest.raises(RuntimeError, match="Metrics not initialized"):
                get_meter()
    
    def test_get_counter(self):
        """Test getting a counter metric."""
        mock_meter = Mock()
        mock_counter = Mock()
        mock_meter.create_counter.return_value = mock_counter
        
        with patch('project_kernel_runtime.observability.metrics.get_meter', return_value=mock_meter):
            counter = get_counter("test-counter", "Test counter")
            
            assert counter == mock_counter
            mock_meter.create_counter.assert_called_once_with("test-counter", description="Test counter")
    
    def test_get_histogram(self):
        """Test getting a histogram metric."""
        mock_meter = Mock()
        mock_histogram = Mock()
        mock_meter.create_histogram.return_value = mock_histogram
        
        with patch('project_kernel_runtime.observability.metrics.get_meter', return_value=mock_meter):
            histogram = get_histogram("test-histogram", "Test histogram")
            
            assert histogram == mock_histogram
            mock_meter.create_histogram.assert_called_once_with("test-histogram", description="Test histogram")
    
    def test_get_up_down_counter(self):
        """Test getting an up-down counter metric."""
        mock_meter = Mock()
        mock_counter = Mock()
        mock_meter.create_up_down_counter.return_value = mock_counter
        
        with patch('project_kernel_runtime.observability.metrics.get_meter', return_value=mock_meter):
            counter = get_up_down_counter("test-counter", "Test up-down counter")
            
            assert counter == mock_counter
            mock_meter.create_up_down_counter.assert_called_once_with("test-counter", description="Test up-down counter")
    
    def test_track_execution_time_success(self):
        """Test execution time tracking decorator for successful function."""
        mock_histogram = Mock()
        
        with patch('project_kernel_runtime.observability.metrics.get_histogram', return_value=mock_histogram):
            
            @track_execution_time("test-metric", "Test metric")
            def test_function():
                return "success"
            
            result = test_function()
            
            assert result == "success"
            mock_histogram.record.assert_called_once()
    
    def test_track_execution_time_failure(self):
        """Test execution time tracking decorator for failed function."""
        mock_histogram = Mock()
        mock_error_counter = Mock()
        
        with patch('project_kernel_runtime.observability.metrics.get_histogram', return_value=mock_histogram):
            with patch('project_kernel_runtime.observability.metrics.get_error_counter', return_value=mock_error_counter):
                
                @track_execution_time("test-metric", "Test metric")
                def test_function():
                    raise ValueError("test error")
                
                with pytest.raises(ValueError, match="test error"):
                    test_function()
                
                mock_histogram.record.assert_called_once()
                mock_error_counter.add.assert_called_once_with(1)
    
    def test_track_api_request_success(self):
        """Test API request tracking decorator for successful request."""
        mock_request_counter = Mock()
        mock_request_duration = Mock()
        
        with patch('project_kernel_runtime.observability.metrics.get_request_counter', return_value=mock_request_counter):
            with patch('project_kernel_runtime.observability.metrics.get_request_duration_histogram', return_value=mock_request_duration):
                
                @track_api_request
                def test_function():
                    class MockResponse:
                        status_code = 200
                    return MockResponse()
                
                result = test_function()
                
                assert result.status_code == 200
                mock_request_counter.add.assert_called_once_with(1)
                mock_request_duration.record.assert_called_once()
    
    def test_track_api_request_failure(self):
        """Test API request tracking decorator for failed request."""
        mock_request_counter = Mock()
        mock_request_duration = Mock()
        mock_error_counter = Mock()
        
        with patch('project_kernel_runtime.observability.metrics.get_request_counter', return_value=mock_request_counter):
            with patch('project_kernel_runtime.observability.metrics.get_request_duration_histogram', return_value=mock_request_duration):
                with patch('project_kernel_runtime.observability.metrics.get_error_counter', return_value=mock_error_counter):
                    
                    @track_api_request
                    def test_function():
                        raise ValueError("test error")
                    
                    with pytest.raises(ValueError, match="test error"):
                        test_function()
                    
                    mock_request_counter.add.assert_called_once_with(1)
                    mock_request_duration.record.assert_called_once()
                    mock_error_counter.add.assert_called_once_with(1)
    
    def test_track_task_execution_success(self):
        """Test task execution tracking decorator for successful task."""
        mock_task_counter = Mock()
        mock_task_duration = Mock()
        
        with patch('project_kernel_runtime.observability.metrics.get_task_counter', return_value=mock_task_counter):
            with patch('project_kernel_runtime.observability.metrics.get_task_duration_histogram', return_value=mock_task_duration):
                
                @track_task_execution
                def test_function():
                    return "task_success"
                
                result = test_function()
                
                assert result == "task_success"
                mock_task_counter.add.assert_called_once_with(1)
                mock_task_duration.record.assert_called_once()
    
    def test_track_task_execution_failure(self):
        """Test task execution tracking decorator for failed task."""
        mock_task_counter = Mock()
        mock_task_duration = Mock()
        mock_error_counter = Mock()
        
        with patch('project_kernel_runtime.observability.metrics.get_task_counter', return_value=mock_task_counter):
            with patch('project_kernel_runtime.observability.metrics.get_task_duration_histogram', return_value=mock_task_duration):
                with patch('project_kernel_runtime.observability.metrics.get_error_counter', return_value=mock_error_counter):
                    
                    @track_task_execution
                    def test_function():
                        raise ValueError("task error")
                    
                    with pytest.raises(ValueError, match="task error"):
                        test_function()
                    
                    mock_task_counter.add.assert_called_once_with(1)
                    mock_task_duration.record.assert_called_once()
                    mock_error_counter.add.assert_called_once_with(1)