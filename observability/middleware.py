"""
Middleware for observability integration in Project Kernel Runtime.
"""

import time
from typing import Callable, Optional
from fastapi import Request, Response
from fastapi.middleware.base import BaseHTTPMiddleware
from opentelemetry import trace
from opentelemetry.propagate import extract

from .tracing import get_tracer
from .metrics import get_request_counter, get_request_duration_histogram
from .logging import get_logger, log_api_request

logger = get_logger("middleware")


class ObservabilityMiddleware(BaseHTTPMiddleware):
    """Middleware to add observability to HTTP requests."""
    
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """Process request with observability tracking."""
        start_time = time.time()
        
        # Get tracer
        tracer = get_tracer()
        
        # Extract trace context from request headers
        carrier = {k: v for k, v in request.headers.items() if k.startswith('traceparent-')}
        context = extract(carrier)
        
        # Start span for the request
        with tracer.start_span(
            name=f"HTTP {request.method}",
            kind="SERVER",
            context=context
        ) as span:
            # Add request attributes to span
            span.set_attribute("http.method", request.method)
            span.set_attribute("http.url", str(request.url))
            span.set_attribute("http.host", request.client.host if request.client else "unknown")
            span.set_attribute("http.user_agent", request.headers.get("user-agent", "unknown"))
            
            # Add trace context to request state for later use
            request.state.trace_id = span.get_span_context().trace_id
            request.state.span_id = span.get_span_context().span_id
            
            try:
                # Process the request
                response = await call_next(request)
                
                # Record response attributes
                span.set_attribute("http.status_code", response.status_code)
                
                # Mark span as successful for 2xx and 3xx status codes
                if 200 <= response.status_code < 400:
                    span.set_status("OK")
                else:
                    span.set_status("ERROR")
                
                # Log the request
                duration = (time.time() - start_time) * 1000  # Convert to milliseconds
                log_api_request(
                    method=request.method,
                    path=str(request.url.path),
                    status_code=response.status_code,
                    duration_ms=duration,
                    trace_id=str(span.get_span_context().trace_id) if span.get_span_context().trace_id else None
                )
                
                # Record metrics
                request_counter = get_request_counter()
                request_duration = get_request_duration_histogram()
                
                request_counter.add(1)
                request_duration.record(duration)
                
                return response
                
            except Exception as e:
                # Mark span as failed
                span.set_status("ERROR")
                span.set_attribute("error.type", type(e).__name__)
                span.set_attribute("error.message", str(e))
                
                # Log the error
                duration = (time.time() - start_time) * 1000  # Convert to milliseconds
                log_api_request(
                    method=request.method,
                    path=str(request.url.path),
                    status_code=500,
                    duration_ms=duration,
                    trace_id=str(span.get_span_context().trace_id) if span.get_span_context().trace_id else None
                )
                
                # Record metrics
                request_counter = get_request_counter()
                request_duration = get_request_duration_histogram()
                
                request_counter.add(1)
                request_duration.record(duration)
                
                # Re-raise the exception
                raise


class MetricsMiddleware(BaseHTTPMiddleware):
    """Middleware to collect metrics for HTTP requests."""
    
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """Process request with metrics collection."""
        start_time = time.time()
        
        try:
            # Process the request
            response = await call_next(request)
            
            # Calculate duration
            duration = (time.time() - start_time) * 1000  # Convert to milliseconds
            
            # Record metrics
            request_counter = get_request_counter()
            request_duration = get_request_duration_histogram()
            
            request_counter.add(1)
            request_duration.record(duration)
            
            return response
            
        except Exception as e:
            # Calculate duration
            duration = (time.time() - start_time) * 1000  # Convert to milliseconds
            
            # Record metrics
            request_counter = get_request_counter()
            request_duration = get_request_duration_histogram()
            
            request_counter.add(1)
            request_duration.record(duration)
            
            # Re-raise the exception
            raise


class LoggingMiddleware(BaseHTTPMiddleware):
    """Middleware to add logging to HTTP requests."""
    
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """Process request with logging."""
        start_time = time.time()
        
        try:
            # Log request
            logger.info(
                "HTTP request received",
                extra={
                    "method": request.method,
                    "url": str(request.url),
                    "user_agent": request.headers.get("user-agent", "unknown"),
                    "client_host": request.client.host if request.client else "unknown"
                }
            )
            
            # Process the request
            response = await call_next(request)
            
            # Calculate duration
            duration = (time.time() - start_time) * 1000  # Convert to milliseconds
            
            # Log response
            logger.info(
                "HTTP request processed",
                extra={
                    "method": request.method,
                    "url": str(request.url),
                    "status_code": response.status_code,
                    "duration_ms": duration
                }
            )
            
            return response
            
        except Exception as e:
            # Calculate duration
            duration = (time.time() - start_time) * 1000  # Convert to milliseconds
            
            # Log error
            logger.error(
                "HTTP request failed",
                extra={
                    "method": request.method,
                    "url": str(request.url),
                    "error": str(e),
                    "duration_ms": duration
                }
            )
            
            # Re-raise the exception
            raise


class SecurityMiddleware(BaseHTTPMiddleware):
    """Middleware to add security logging to HTTP requests."""
    
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """Process request with security logging."""
        start_time = time.time()
        
        try:
            # Log security-relevant request details
            logger.info(
                "Security check: HTTP request",
                extra={
                    "method": request.method,
                    "url": str(request.url),
                    "user_agent": request.headers.get("user-agent", "unknown"),
                    "client_host": request.client.host if request.client else "unknown",
                    "content_type": request.headers.get("content-type", "unknown"),
                    "content_length": request.headers.get("content-length", "unknown")
                }
            )
            
            # Process the request
            response = await call_next(request)
            
            # Calculate duration
            duration = (time.time() - start_time) * 1000  # Convert to milliseconds
            
            # Log security-relevant response details
            logger.info(
                "Security check: HTTP response",
                extra={
                    "method": request.method,
                    "url": str(request.url),
                    "status_code": response.status_code,
                    "duration_ms": duration,
                    "content_type": response.headers.get("content-type", "unknown")
                }
            )
            
            return response
            
        except Exception as e:
            # Calculate duration
            duration = (time.time() - start_time) * 1000  # Convert to milliseconds
            
            # Log security error
            logger.error(
                "Security check: HTTP request failed",
                extra={
                    "method": request.method,
                    "url": str(request.url),
                    "error": str(e),
                    "duration_ms": duration
                }
            )
            
            # Re-raise the exception
            raise


def setup_middleware(app):
    """Setup all middleware for the FastAPI application."""
    
    # Add observability middleware (includes tracing, metrics, and logging)
    app.add_middleware(ObservabilityMiddleware)
    
    # Add additional middleware if needed
    # app.add_middleware(MetricsMiddleware)
    # app.add_middleware(LoggingMiddleware)
    # app.add_middleware(SecurityMiddleware)
    
    logger.info("Observability middleware setup complete")