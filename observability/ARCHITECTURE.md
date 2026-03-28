# observability Architecture Documentation

*Generated on: 2026-03-28T15:12:48.110515*

---

#### __init__.py *(17 lines)*

> **Imports**: `from tracing import setup_tracing`, `from tracing import get_tracer`, `from metrics import setup_metrics`, `from metrics import get_counter`, `from metrics import get_histogram`, `from logging import setup_logging`, `from logging import get_logger`

> **Constants**: `__all__`=['setup_tracing', 'get_tracer', 'setup_metrics', 'get_counter', 'get_histogram', 'setup_logging', 'get_logger']

---

#### health.py *(257 lines)*

> **Imports**: `import asyncio`, `import time`, `from typing import Dict`, `from typing import Any`, `from typing import Optional`, `from fastapi import FastAPI`, `from fastapi import HTTPException`, `from fastapi import status`, `from fastapi.responses import JSONResponse`, `from tracing import get_tracer`, `from metrics import get_meter`, `from logging import get_logger`, `from logging import log_api_request`

> **Constants**: `logger`=get_logger('health')

> **Classes**:
  - **HealthChecker** – *Health checker for monitoring service health.* (lines 18-106)
    - `__init__(self)` (lines 21-24)
    - `_register_default_checks(self)` – *Register default health checks.* (lines 26-32)
    - `register_check(self, name, check_func)` – *Register a health check function.* (lines 34-37)

> **Functions**:
  - `get_health_checker()` – *Get the global health checker instance.* (lines 113-118)
  - `setup_health_check_routes(app)` – *Setup health check routes for FastAPI application.* (lines 121-237)
  - `register_custom_health_check(name, check_func)` – *Register a custom health check function.* (lines 240-243)
  - `setup_circuit_breaker()` – *Setup circuit breaker for external service calls.* (lines 246-250)
  - `setup_rate_limiting()` – *Setup rate limiting for API endpoints.* (lines 253-257)

---

#### logging.py *(324 lines)*

> **Imports**: `import json`, `import logging`, `import logging.handlers`, `import os`, `import sys`, `from datetime import datetime`, `from typing import Any`, `from typing import Dict`, `from typing import Optional`, `from typing import Union`, `from pathlib import Path`

> **Classes**:
  - **JSONFormatter** – *JSON formatter for structured logging.* (lines 15-59)
    - `format(self, record)` – *Format log record as JSON.* (lines 18-48)
    - `_json_serializer(self, obj)` – *JSON serializer for non-serializable objects.* (lines 50-59)
  - **StructuredLogger** – *Structured logger with JSON formatting and context support.* (lines 62-126)
    - `__init__(self, name, level)` (lines 65-71)
    - `_setup_handlers(self)` – *Setup logging handlers.* (lines 73-90)
    - `info(self, message)` – *Log info message with extra context.* (lines 92-96)
    - `warning(self, message)` – *Log warning message with extra context.* (lines 98-102)
    - `error(self, message)` – *Log error message with extra context.* (lines 104-108)
    - `debug(self, message)` – *Log debug message with extra context.* (lines 110-114)
    - `critical(self, message)` – *Log critical message with extra context.* (lines 116-120)
    - `exception(self, message)` – *Log exception message with extra context.* (lines 122-126)

> **Functions**:
  - `setup_logging(level, log_dir, json_format)` – *Setup structured logging for the application.

Args:
    level: Logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
    log_dir: Directory for log files (default: ./logs)
    json_format: Whether to use JSON formatting

Returns:
    Configured logger instance* (lines 133-175)
  - `get_logger(name)` – *Get a logger instance for the specified name.* (lines 178-185)
  - `_configure_loggers()` – *Configure specific loggers for different components.* (lines 188-200)
  - `log_api_request(method, path, status_code, duration_ms, user_id, trace_id)` – *Log API request with structured data.* (lines 203-225)
  - `log_task_execution(task_id, task_type, status, duration_ms, user_id, trace_id)` – *Log task execution with structured data.* (lines 228-250)
  - `log_mcp_interaction(method, tool_name, status, duration_ms, user_id, trace_id)` – *Log MCP interaction with structured data.* (lines 253-275)
  - `log_llm_call(provider, model, prompt_tokens, completion_tokens, duration_ms, user_id, trace_id)` – *Log LLM provider call with structured data.* (lines 278-302)
  - `log_error(error_type, error_message, context, user_id, trace_id)` – *Log error with structured data.* (lines 305-324)

