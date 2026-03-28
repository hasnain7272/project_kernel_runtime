# observability Module Information

This file provides an ultra-dense context mapping for agentic AI ingestion.


## File: `README.md`
Total Lines: 341

## File: `health.py`
Imports: asyncio, time, typing.{Dict,Any,Optional}, fastapi.{FastAPI,HTTPException,status}, fastapi.responses.{JSONResponse}, tracing.{get_tracer}, metrics.{get_meter}, logging.{get_logger,log_api_request}
Class `HealthChecker` (L18-106):
  > Docs: Health checker for monitoring service health.
  - `def __init__(self)` (L21-24)
  - `def _register_default_checks(self)` (L26-32) - Register default health checks.
  - `def register_check(self, name, check_func)` (L34-37) - Register a health check function.
  - `async def run_checks(self)` (L39-76) - Run all registered health checks.
  - `async def _check_database(self)` (L78-82) - Check database connectivity.
  - `async def _check_redis(self)` (L84-88) - Check Redis connectivity.
  - `async def _check_llm_provider(self)` (L90-94) - Check LLM provider connectivity.
  - `async def _check_mcp_server(self)` (L96-100) - Check MCP server connectivity.
  - `async def _check_storage(self)` (L102-106) - Check storage connectivity.
Func `def get_health_checker()` (L113-118) - Get the global health checker instance.
Func `def setup_health_check_routes(app)` (L121-237) - Setup health check routes for FastAPI application.
Func `def register_custom_health_check(name, check_func)` (L240-243) - Register a custom health check function.
Func `def setup_circuit_breaker()` (L246-250) - Setup circuit breaker for external service calls.
Func `def setup_rate_limiting()` (L253-257) - Setup rate limiting for API endpoints.

## File: `logging.py`
Imports: json, logging, logging.handlers, os, sys, datetime.{datetime}, typing.{Any,Dict,Optional,Union}, pathlib.{Path}
Class `JSONFormatter` (L15-59):
  > Docs: JSON formatter for structured logging.
  - `def format(self, record)` (L18-48) - Format log record as JSON.
  - `def _json_serializer(self, obj)` (L50-59) - JSON serializer for non-serializable objects.
Class `StructuredLogger` (L62-126):
  > Docs: Structured logger with JSON formatting and context support.
  - `def __init__(self, name, level)` (L65-71)
  - `def _setup_handlers(self)` (L73-90) - Setup logging handlers.
  - `def info(self, message)` (L92-96) - Log info message with extra context.
  - `def warning(self, message)` (L98-102) - Log warning message with extra context.
  - `def error(self, message)` (L104-108) - Log error message with extra context.
  - `def debug(self, message)` (L110-114) - Log debug message with extra context.
  - `def critical(self, message)` (L116-120) - Log critical message with extra context.
  - `def exception(self, message)` (L122-126) - Log exception message with extra context.
Func `def setup_logging(level, log_dir, json_format)` (L133-175) - Setup structured logging for the application.
Func `def get_logger(name)` (L178-185) - Get a logger instance for the specified name.
Func `def _configure_loggers()` (L188-200) - Configure specific loggers for different components.
Func `def log_api_request(method, path, status_code, duration_ms, user_id, trace_id)` (L203-225) - Log API request with structured data.
Func `def log_task_execution(task_id, task_type, status, duration_ms, user_id, trace_id)` (L228-250) - Log task execution with structured data.
Func `def log_mcp_interaction(method, tool_name, status, duration_ms, user_id, trace_id)` (L253-275) - Log MCP interaction with structured data.
Func `def log_llm_call(provider, model, prompt_tokens, completion_tokens, duration_ms, user_id, trace_id)` (L278-302) - Log LLM provider call with structured data.
Func `def log_error(error_type, error_message, context, user_id, trace_id)` (L305-324) - Log error with structured data.

