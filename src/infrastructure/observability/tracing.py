"""
Production-Grade Distributed Tracing with OpenTelemetry

Provides automatic instrumentation for:
- HTTP requests (FastAPI)
- Database queries (SQLAlchemy)
- Message queue operations
- Tool executions
- LLM API calls
"""
import asyncio
import functools
import logging
import os
from contextlib import contextmanager
from typing import Any, Callable, Dict, Optional, TypeVar

from opentelemetry import trace
from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import OTLPSpanExporter
from opentelemetry.sdk.resources import Resource, SERVICE_NAME, SERVICE_VERSION, DEPLOYMENT_ENVIRONMENT
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor, ConsoleSpanExporter
from opentelemetry.propagate import extract, inject
from opentelemetry.trace import SpanKind, Status, StatusCode

# Optional instrumentations - gracefully handle if not installed
try:
    from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor
    FASTAPI_INST_AVAILABLE = True
except ImportError:
    FASTAPI_INST_AVAILABLE = False

try:
    from opentelemetry.instrumentation.sqlalchemy import SQLAlchemyInstrumentor
    SQLALCHEMY_INST_AVAILABLE = True
except ImportError:
    SQLALCHEMY_INST_AVAILABLE = False

try:
    from opentelemetry.instrumentation.redis import RedisInstrumentor
    REDIS_INST_AVAILABLE = True
except ImportError:
    REDIS_INST_AVAILABLE = False

logger = logging.getLogger(__name__)

# Service identity
SERVICE_NAME_VALUE = os.environ.get("OTEL_SERVICE_NAME", "antigravity-runtime")
SERVICE_VERSION_VALUE = os.environ.get("OTEL_SERVICE_VERSION", "3.0.0")
ENVIRONMENT = os.environ.get("DEPLOYMENT_ENVIRONMENT", "development")
OTEL_ENDPOINT = os.environ.get("OTEL_EXPORTER_OTLP_ENDPOINT", "")

# Initialize tracer provider
_resource = Resource.create({
    SERVICE_NAME: SERVICE_NAME_VALUE,
    SERVICE_VERSION: SERVICE_VERSION_VALUE,
    DEPLOYMENT_ENVIRONMENT: ENVIRONMENT,
    "service.instance.id": os.environ.get("HOSTNAME", "local"),
})

tracer_provider = TracerProvider(resource=_resource)
trace.set_tracer_provider(tracer_provider)

# Configure exporters
if OTEL_ENDPOINT:
    # Production: send to collector (Jaeger, Tempo, etc.)
    otlp_exporter = OTLPSpanExporter(endpoint=OTEL_ENDPOINT)
    span_processor = BatchSpanProcessor(
        otlp_exporter,
        max_queue_size=2048,
        max_export_batch_size=512,
        schedule_delay_millis=5000,
    )
    tracer_provider.add_span_processor(span_processor)
    logger.info(f"[Tracing] OTLP exporter configured: {OTEL_ENDPOINT}")

# Discrete Console Logging: 
# Instead of dumping JSON Spans, we use standard logging for milestones.
# This keeps the terminal "agentic" and clean.
class DiscreteEventLogger:
    @staticmethod
    def milestone(event: str, attributes: Optional[Dict] = None):
        attr_str = f" | {attributes}" if attributes else ""
        logger.info(f"✨ [Milestone] {event}{attr_str}")

milestones = DiscreteEventLogger()
logger.info("[Tracing] Discrete hyper-observability active (Milestones only)")

# Get tracer
tracer = trace.get_tracer(__name__)


class TraceContext:
    """Context manager for manual span creation."""
    
    def __init__(
        self,
        operation: str,
        kind: SpanKind = SpanKind.INTERNAL,
        attributes: Optional[Dict[str, Any]] = None,
        parent: Optional[trace.Span] = None
    ):
        self.operation = operation
        self.kind = kind
        self.attributes = attributes or {}
        self.parent = parent
        self.span: Optional[trace.Span] = None
        
    async def __aenter__(self):
        ctx = trace.set_span_in_context(self.parent) if self.parent else None
        self.span = tracer.start_span(
            self.operation,
            kind=self.kind,
            context=ctx,
            attributes=self.attributes
        )
        return self.span
        
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if self.span:
            if exc_val:
                self.span.set_status(
                    Status(StatusCode.ERROR, description=str(exc_val))
                )
                self.span.record_exception(exc_val)
            else:
                self.span.set_status(Status(StatusCode.OK))
            self.span.end()