---

#### metrics.py *(277 lines)*

> **Imports**: `import logging`, `import time`, `from typing import Optional`, `from opentelemetry import metrics`, `from opentelemetry.exporter.otlp.proto.http.metrics_exporter import OTLPMetricExporter`, `from opentelemetry.sdk.metrics import MeterProvider`, `from opentelemetry.sdk.metrics.export import PeriodicExportingMetricReader`, `from opentelemetry.sdk.metrics.export import ConsoleMetricExporter`, `from opentelemetry.metrics import Counter`, `from opentelemetry.metrics import Histogram`, `from opentelemetry.metrics import UpDownCounter`

> **Constants**: `logger`=logging.getLogger(__name__)

> **Functions**:
  - `setup_metrics(service_name, endpoint, console_export)` – *Setup OpenTelemetry metrics with configurable exporters.

Args:
    service_name: Name of this service for resource attributes
    endpoint: OTLP endpoint for remote metrics (e.g., "http://localhost:4318")
    console_export: Whether to export metrics to console for development

Returns:
    Configured MeterProvider instance* (lines 21-68)
  - `get_meter()` – *Get the global meter instance.* (lines 71-75)
  - `get_counter(name, description)` – *Get or create a counter metric.* (lines 78-81)
  - `get_histogram(name, description)` – *Get or create a histogram metric.* (lines 84-87)
  - `get_up_down_counter(name, description)` – *Get or create an up-down counter metric.* (lines 90-93)
  - `get_request_counter()` – *Counter for HTTP requests.* (lines 97-102)
  - `get_request_duration_histogram()` – *Histogram for HTTP request duration.* (lines 105-110)
  - `get_task_counter()` – *Counter for tasks executed.* (lines 113-118)
  - `get_task_duration_histogram()` – *Histogram for task execution duration.* (lines 121-126)
  - `get_error_counter()` – *Counter for errors encountered.* (lines 129-134)
  - `get_active_sessions_counter()` – *Counter for active user sessions.* (lines 137-142)
  - `get_mcp_calls_counter()` – *Counter for MCP calls.* (lines 145-150)
  - `get_llm_calls_counter()` – *Counter for LLM provider calls.* (lines 153-158)
  - `track_execution_time(metric_name, description)` – *Decorator to track execution time of a function.

Args:
    metric_name: Name of the histogram metric to use
    description: Description of the metric

Returns:
    Decorated function with timing tracking* (lines 161-199)
  - `track_api_request(func)` – *Decorator to track API request metrics.

Args:
    func: Function to track

Returns:
    Decorated function with API request tracking* (lines 202-238)
  - `track_task_execution(func)` – *Decorator to track task execution metrics.

Args:
    func: Function to track

Returns:
    Decorated function with task execution tracking* (lines 241-277)

---

#### middleware.py *(274 lines)*

> **Imports**: `import time`, `from typing import Callable`, `from typing import Optional`, `from fastapi import Request`, `from fastapi import Response`, `from fastapi.middleware.base import BaseHTTPMiddleware`, `from opentelemetry import trace`, `from opentelemetry.propagate import extract`, `from tracing import get_tracer`, `from metrics import get_request_counter`, `from metrics import get_request_duration_histogram`, `from logging import get_logger`, `from logging import log_api_request`

> **Constants**: `logger`=get_logger('middleware')

> **Classes**:
  - **ObservabilityMiddleware** – *Middleware to add observability to HTTP requests.* (lines 19-105)
  - **MetricsMiddleware** – *Middleware to collect metrics for HTTP requests.* (lines 108-143)
  - **LoggingMiddleware** – *Middleware to add logging to HTTP requests.* (lines 146-200)
  - **SecurityMiddleware** – *Middleware to add security logging to HTTP requests.* (lines 203-260)

> **Functions**:
  - `setup_middleware(app)` – *Setup all middleware for the FastAPI application.* (lines 263-274)

---

#### setup.py *(45 lines)*

> **Imports**: `from setuptools import setup`, `from setuptools import find_packages`

---

#### tests\__init__.py *(3 lines)*

---

#### tests\conftest.py *(55 lines)*

> **Imports**: `import pytest`, `import sys`, `from pathlib import Path`

> **Constants**: `project_root`=Path(__file__).parent.parent.parent