## File: `metrics.py`
Imports: logging, time, typing.{Optional}, opentelemetry.{metrics}, opentelemetry.exporter.otlp.proto.http.metrics_exporter.{OTLPMetricExporter}, opentelemetry.sdk.metrics.{MeterProvider}, opentelemetry.sdk.metrics.export.{PeriodicExportingMetricReader,ConsoleMetricExporter}, opentelemetry.metrics.{Counter,Histogram,UpDownCounter}
Func `def setup_metrics(service_name, endpoint, console_export)` (L21-68) - Setup OpenTelemetry metrics with configurable exporters.
Func `def get_meter()` (L71-75) - Get the global meter instance.
Func `def get_counter(name, description)` (L78-81) - Get or create a counter metric.
Func `def get_histogram(name, description)` (L84-87) - Get or create a histogram metric.
Func `def get_up_down_counter(name, description)` (L90-93) - Get or create an up-down counter metric.
Func `def get_request_counter()` (L97-102) - Counter for HTTP requests.
Func `def get_request_duration_histogram()` (L105-110) - Histogram for HTTP request duration.
Func `def get_task_counter()` (L113-118) - Counter for tasks executed.
Func `def get_task_duration_histogram()` (L121-126) - Histogram for task execution duration.
Func `def get_error_counter()` (L129-134) - Counter for errors encountered.
Func `def get_active_sessions_counter()` (L137-142) - Counter for active user sessions.
Func `def get_mcp_calls_counter()` (L145-150) - Counter for MCP calls.
Func `def get_llm_calls_counter()` (L153-158) - Counter for LLM provider calls.
Func `def track_execution_time(metric_name, description)` (L161-199) - Decorator to track execution time of a function.
Func `def track_api_request(func)` (L202-238) - Decorator to track API request metrics.
Func `def track_task_execution(func)` (L241-277) - Decorator to track task execution metrics.

## File: `middleware.py`
Imports: time, typing.{Callable,Optional}, fastapi.{Request,Response}, fastapi.middleware.base.{BaseHTTPMiddleware}, opentelemetry.{trace}, opentelemetry.propagate.{extract}, tracing.{get_tracer}, metrics.{get_request_counter,get_request_duration_histogram}, logging.{get_logger,log_api_request}
Class `ObservabilityMiddleware` (L19-105):
  > Docs: Middleware to add observability to HTTP requests.
  - `async def dispatch(self, request, call_next)` (L22-105) - Process request with observability tracking.
Class `MetricsMiddleware` (L108-143):
  > Docs: Middleware to collect metrics for HTTP requests.
  - `async def dispatch(self, request, call_next)` (L111-143) - Process request with metrics collection.
Class `LoggingMiddleware` (L146-200):
  > Docs: Middleware to add logging to HTTP requests.
  - `async def dispatch(self, request, call_next)` (L149-200) - Process request with logging.
Class `SecurityMiddleware` (L203-260):
  > Docs: Middleware to add security logging to HTTP requests.
  - `async def dispatch(self, request, call_next)` (L206-260) - Process request with security logging.
Func `def setup_middleware(app)` (L263-274) - Setup all middleware for the FastAPI application.

## File: `requirements.txt`
Total Lines: 21

## File: `setup.py`
Imports: setuptools.{setup,find_packages}

## File: `tracing.py`
Imports: asyncio, logging, typing.{Optional}, opentelemetry.{trace}, opentelemetry.exporter.otlp.proto.http.trace_exporter.{OTLPSpanExporter}, opentelemetry.sdk.resources.{Resource}, opentelemetry.sdk.trace.{TracerProvider}, opentelemetry.sdk.trace.export.{BatchSpanProcessor,ConsoleSpanExporter}, opentelemetry.trace.{SpanKind}, opentelemetry.trace.status.{Status,StatusCode}
Func `def setup_tracing(service_name, endpoint, console_export)` (L23-73) - Setup OpenTelemetry tracing with configurable exporters.
Func `def get_tracer()` (L76-80) - Get the global tracer instance.
Func `def trace_orchestrator_call(func)` (L83-128) - Decorator to trace orchestrator method calls.
Func `def trace_api_call(func)` (L131-176) - Decorator to trace API endpoint calls.
Func `def trace_mcp_interaction(func)` (L179-220) - Decorator to trace MCP client/server interactions.
Func `async def trace_async_operation(operation_name, async_func)` (L223-265) - Trace an async operation with proper context propagation.

## File: `tests\conftest.py`
Imports: pytest, sys, pathlib.{Path}
Func `def mock_opentelemetry()` (L14-33) - Mock OpenTelemetry components for testing.
Func `def mock_fastapi()` (L36-45) - Mock FastAPI components for testing.
Func `def mock_pydantic()` (L48-55) - Mock Pydantic components for testing.

## File: `tests\test_health.py`
Imports: pytest, unittest.mock.{Mock,patch,AsyncMock}, fastapi.{FastAPI}, fastapi.testclient.{TestClient}, project_kernel_runtime.observability.health.{HealthChecker,setup_health_check_routes,get_health_checker,register_custom_health_check}
Class `TestHealthChecker` (L18-124):
  > Docs: Test cases for health checker.
  - `def test_health_checker_initialization(self)` (L21-31) - Test health checker initialization.
  - `def test_register_custom_check(self)` (L33-43) - Test registering custom health check.
  - `async def test_run_checks_all_healthy(self)` (L46-61) - Test running all health checks when all are healthy.
  - `async def test_run_checks_some_unhealthy(self)` (L64-80) - Test running health checks when some are unhealthy.
  - `async def test_run_checks_with_exception(self)` (L83-99) - Test running health checks when one throws an exception.
  - `async def test_default_checks(self)` (L102-124) - Test default health check implementations.
