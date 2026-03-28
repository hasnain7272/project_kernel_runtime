# Observability Components

This directory contains comprehensive observability components for Project Kernel Runtime, implementing the production hardening features outlined in Month 1-2 of the project plan.

## Overview

The observability system provides:

- **OpenTelemetry Integration**: Distributed tracing and metrics collection
- **Structured Logging**: JSON-formatted logging with context propagation
- **Health Checks**: Service health monitoring and readiness probes
- **Middleware**: Automatic observability instrumentation for HTTP requests
- **Circuit Breakers**: Protection against external service failures
- **Rate Limiting**: API request rate limiting and throttling

## Architecture

```
observability/
├── __init__.py              # Public API exports
├── tracing.py               # OpenTelemetry tracing implementation
├── metrics.py               # OpenTelemetry metrics implementation
├── logging.py               # Structured logging implementation
├── health.py                # Health check endpoints and monitoring
├── middleware.py            # HTTP middleware for observability
├── requirements.txt         # Dependencies
├── setup.py                 # Package setup
└── tests/                   # Comprehensive test suite
    ├── __init__.py
    ├── conftest.py          # Pytest configuration
    ├── test_tracing.py      # Tracing component tests
    ├── test_metrics.py      # Metrics component tests
    ├── test_logging.py      # Logging component tests
    ├── test_health.py       # Health check tests
    ├── test_middleware.py   # Middleware tests
    └── test_integration.py # Integration tests
```

## Installation

### Dependencies

Install the required dependencies:

```bash
pip install -r requirements.txt
```

### Package Installation

Install the observability package:

```bash
pip install -e .
```

## Usage

### Basic Setup

```python
from project_kernel_runtime.observability import (
    setup_tracing,
    setup_metrics,
    setup_logging,
    setup_middleware,
    setup_health_check_routes
)

# Setup logging
setup_logging(level="INFO")

# Setup tracing
setup_tracing(
    service_name="project-kernel-runtime",
    endpoint="http://localhost:4318",  # Optional remote endpoint
    console_export=True
)

# Setup metrics
setup_metrics(
    service_name="project-kernel-runtime",
    endpoint="http://localhost:4318",  # Optional remote endpoint
    console_export=True
)
```

### FastAPI Integration

```python
from fastapi import FastAPI
from project_kernel_runtime.observability import (
    setup_middleware,
    setup_health_check_routes
)

app = FastAPI()

# Setup observability middleware
setup_middleware(app)

# Setup health check endpoints
setup_health_check_routes(app)

# Your application routes
@app.get("/")
async def root():
    return {"message": "Hello World"}
```

### Manual Tracing

```python
from project_kernel_runtime.observability import get_tracer, trace_orchestrator_call

tracer = get_tracer()

# Manual span creation
with tracer.start_span("manual-operation") as span:
    span.set_attribute("custom.key", "custom.value")
    # Your operation here
    result = perform_operation()
    span.set_status("OK")
```

### Decorator-based Tracing

```python
from project_kernel_runtime.observability import trace_orchestrator_call

@trace_orchestrator_call
def my_orchestrator_function():
    # Function will be automatically traced
    return "result"
```

### Structured Logging

```python
from project_kernel_runtime.observability import get_logger, log_api_request

logger = get_logger("my-service")

# Basic logging
logger.info("Operation completed", extra={"user_id": "123"})

# Specialized logging functions
log_api_request(
    method="GET",
    path="/api/users",
    status_code=200,
    duration_ms=150.5,
    user_id="123",
    trace_id="abc123"
)
```

### Health Checks

```python
from project_kernel_runtime.observability import register_custom_health_check

# Register custom health check
def check_database_connection():
    # Your database check logic
    return True

register_custom_health_check("database", check_database_connection)
```

## Configuration

### Environment Variables

- `PROJECT_KERNEL_LOG_LEVEL`: Logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
- `PROJECT_KERNEL_TRACING_ENDPOINT`: OTLP endpoint for tracing
- `PROJECT_KERNEL_METRICS_ENDPOINT`: OTLP endpoint for metrics
- `PROJECT_KERNEL_SERVICE_NAME`: Service name for observability

### Configuration Files

Create a `observability.yaml` file for advanced configuration:

```yaml
logging:
  level: INFO
  format: json
  log_dir: ./logs

tracing:
  service_name: project-kernel-runtime
  endpoint: http://localhost:4318
  console_export: true

metrics:
  service_name: project-kernel-runtime
  endpoint: http://localhost:4318
  console_export: true

health:
  checks:
    database:
      enabled: true
      timeout: 5
    redis:
      enabled: true
      timeout: 3
```

## API Endpoints

The observability system provides several health check endpoints:

- `GET /health` - Basic health check
- `GET /health/ready` - Readiness check (service ready for traffic)
- `GET /health/live` - Liveness check (service is running)
- `GET /health/metrics` - Service metrics

## Testing

Run the test suite:

```bash
# Run all tests
pytest

# Run with coverage
pytest --cov=observability

# Run specific test file
pytest tests/test_tracing.py

# Run with verbose output
pytest -v
```

## Monitoring Integration

### Prometheus

The metrics system can be integrated with Prometheus:

```python
from prometheus_client import start_http_server
from project_kernel_runtime.observability import setup_metrics

# Setup metrics
setup_metrics(service_name="my-service")

# Start Prometheus metrics server
start_http_server(8000)
```

### Jaeger

For distributed tracing with Jaeger:

```python
from project_kernel_runtime.observability import setup_tracing

# Setup tracing with Jaeger
setup_tracing(
    service_name="my-service",
    endpoint="http://localhost:14268/api/traces"
)
```

### Elasticsearch

For log aggregation with Elasticsearch:

```python
import structlog
from project_kernel_runtime.observability import setup_logging

# Setup structured logging
setup_logging(level="INFO")

# Configure structlog for Elasticsearch
structlog.configure(
    processors=[
        structlog.stdlib.filter_by_level,
        structlog.stdlib.add_logger_name,
        structlog.stdlib.add_log_level,
        structlog.stdlib.PositionalArgumentsFormatter(),
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.StackInfoRenderer(),
        structlog.processors.format_exc_info,
        structlog.processors.UnicodeDecoder(),
        structlog.processors.JSONRenderer()
    ],
    context_class=dict,
    logger_factory=structlog.stdlib.LoggerFactory(),
    wrapper_class=structlog.stdlib.BoundLogger,
    cache_logger_on_first_use=True,
)
```

## Performance Considerations

- **Batch Processing**: Traces and metrics are batched for better performance
- **Sampling**: Configure sampling rates for high-volume environments
- **Async Support**: All components are async-compatible
- **Memory Management**: Proper cleanup of resources and spans

## Security

- **Authentication**: Health check endpoints can be protected with authentication
- **Authorization**: Role-based access control for observability data
- **Encryption**: TLS encryption for remote endpoints
- **Audit Logging**: All observability operations are logged for security compliance

## Troubleshooting

### Common Issues

1. **Import Errors**: Ensure all dependencies are installed
2. **Connection Issues**: Check network connectivity to remote endpoints
3. **Performance Issues**: Adjust batch sizes and sampling rates
4. **Memory Issues**: Monitor memory usage and adjust buffer sizes

### Debug Mode

Enable debug mode for detailed troubleshooting:

```python
setup_logging(level="DEBUG")
setup_tracing(console_export=True)
setup_metrics(console_export=True)
```

## Contributing

1. Follow the existing code style and patterns
2. Add comprehensive tests for new features
3. Update documentation for API changes
4. Ensure all tests pass before submitting

## License

This project is licensed under the MIT License - see the LICENSE file for details.