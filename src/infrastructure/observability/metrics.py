"""Production metrics collection."""
import logging
import time
from functools import wraps
from typing import Any, Callable, Optional

from prometheus_client import Counter, Histogram, Gauge, Info

logger = logging.getLogger(__name__)

# Define metrics
APP_INFO = Info("antigravity_app", "Application information")
REQUEST_COUNT = Counter(
    "antigravity_http_requests_total",
    "Total HTTP requests",
    ["method", "endpoint", "status"]
)
REQUEST_DURATION = Histogram(
    "antigravity_http_request_duration_seconds",
    "HTTP request duration",
    ["method", "endpoint"],
    buckets=[.005, .01, .025, .05, .075, .1, .25, .5, .75, 1.0, 2.5, 5.0, 7.5, 10.0]
)
ACTIVE_SESSIONS = Gauge(
    "antigravity_active_sessions",
    "Number of active sessions"
)
TASK_QUEUE_DEPTH = Gauge(
    "antigravity_task_queue_depth",
    "Current task queue depth",
    ["queue_name"]
)
LLM_REQUESTS = Counter(
    "antigravity_llm_requests_total",
    "Total LLM requests",
    ["model", "status"]
)
LLM_LATENCY = Histogram(
    "antigravity_llm_latency_seconds",
    "LLM request latency",
    ["model"],
    buckets=[.1, .25, .5, 1, 2.5, 5, 10, 30, 60]
)
TOOL_EXECUTIONS = Counter(
    "antigravity_tool_executions_total",
    "Total tool executions",
    ["tool_name", "status"]
)
SANDBOX_EXECUTIONS = Counter(
    "antigravity_sandbox_executions_total",
    "Total sandbox executions",
    ["sandbox_type", "status"]
)


def init_metrics(app_version: str):
    """Initialize metrics."""
    APP_INFO.info({"version": app_version})
    logger.info("[Metrics] Initialized")


def track_request(method: str, endpoint: str, status_code: int):
    """Track HTTP request."""
    REQUEST_COUNT.labels(
        method=method,
        endpoint=endpoint,
        status=str(status_code)
    ).inc()


def track_request_duration(method: str, endpoint: str, duration: float):
    """Track request duration."""
    REQUEST_DURATION.labels(
        method=method,
        endpoint=endpoint
    ).observe(duration)


def track_llm_request(model: str, status: str, latency: float):
    """Track LLM request."""
    LLM_REQUESTS.labels(model=model, status=status).inc()
    LLM_LATENCY.labels(model=model).observe(latency)


def track_tool_execution(tool_name: str, success: bool):
    """Track tool execution."""
    status = "success" if success else "failure"
    TOOL_EXECUTIONS.labels(tool_name=tool_name, status=status).inc()


def track_sandbox_execution(sandbox_type: str, success: bool):
    """Track sandbox execution."""
    status = "success" if success else "failure"
    SANDBOX_EXECUTIONS.labels(sandbox_type=sandbox_type, status=status).inc()


def set_active_sessions(count: int):
    """Set active sessions gauge."""
    ACTIVE_SESSIONS.set(count)


def set_queue_depth(queue_name: str, depth: int):
    """Set queue depth gauge."""
    TASK_QUEUE_DEPTH.labels(queue_name=queue_name).set(depth)


def timed(metric: Histogram, labels: Optional[dict] = None):
    """Decorator to time function execution."""
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        async def async_wrapper(*args, **kwargs):
            start = time.time()
            try:
                result = await func(*args, **kwargs)
                status = "success"
                return result
            except Exception as e:
                status = "failure"
                raise
            finally:
                duration = time.time() - start
                label_values = labels or {}
                label_values["status"] = status
                metric.labels(**label_values).observe(duration)
        
        @wraps(func)
        def sync_wrapper(*args, **kwargs):
            start = time.time()
            try:
                result = func(*args, **kwargs)
                status = "success"
                return result
            except Exception:
                status = "failure"
                raise
            finally:
                duration = time.time() - start
                label_values = labels or {}
                label_values["status"] = status
                metric.labels(**label_values).observe(duration)
        
        return async_wrapper if asyncio.iscoroutinefunction(func) else sync_wrapper
    return decorator


# Import asyncio at end to avoid circular imports
import asyncio