"""
OpenTelemetry metrics implementation for Project Kernel Runtime.
"""

import logging
import time
from typing import Optional
from opentelemetry import metrics
from opentelemetry.exporter.otlp.proto.http.metrics_exporter import OTLPMetricExporter
from opentelemetry.sdk.metrics import MeterProvider
from opentelemetry.sdk.metrics.export import PeriodicExportingMetricReader, ConsoleMetricExporter
from opentelemetry.metrics import Counter, Histogram, UpDownCounter

logger = logging.getLogger(__name__)

# Global meter provider instance
_meter_provider: Optional[MeterProvider] = None
_meter: Optional[metrics.Meter] = None


def setup_metrics(
    service_name: str = "project-kernel-runtime",
    endpoint: Optional[str] = None,
    console_export: bool = True
) -> MeterProvider:
    """
    Setup OpenTelemetry metrics with configurable exporters.
    
    Args:
        service_name: Name of this service for resource attributes
        endpoint: OTLP endpoint for remote metrics (e.g., "http://localhost:4318")
        console_export: Whether to export metrics to console for development
    
    Returns:
        Configured MeterProvider instance
    """
    global _meter_provider, _meter
    
    # Create metric readers
    metric_readers = []
    
    # Add console exporter for development
    if console_export:
        console_reader = PeriodicExportingMetricReader(
            ConsoleMetricExporter()
        )
        metric_readers.append(console_reader)
    
    # Add OTLP exporter for remote collection if endpoint provided
    if endpoint:
        otlp_exporter = OTLPMetricExporter(endpoint=endpoint)
        otlp_reader = PeriodicExportingMetricReader(otlp_exporter)
        metric_readers.append(otlp_reader)
    
    # Create meter provider
    _meter_provider = MeterProvider(metric_readers=metric_readers)
    
    # Set global meter provider
    metrics.set_meter_provider(_meter_provider)
    
    # Get meter instance
    _meter = metrics.get_meter(service_name)
    
    logger.info(f"OpenTelemetry metrics initialized for service: {service_name}")
    if endpoint:
        logger.info(f"Remote metrics endpoint: {endpoint}")
    
    return _meter_provider


def get_meter() -> metrics.Meter:
    """Get the global meter instance."""
    if _meter is None:
        raise RuntimeError("Metrics not initialized. Call setup_metrics() first.")
    return _meter


def get_counter(name: str, description: str = "") -> Counter:
    """Get or create a counter metric."""
    meter = get_meter()
    return meter.create_counter(name, description=description)


def get_histogram(name: str, description: str = "") -> Histogram:
    """Get or create a histogram metric."""
    meter = get_meter()
    return meter.create_histogram(name, description=description)


def get_up_down_counter(name: str, description: str = "") -> UpDownCounter:
    """Get or create an up-down counter metric."""
    meter = get_meter()
    return meter.create_up_down_counter(name, description=description)


# Pre-defined metrics for common operations
def get_request_counter() -> Counter:
    """Counter for HTTP requests."""
    return get_counter(
        "http.requests.total",
        "Total number of HTTP requests"
    )


def get_request_duration_histogram() -> Histogram:
    """Histogram for HTTP request duration."""
    return get_histogram(
        "http.request.duration",
        "Duration of HTTP requests in milliseconds"
    )


def get_task_counter() -> Counter:
    """Counter for tasks executed."""
    return get_counter(
        "tasks.total",
        "Total number of tasks executed"
    )


def get_task_duration_histogram() -> Histogram:
    """Histogram for task execution duration."""
    return get_histogram(
        "task.duration",
        "Duration of task execution in milliseconds"
    )


def get_error_counter() -> Counter:
    """Counter for errors encountered."""
    return get_counter(
        "errors.total",
        "Total number of errors encountered"
    )


def get_active_sessions_counter() -> UpDownCounter:
    """Counter for active user sessions."""
    return get_up_down_counter(
        "sessions.active",
        "Current number of active user sessions"
    )


def get_mcp_calls_counter() -> Counter:
    """Counter for MCP calls."""
    return get_counter(
        "mcp.calls.total",
        "Total number of MCP calls"
    )


def get_llm_calls_counter() -> Counter:
    """Counter for LLM provider calls."""
    return get_counter(
        "llm.calls.total",
        "Total number of LLM provider calls"
    )


def track_execution_time(metric_name: str, description: str = ""):
    """
    Decorator to track execution time of a function.
    
    Args:
        metric_name: Name of the histogram metric to use
        description: Description of the metric
    
    Returns:
        Decorated function with timing tracking
    """
    def decorator(func):
        histogram = get_histogram(metric_name, description)
        
        def wrapper(*args, **kwargs):
            start_time = time.time()
            
            try:
                result = func(*args, **kwargs)
                
                # Record successful execution time
                duration = (time.time() - start_time) * 1000  # Convert to milliseconds
                histogram.record(duration)
                
                return result
                
            except Exception as e:
                # Record error execution time
                duration = (time.time() - start_time) * 1000  # Convert to milliseconds
                histogram.record(duration)
                
                # Increment error counter
                get_error_counter().add(1)
                
                # Re-raise the exception
                raise
        
        return wrapper
    return decorator


def track_api_request(func):
    """
    Decorator to track API request metrics.
    
    Args:
        func: Function to track
    
    Returns:
        Decorated function with API request tracking
    """
    request_counter = get_request_counter()
    request_duration = get_request_duration_histogram()
    
    def wrapper(*args, **kwargs):
        start_time = time.time()
        
        try:
            result = func(*args, **kwargs)
            
            # Record successful request
            duration = (time.time() - start_time) * 1000  # Convert to milliseconds
            request_duration.record(duration)
            request_counter.add(1)
            
            return result
            
        except Exception as e:
            # Record failed request
            duration = (time.time() - start_time) * 1000  # Convert to milliseconds
            request_duration.record(duration)
            request_counter.add(1)
            get_error_counter().add(1)
            
            # Re-raise the exception
            raise
    
    return wrapper


def track_task_execution(func):
    """
    Decorator to track task execution metrics.
    
    Args:
        func: Function to track
    
    Returns:
        Decorated function with task execution tracking
    """
    task_counter = get_task_counter()
    task_duration = get_task_duration_histogram()
    
    def wrapper(*args, **kwargs):
        start_time = time.time()
        
        try:
            result = func(*args, **kwargs)
            
            # Record successful task execution
            duration = (time.time() - start_time) * 1000  # Convert to milliseconds
            task_duration.record(duration)
            task_counter.add(1)
            
            return result
            
        except Exception as e:
            # Record failed task execution
            duration = (time.time() - start_time) * 1000  # Convert to milliseconds
            task_duration.record(duration)
            task_counter.add(1)
            get_error_counter().add(1)
            
            # Re-raise the exception
            raise
    
    return wrapper