Class `TestHealthCheckRoutes` (L127-246):
  > Docs: Test cases for health check routes.
  - `def setup_method(self)` (L130-134) - Setup test client.
  - `def test_health_check_endpoint(self)` (L136-158) - Test basic health check endpoint.
  - `def test_health_check_endpoint_unhealthy(self)` (L160-181) - Test health check endpoint when service is unhealthy.
  - `def test_readiness_check_endpoint(self)` (L183-205) - Test readiness check endpoint.
  - `def test_readiness_check_not_ready(self)` (L207-228) - Test readiness check endpoint when not ready.
  - `def test_liveness_check_endpoint(self)` (L230-237) - Test liveness check endpoint.
  - `def test_metrics_check_endpoint(self)` (L239-246) - Test metrics check endpoint.
Class `TestHealthCheckFunctions` (L249-270):
  > Docs: Test cases for health check functions.
  - `def test_get_health_checker(self)` (L252-257) - Test getting health checker instance.
  - `def test_register_custom_health_check_function(self)` (L259-270) - Test registering custom health check function.

## File: `tests\test_integration.py`
Imports: pytest, unittest.mock.{Mock,patch,AsyncMock}, fastapi.{FastAPI}, fastapi.testclient.{TestClient}, project_kernel_runtime.observability.{setup_tracing,setup_metrics,setup_logging,setup_middleware,setup_health_check_routes}
Class `TestObservabilityIntegration` (L19-166):
  > Docs: Integration tests for observability components.
  - `def setup_method(self)` (L22-33) - Setup test environment.
  - `async def test_full_integration(self)` (L36-42) - Test full integration of observability components.
  - `def test_middleware_integration(self)` (L44-54) - Test middleware integration with FastAPI.
  - `def test_health_check_integration(self)` (L56-72) - Test health check integration.
  - `def test_error_handling_integration(self)` (L74-83) - Test error handling integration.
  - `def test_tracing_integration(self)` (L85-107) - Test tracing integration.
  - `def test_metrics_integration(self)` (L109-130) - Test metrics integration.
  - `def test_logging_integration(self)` (L132-149) - Test logging integration.
  - `def test_custom_health_check(self)` (L151-166) - Test custom health check integration.
Class `TestObservabilityConfiguration` (L169-217):
  > Docs: Test observability configuration scenarios.
  - `def test_configuration_with_remote_endpoint(self)` (L172-190) - Test configuration with remote endpoints.
  - `def test_configuration_with_different_levels(self)` (L192-203) - Test configuration with different log levels.
  - `def test_configuration_with_multiple_services(self)` (L205-217) - Test configuration with multiple service names.

## File: `tests\test_logging.py`
Imports: json, logging, pytest, unittest.mock.{Mock,patch,MagicMock}, pathlib.{Path}, project_kernel_runtime.observability.logging.{setup_logging,get_logger,JSONFormatter,StructuredLogger,log_api_request,log_task_execution,log_mcp_interaction,log_llm_call,log_error}
Class `TestJSONFormatter` (L24-96):
  > Docs: Test cases for JSON formatter.
  - `def test_format_basic_log(self)` (L27-49) - Test basic log formatting.
  - `def test_format_with_exception(self)` (L51-75) - Test log formatting with exception.
  - `def test_format_with_extra_fields(self)` (L77-96) - Test log formatting with extra fields.
Class `TestStructuredLogger` (L99-119):
  > Docs: Test cases for structured logger.
  - `def test_logger_initialization(self)` (L102-107) - Test logger initialization.
  - `def test_log_methods(self)` (L109-119) - Test all logging methods.
Class `TestLoggingSetup` (L122-150):
  > Docs: Test cases for logging setup.
  - `def test_setup_logging_basic(self)` (L125-133) - Test basic logging setup.
  - `def test_setup_logging_with_log_dir(self)` (L135-142) - Test logging setup with custom log directory.
  - `def test_get_logger(self)` (L144-150) - Test getting logger instance.
Class `TestLoggingFunctions` (L153-293):
  > Docs: Test cases for logging functions.
  - `def test_log_api_request(self)` (L156-182) - Test API request logging.
  - `def test_log_task_execution(self)` (L184-210) - Test task execution logging.
  - `def test_log_mcp_interaction(self)` (L212-238) - Test MCP interaction logging.
  - `def test_log_llm_call(self)` (L240-268) - Test LLM call logging.
  - `def test_log_error(self)` (L270-293) - Test error logging.

