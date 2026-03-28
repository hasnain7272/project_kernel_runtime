"""
Pytest configuration for observability tests.
"""

import pytest
import sys
from pathlib import Path

# Add the project root to Python path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

@pytest.fixture
def mock_opentelemetry():
    """Mock OpenTelemetry components for testing."""
    with pytest.MonkeyPatch().context() as m:
        # Mock OpenTelemetry imports
        m.setattr('sys.modules', {
            'opentelemetry': Mock(),
            'opentelemetry.trace': Mock(),
            'opentelemetry.metrics': Mock(),
            'opentelemetry.sdk.trace': Mock(),
            'opentelemetry.sdk.metrics': Mock(),
            'opentelemetry.sdk.trace.export': Mock(),
            'opentelemetry.sdk.metrics.export': Mock(),
            'opentelemetry.exporter.otlp.proto.http.trace_exporter': Mock(),
            'opentelemetry.exporter.otlp.proto.http.metrics_exporter': Mock(),
            'opentelemetry.exporter.jaeger': Mock(),
            'opentelemetry.exporter.zipkin': Mock(),
            'opentelemetry.instrumentation': Mock(),
            'opentelemetry.propagate': Mock(),
        })
        yield

@pytest.fixture
def mock_fastapi():
    """Mock FastAPI components for testing."""
    with pytest.MonkeyPatch().context() as m:
        # Mock FastAPI imports
        m.setattr('sys.modules', {
            'fastapi': Mock(),
            'fastapi.middleware.base': Mock(),
            'fastapi.testclient': Mock(),
        })
        yield

@pytest.fixture
def mock_pydantic():
    """Mock Pydantic components for testing."""
    with pytest.MonkeyPatch().context() as m:
        # Mock Pydantic imports
        m.setattr('sys.modules', {
            'pydantic': Mock(),
        })
        yield