> **Functions**:
  - `mock_opentelemetry()` – *Mock OpenTelemetry components for testing.* (lines 14-33)
  - `mock_fastapi()` – *Mock FastAPI components for testing.* (lines 36-45)
  - `mock_pydantic()` – *Mock Pydantic components for testing.* (lines 48-55)

---

#### tests\test_health.py *(270 lines)*

> **Imports**: `import pytest`, `from unittest.mock import Mock`, `from unittest.mock import patch`, `from unittest.mock import AsyncMock`, `from fastapi import FastAPI`, `from fastapi.testclient import TestClient`, `from project_kernel_runtime.observability.health import HealthChecker`, `from project_kernel_runtime.observability.health import setup_health_check_routes`, `from project_kernel_runtime.observability.health import get_health_checker`, `from project_kernel_runtime.observability.health import register_custom_health_check`

> **Classes**:
  - **TestHealthChecker** – *Test cases for health checker.* (lines 18-124)
    - `test_health_checker_initialization(self)` – *Test health checker initialization.* (lines 21-31)
    - `test_register_custom_check(self)` – *Test registering custom health check.* (lines 33-43)
  - **TestHealthCheckRoutes** – *Test cases for health check routes.* (lines 127-246)
    - `setup_method(self)` – *Setup test client.* (lines 130-134)
    - `test_health_check_endpoint(self)` – *Test basic health check endpoint.* (lines 136-158)
    - `test_health_check_endpoint_unhealthy(self)` – *Test health check endpoint when service is unhealthy.* (lines 160-181)
    - `test_readiness_check_endpoint(self)` – *Test readiness check endpoint.* (lines 183-205)
    - `test_readiness_check_not_ready(self)` – *Test readiness check endpoint when not ready.* (lines 207-228)
    - `test_liveness_check_endpoint(self)` – *Test liveness check endpoint.* (lines 230-237)
    - `test_metrics_check_endpoint(self)` – *Test metrics check endpoint.* (lines 239-246)
  - **TestHealthCheckFunctions** – *Test cases for health check functions.* (lines 249-270)
    - `test_get_health_checker(self)` – *Test getting health checker instance.* (lines 252-257)
    - `test_register_custom_health_check_function(self)` – *Test registering custom health check function.* (lines 259-270)

---

#### tests\test_integration.py *(217 lines)*

> **Imports**: `import pytest`, `from unittest.mock import Mock`, `from unittest.mock import patch`, `from unittest.mock import AsyncMock`, `from fastapi import FastAPI`, `from fastapi.testclient import TestClient`, `from project_kernel_runtime.observability import setup_tracing`, `from project_kernel_runtime.observability import setup_metrics`, `from project_kernel_runtime.observability import setup_logging`, `from project_kernel_runtime.observability import setup_middleware`, `from project_kernel_runtime.observability import setup_health_check_routes`, `from project_kernel_runtime.observability.health import register_custom_health_check`

> **Classes**:
  - **TestObservabilityIntegration** – *Integration tests for observability components.* (lines 19-166)
    - `setup_method(self)` – *Setup test environment.* (lines 22-33)
    - `test_middleware_integration(self)` – *Test middleware integration with FastAPI.* (lines 44-54)
    - `test_health_check_integration(self)` – *Test health check integration.* (lines 56-72)
    - `test_error_handling_integration(self)` – *Test error handling integration.* (lines 74-83)
    - `test_tracing_integration(self)` – *Test tracing integration.* (lines 85-107)
    - `test_metrics_integration(self)` – *Test metrics integration.* (lines 109-130)
    - `test_logging_integration(self)` – *Test logging integration.* (lines 132-149)
    - `test_custom_health_check(self)` – *Test custom health check integration.* (lines 151-166)
  - **TestObservabilityConfiguration** – *Test observability configuration scenarios.* (lines 169-217)
    - `test_configuration_with_remote_endpoint(self)` – *Test configuration with remote endpoints.* (lines 172-190)
    - `test_configuration_with_different_levels(self)` – *Test configuration with different log levels.* (lines 192-203)
    - `test_configuration_with_multiple_services(self)` – *Test configuration with multiple service names.* (lines 205-217)

---

#### tests\test_logging.py *(293 lines)*