def traced(
    operation: Optional[str] = None,
    kind: SpanKind = SpanKind.INTERNAL,
    attributes: Optional[Dict[str, Any]] = None
):
    """Decorator for tracing async functions."""
    def decorator(func: Callable) -> Callable:
        span_name = operation or func.__qualname__
        
        @functools.wraps(func)
        async def async_wrapper(*args, **kwargs):
            with tracer.start_as_current_span(
                span_name,
                kind=kind,
                attributes=attributes
            ) as span:
                try:
                    # Add function parameters as attributes (sanitized)
                    span.set_attribute("function.args_count", len(args))
                    span.set_attribute("function.kwargs_count", len(kwargs))
                    
                    result = await func(*args, **kwargs)
                    
                    # Add result metadata
                    if isinstance(result, dict):
                        span.set_attribute("result.has_error", "error" in result)
                    
                    return result
                    
                except Exception as e:
                    span.set_status(Status(StatusCode.ERROR, description=str(e)))
                    span.record_exception(e)
                    raise
        
        @functools.wraps(func)
        def sync_wrapper(*args, **kwargs):
            with tracer.start_as_current_span(
                span_name,
                kind=kind,
                attributes=attributes
            ) as span:
                try:
                    result = func(*args, **kwargs)
                    return result
                except Exception as e:
                    span.set_status(Status(StatusCode.ERROR, description=str(e)))
                    span.record_exception(e)
                    raise
        
        return async_wrapper if asyncio.iscoroutinefunction(func) else sync_wrapper
    return decorator


def instrument_fastapi(app):
    """Instrument FastAPI application."""
    if FASTAPI_INST_AVAILABLE:
        FastAPIInstrumentor.instrument_app(
            app,
            excluded_urls="/health,/metrics",  # Don't trace health checks
        )
        logger.info("[Tracing] FastAPI instrumented")
    else:
        logger.debug("[Tracing] FastAPI instrumentation not available")


def instrument_sqlalchemy(engine):
    """Instrument SQLAlchemy engine."""
    if SQLALCHEMY_INST_AVAILABLE:
        SQLAlchemyInstrumentor().instrument(
            engine=engine,
            enable_commenter=True,
            commenter_options={},
        )
        logger.info("[Tracing] SQLAlchemy instrumented")
    else:
        logger.debug("[Tracing] SQLAlchemy instrumentation not available")


def instrument_redis():
    """Instrument Redis client."""
    if REDIS_INST_AVAILABLE:
        RedisInstrumentor().instrument()
        logger.info("[Tracing] Redis instrumented")
    else:
        logger.debug("[Tracing] Redis instrumentation not available")


class TracedMessageProcessor:
    """
    Wrapper for message processors that adds tracing.
    
    Injects trace context into messages and extracts it on consumption.
    """
    
    @staticmethod
    def inject_trace_context(message: Dict[str, Any]) -> Dict[str, Any]:
        """Inject current trace context into message."""
        carrier = {}
        inject(carrier)
        message["trace_context"] = carrier
        return message
    
    @staticmethod
    def extract_trace_context(message: Dict[str, Any]) -> Optional[trace.SpanContext]:
        """Extract trace context from message."""
        if "trace_context" in message:
            return extract(message["trace_context"])
        return None


def create_task_span(
    task_id: str,
    session_id: str,
    operation: str,
    parent_context: Optional[trace.SpanContext] = None
) -> trace.Span:
    """Create a span for a task operation."""
    
    ctx = trace.set_span_in_context(
        trace.NonRecordingSpan(parent_context)
    ) if parent_context else None
    
    span = tracer.start_span(
        operation,
        context=ctx,
        kind=SpanKind.SERVER,
        attributes={
            "task.id": task_id,
            "session.id": session_id,
            "service.name": SERVICE_NAME_VALUE,
        }
    )
    
    return span


class MetricsCollector:
    """
    Simple metrics collector that works with spans.
    
    In production, this would integrate with Prometheus.
    """
    
    def __init__(self):
        self._counters: Dict[str, int] = {}
        self._gauges: Dict[str, float] = {}
        self._histograms: Dict[str, list] = {}
    
    def increment(self, name: str, value: int = 1, labels: Optional[Dict] = None):
        """Increment a counter."""
        key = f"{name}:{labels}" if labels else name
        self._counters[key] = self._counters.get(key, 0) + value
        
        # Also record in current span
        current_span = trace.get_current_span()
        if current_span:
            current_span.set_attribute(f"metric.{name}", self._counters[key])
    
    def gauge(self, name: str, value: float, labels: Optional[Dict] = None):
        """Set a gauge value."""
        key = f"{name}:{labels}" if labels else name
        self._gauges[key] = value
        
        current_span = trace.get_current_span()
        if current_span:
            current_span.set_attribute(f"metric.{name}", value)
    
    def histogram(self, name: str, value: float, labels: Optional[Dict] = None):
        """Record a histogram value."""
        key = f"{name}:{labels}" if labels else name
        if key not in self._histograms:
            self._histograms[key] = []
        self._histograms[key].append(value)
        
        current_span = trace.get_current_span()
        if current_span:
            current_span.set_attribute(f"metric.{name}", value)


# Global metrics instance
metrics = MetricsCollector()