## File: `tests\test_metrics.py`
Imports: pytest, unittest.mock.{Mock,patch}, opentelemetry.{metrics}, opentelemetry.sdk.metrics.{MeterProvider}, project_kernel_runtime.observability.metrics.{setup_metrics,get_meter,get_counter,get_histogram,get_up_down_counter,track_execution_time,track_api_request,track_task_execution}
Class `TestMetrics` (L22-204):
  > Docs: Test cases for metrics functionality.
  - `def test_setup_metrics_with_console_export(self)` (L25-36) - Test metrics setup with console export.
  - `def test_setup_metrics_with_remote_endpoint(self)` (L38-49) - Test metrics setup with remote endpoint.
  - `def test_get_meter_not_initialized(self)` (L51-55) - Test getting meter when not initialized.
  - `def test_get_counter(self)` (L57-67) - Test getting a counter metric.
  - `def test_get_histogram(self)` (L69-79) - Test getting a histogram metric.
  - `def test_get_up_down_counter(self)` (L81-91) - Test getting an up-down counter metric.
  - `def test_track_execution_time_success(self)` (L93-106) - Test execution time tracking decorator for successful function.
  - `def test_track_execution_time_failure(self)` (L108-124) - Test execution time tracking decorator for failed function.
  - `def test_track_api_request_success(self)` (L126-144) - Test API request tracking decorator for successful request.
  - `def test_track_api_request_failure(self)` (L146-165) - Test API request tracking decorator for failed request.
  - `def test_track_task_execution_success(self)` (L167-183) - Test task execution tracking decorator for successful task.
  - `def test_track_task_execution_failure(self)` (L185-204) - Test task execution tracking decorator for failed task.

## File: `tests\test_middleware.py`
Imports: pytest, unittest.mock.{Mock,patch,AsyncMock}, fastapi.{Request,Response}, fastapi.testclient.{TestClient}, project_kernel_runtime.observability.middleware.{ObservabilityMiddleware,MetricsMiddleware,LoggingMiddleware,SecurityMiddleware,setup_middleware}
Class `TestObservabilityMiddleware` (L19-111):
  > Docs: Test cases for observability middleware.
  - `async def test_middleware_success(self)` (L23-68) - Test middleware with successful request.
  - `async def test_middleware_error(self)` (L71-111) - Test middleware with failed request.
Class `TestMetricsMiddleware` (L114-177):
  > Docs: Test cases for metrics middleware.
  - `async def test_metrics_middleware_success(self)` (L118-148) - Test metrics middleware with successful request.
  - `async def test_metrics_middleware_error(self)` (L151-177) - Test metrics middleware with failed request.
Class `TestLoggingMiddleware` (L180-286):
  > Docs: Test cases for logging middleware.
  - `async def test_logging_middleware_success(self)` (L184-236) - Test logging middleware with successful request.
  - `async def test_logging_middleware_error(self)` (L239-286) - Test logging middleware with failed request.
Class `TestSecurityMiddleware` (L289-352):
  > Docs: Test cases for security middleware.
  - `async def test_security_middleware_success(self)` (L293-352) - Test security middleware with successful request.
Class `TestMiddlewareSetup` (L355-366):
  > Docs: Test cases for middleware setup.
  - `def test_setup_middleware(self)` (L358-366) - Test middleware setup function.

## File: `tests\test_tracing.py`
Imports: pytest, unittest.mock.{Mock,patch}, opentelemetry.{trace}, opentelemetry.sdk.trace.{TracerProvider}, project_kernel_runtime.observability.tracing.{setup_tracing,get_tracer,trace_orchestrator_call,trace_api_call,trace_mcp_interaction,trace_async_operation}
Class `TestTracing` (L20-169):
  > Docs: Test cases for tracing functionality.
  - `def test_setup_tracing_with_console_export(self)` (L23-34) - Test tracing setup with console export.
  - `def test_setup_tracing_with_remote_endpoint(self)` (L36-47) - Test tracing setup with remote endpoint.
  - `def test_get_tracer_not_initialized(self)` (L49-53) - Test getting tracer when not initialized.
  - `def test_trace_orchestrator_call_success(self)` (L55-71) - Test tracing decorator for successful orchestrator call.
  - `def test_trace_orchestrator_call_failure(self)` (L73-89) - Test tracing decorator for failed orchestrator call.
  - `def test_trace_api_call_success(self)` (L91-109) - Test tracing decorator for successful API call.
  - `def test_trace_mcp_interaction_success(self)` (L111-127) - Test tracing decorator for successful MCP interaction.
  - `async def test_trace_async_operation_success(self)` (L130-148) - Test tracing for successful async operation.
  - `async def test_trace_async_operation_failure(self)` (L151-169) - Test tracing for failed async operation.