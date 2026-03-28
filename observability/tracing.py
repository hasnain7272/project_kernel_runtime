"""
OpenTelemetry tracing implementation for Project Kernel Runtime.
"""

import asyncio
import logging
from typing import Optional
from opentelemetry import trace
from opentelemetry.exporter.otlp.proto.http.trace_exporter import OTLPSpanExporter
from opentelemetry.sdk.resources import Resource
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor, ConsoleSpanExporter
from opentelemetry.trace import SpanKind
from opentelemetry.trace.status import Status, StatusCode

logger = logging.getLogger(__name__)

# Global tracer provider instance
_tracer_provider: Optional[TracerProvider] = None
_tracer: Optional[trace.Tracer] = None


def setup_tracing(
    service_name: str = "project-kernel-runtime",
    endpoint: Optional[str] = None,
    console_export: bool = True
) -> trace.TracerProvider:
    """
    Setup OpenTelemetry tracing with configurable exporters.
    
    Args:
        service_name: Name of this service for resource attributes
        endpoint: OTLP endpoint for remote tracing (e.g., "http://localhost:4318")
        console_export: Whether to export traces to console for development
    
    Returns:
        Configured TracerProvider instance
    """
    global _tracer_provider, _tracer
    
    # Create resource with service name
    resource = Resource(attributes={
        "service.name": service_name,
        "service.version": "1.0.0"
    })
    
    # Create tracer provider
    _tracer_provider = TracerProvider(resource=resource)
    
    # Add console exporter for development
    if console_export:
        console_span_processor = BatchSpanProcessor(
            ConsoleSpanExporter()
        )
        _tracer_provider.add_span_processor(console_span_processor)
    
    # Add OTLP exporter for remote collection if endpoint provided
    if endpoint:
        otlp_exporter = OTLPSpanExporter(endpoint=endpoint)
        otlp_span_processor = BatchSpanProcessor(otlp_exporter)
        _tracer_provider.add_span_processor(otlp_span_processor)
    
    # Set global tracer provider
    trace.set_tracer_provider(_tracer_provider)
    
    # Get tracer instance
    _tracer = trace.get_tracer(service_name)
    
    logger.info(f"OpenTelemetry tracing initialized for service: {service_name}")
    if endpoint:
        logger.info(f"Remote tracing endpoint: {endpoint}")
    
    return _tracer_provider


def get_tracer() -> trace.Tracer:
    """Get the global tracer instance."""
    if _tracer is None:
        raise RuntimeError("Tracing not initialized. Call setup_tracing() first.")
    return _tracer


def trace_orchestrator_call(func):
    """
    Decorator to trace orchestrator method calls.
    
    Args:
        func: Function to trace
    
    Returns:
        Decorated function with tracing
    """
    def wrapper(*args, **kwargs):
        tracer = get_tracer()
        
        # Create span with function name
        with tracer.start_span(
            name=f"orchestrator.{func.__name__}",
            kind=SpanKind.INTERNAL
        ) as span:
            # Add function name as attribute
            span.set_attribute("function.name", func.__name__)
            
            try:
                # Execute the function
                result = func(*args, **kwargs)
                
                # Mark span as successful
                span.set_status(Status(StatusCode.OK))
                
                # Add result type as attribute if available
                if result is not None:
                    span.set_attribute("result.type", type(result).__name__)
                
                return result
                
            except Exception as e:
                # Mark span as failed
                span.set_status(
                    Status(StatusCode.ERROR, description=str(e))
                )
                span.set_attribute("error.type", type(e).__name__)
                span.set_attribute("error.message", str(e))
                
                # Re-raise the exception
                raise
    
    return wrapper


def trace_api_call(func):
    """
    Decorator to trace API endpoint calls.
    
    Args:
        func: Function to trace
    
    Returns:
        Decorated function with tracing
    """
    def wrapper(*args, **kwargs):
        tracer = get_tracer()
        
        # Create span with function name
        with tracer.start_span(
            name=f"api.{func.__name__}",
            kind=SpanKind.SERVER
        ) as span:
            # Add function name as attribute
            span.set_attribute("function.name", func.__name__)
            
            try:
                # Execute the function
                result = func(*args, **kwargs)
                
                # Mark span as successful
                span.set_status(Status(StatusCode.OK))
                
                # Add HTTP status code if available
                if hasattr(result, 'status_code'):
                    span.set_attribute("http.status_code", result.status_code)
                
                return result
                
            except Exception as e:
                # Mark span as failed
                span.set_status(
                    Status(StatusCode.ERROR, description=str(e))
                )
                span.set_attribute("error.type", type(e).__name__)
                span.set_attribute("error.message", str(e))
                
                # Re-raise the exception
                raise
    
    return wrapper


def trace_mcp_interaction(func):
    """
    Decorator to trace MCP client/server interactions.
    
    Args:
        func: Function to trace
    
    Returns:
        Decorated function with tracing
    """
    def wrapper(*args, **kwargs):
        tracer = get_tracer()
        
        # Create span with function name
        with tracer.start_span(
            name=f"mcp.{func.__name__}",
            kind=SpanKind.CLIENT
        ) as span:
            # Add function name as attribute
            span.set_attribute("function.name", func.__name__)
            
            try:
                # Execute the function
                result = func(*args, **kwargs)
                
                # Mark span as successful
                span.set_status(Status(StatusCode.OK))
                
                return result
                
            except Exception as e:
                # Mark span as failed
                span.set_status(
                    Status(StatusCode.ERROR, description=str(e))
                )
                span.set_attribute("error.type", type(e).__name__)
                span.set_attribute("error.message", str(e))
                
                # Re-raise the exception
                raise
    
    return wrapper


async def trace_async_operation(
    operation_name: str,
    async_func,
    *args,
    **kwargs
):
    """
    Trace an async operation with proper context propagation.
    
    Args:
        operation_name: Name for the trace span
        async_func: Async function to execute
        *args: Arguments to pass to the function
        **kwargs: Keyword arguments to pass to the function
    
    Returns:
        Result of the async function
    """
    tracer = get_tracer()
    
    with tracer.start_span(
        name=operation_name,
        kind=SpanKind.INTERNAL
    ) as span:
        try:
            # Execute async function
            result = await async_func(*args, **kwargs)
            
            # Mark span as successful
            span.set_status(Status(StatusCode.OK))
            
            return result
            
        except Exception as e:
            # Mark span as failed
            span.set_status(
                Status(StatusCode.ERROR, description=str(e))
            )
            span.set_attribute("error.type", type(e).__name__)
            span.set_attribute("error.message", str(e))
            
            # Re-raise the exception
            raise