> **Imports**: `import json`, `import logging`, `import pytest`, `from unittest.mock import Mock`, `from unittest.mock import patch`, `from unittest.mock import MagicMock`, `from pathlib import Path`, `from project_kernel_runtime.observability.logging import setup_logging`, `from project_kernel_runtime.observability.logging import get_logger`, `from project_kernel_runtime.observability.logging import JSONFormatter`, `from project_kernel_runtime.observability.logging import StructuredLogger`, `from project_kernel_runtime.observability.logging import log_api_request`, `from project_kernel_runtime.observability.logging import log_task_execution`, `from project_kernel_runtime.observability.logging import log_mcp_interaction`, `from project_kernel_runtime.observability.logging import log_llm_call`, `from project_kernel_runtime.observability.logging import log_error`

> **Classes**:
  - **TestJSONFormatter** – *Test cases for JSON formatter.* (lines 24-96)
    - `test_format_basic_log(self)` – *Test basic log formatting.* (lines 27-49)
    - `test_format_with_exception(self)` – *Test log formatting with exception.* (lines 51-75)
    - `test_format_with_extra_fields(self)` – *Test log formatting with extra fields.* (lines 77-96)
  - **TestStructuredLogger** – *Test cases for structured logger.* (lines 99-119)
    - `test_logger_initialization(self)` – *Test logger initialization.* (lines 102-107)
    - `test_log_methods(self)` – *Test all logging methods.* (lines 109-119)
  - **TestLoggingSetup** – *Test cases for logging setup.* (lines 122-150)
    - `test_setup_logging_basic(self)` – *Test basic logging setup.* (lines 125-133)
    - `test_setup_logging_with_log_dir(self)` – *Test logging setup with custom log directory.* (lines 135-142)
    - `test_get_logger(self)` – *Test getting logger instance.* (lines 144-150)
  - **TestLoggingFunctions** – *Test cases for logging functions.* (lines 153-293)
    - `test_log_api_request(self)` – *Test API request logging.* (lines 156-182)
    - `test_log_task_execution(self)` – *Test task execution logging.* (lines 184-210)
    - `test_log_mcp_interaction(self)` – *Test MCP interaction logging.* (lines 212-238)
    - `test_log_llm_call(self)` – *Test LLM call logging.* (lines 240-268)
    - `test_log_error(self)` – *Test error logging.* (lines 270-293)

---

#### tests\test_metrics.py *(204 lines)*

> **Imports**: `import pytest`, `from unittest.mock import Mock`, `from unittest.mock import patch`, `from opentelemetry import metrics`, `from opentelemetry.sdk.metrics import MeterProvider`, `from project_kernel_runtime.observability.metrics import setup_metrics`, `from project_kernel_runtime.observability.metrics import get_meter`, `from project_kernel_runtime.observability.metrics import get_counter`, `from project_kernel_runtime.observability.metrics import get_histogram`, `from project_kernel_runtime.observability.metrics import get_up_down_counter`, `from project_kernel_runtime.observability.metrics import track_execution_time`, `from project_kernel_runtime.observability.metrics import track_api_request`, `from project_kernel_runtime.observability.metrics import track_task_execution`

> **Classes**:
  - **TestMetrics** – *Test cases for metrics functionality.* (lines 22-204)
    - `test_setup_metrics_with_console_export(self)` – *Test metrics setup with console export.* (lines 25-36)
    - `test_setup_metrics_with_remote_endpoint(self)` – *Test metrics setup with remote endpoint.* (lines 38-49)
    - `test_get_meter_not_initialized(self)` – *Test getting meter when not initialized.* (lines 51-55)
    - `test_get_counter(self)` – *Test getting a counter metric.* (lines 57-67)
    - `test_get_histogram(self)` – *Test getting a histogram metric.* (lines 69-79)
    - `test_get_up_down_counter(self)` – *Test getting an up-down counter metric.* (lines 81-91)
    - `test_track_execution_time_success(self)` – *Test execution time tracking decorator for successful function.* (lines 93-106)
    - `test_track_execution_time_failure(self)` – *Test execution time tracking decorator for failed function.* (lines 108-124)
    - `test_track_api_request_success(self)` – *Test API request tracking decorator for successful request.* (lines 126-144)
    - `test_track_api_request_failure(self)` – *Test API request tracking decorator for failed request.* (lines 146-165)
    - `test_track_task_execution_success(self)` – *Test task execution tracking decorator for successful task.* (lines 167-183)
    - `test_track_task_execution_failure(self)` – *Test task execution tracking decorator for failed task.* (lines 185-204)

---

#### tests\test_middleware.py *(366 lines)*

> **Imports**: `import pytest`, `from unittest.mock import Mock`, `from unittest.mock import patch`, `from unittest.mock import AsyncMock`, `from fastapi import Request`, `from fastapi import Response`, `from fastapi.testclient import TestClient`, `from project_kernel_runtime.observability.middleware import ObservabilityMiddleware`, `from project_kernel_runtime.observability.middleware import MetricsMiddleware`, `from project_kernel_runtime.observability.middleware import LoggingMiddleware`, `from project_kernel_runtime.observability.middleware import SecurityMiddleware`, `from project_kernel_runtime.observability.middleware import setup_middleware`

> **Classes**:
  - **TestObservabilityMiddleware** – *Test cases for observability middleware.* (lines 19-111)
  - **TestMetricsMiddleware** – *Test cases for metrics middleware.* (lines 114-177)
  - **TestLoggingMiddleware** – *Test cases for logging middleware.* (lines 180-286)
  - **TestSecurityMiddleware** – *Test cases for security middleware.* (lines 289-352)
  - **TestMiddlewareSetup** – *Test cases for middleware setup.* (lines 355-366)
    - `test_setup_middleware(self)` – *Test middleware setup function.* (lines 358-366)

---

#### tests\test_tracing.py *(169 lines)*

> **Imports**: `import pytest`, `from unittest.mock import Mock`, `from unittest.mock import patch`, `from opentelemetry import trace`, `from opentelemetry.sdk.trace import TracerProvider`, `from project_kernel_runtime.observability.tracing import setup_tracing`, `from project_kernel_runtime.observability.tracing import get_tracer`, `from project_kernel_runtime.observability.tracing import trace_orchestrator_call`, `from project_kernel_runtime.observability.tracing import trace_api_call`, `from project_kernel_runtime.observability.tracing import trace_mcp_interaction`, `from project_kernel_runtime.observability.tracing import trace_async_operation`

> **Classes**:
  - **TestTracing** – *Test cases for tracing functionality.* (lines 20-169)
    - `test_setup_tracing_with_console_export(self)` – *Test tracing setup with console export.* (lines 23-34)
    - `test_setup_tracing_with_remote_endpoint(self)` – *Test tracing setup with remote endpoint.* (lines 36-47)
    - `test_get_tracer_not_initialized(self)` – *Test getting tracer when not initialized.* (lines 49-53)
    - `test_trace_orchestrator_call_success(self)` – *Test tracing decorator for successful orchestrator call.* (lines 55-71)
    - `test_trace_orchestrator_call_failure(self)` – *Test tracing decorator for failed orchestrator call.* (lines 73-89)
    - `test_trace_api_call_success(self)` – *Test tracing decorator for successful API call.* (lines 91-109)
    - `test_trace_mcp_interaction_success(self)` – *Test tracing decorator for successful MCP interaction.* (lines 111-127)

---

#### tracing.py *(265 lines)*

> **Imports**: `import asyncio`, `import logging`, `from typing import Optional`, `from opentelemetry import trace`, `from opentelemetry.exporter.otlp.proto.http.trace_exporter import OTLPSpanExporter`, `from opentelemetry.sdk.resources import Resource`, `from opentelemetry.sdk.trace import TracerProvider`, `from opentelemetry.sdk.trace.export import BatchSpanProcessor`, `from opentelemetry.sdk.trace.export import ConsoleSpanExporter`, `from opentelemetry.trace import SpanKind`, `from opentelemetry.trace.status import Status`, `from opentelemetry.trace.status import StatusCode`

> **Constants**: `logger`=logging.getLogger(__name__)

> **Functions**:
  - `setup_tracing(service_name, endpoint, console_export)` – *Setup OpenTelemetry tracing with configurable exporters.

Args:
    service_name: Name of this service for resource attributes
    endpoint: OTLP endpoint for remote tracing (e.g., "http://localhost:4318")
    console_export: Whether to export traces to console for development

Returns:
    Configured TracerProvider instance* (lines 23-73)
  - `get_tracer()` – *Get the global tracer instance.* (lines 76-80)
  - `trace_orchestrator_call(func)` – *Decorator to trace orchestrator method calls.

Args:
    func: Function to trace

Returns:
    Decorated function with tracing* (lines 83-128)
  - `trace_api_call(func)` – *Decorator to trace API endpoint calls.

Args:
    func: Function to trace

Returns:
    Decorated function with tracing* (lines 131-176)
  - `trace_mcp_interaction(func)` – *Decorator to trace MCP client/server interactions.

Args:
    func: Function to trace

Returns:
    Decorated function with tracing* (lines 179-220)

---

