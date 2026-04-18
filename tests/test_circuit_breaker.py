"""
Tests for Circuit Breaker
"""
import asyncio
import pytest
import pytest_asyncio
from datetime import datetime

from src.infrastructure.resilience.circuit_breaker import (
    CircuitBreaker,
    CircuitBreakerConfig,
    CircuitBreakerOpenError,
    CircuitState,
    get_circuit_breaker
)


@pytest_asyncio.fixture
async def circuit_breaker():
    """Fixture for circuit breaker."""
    config = CircuitBreakerConfig(
        failure_threshold=3,
        success_threshold=2,
        timeout=0.1,  # Short timeout for testing
        half_open_max_calls=2
    )
    cb = CircuitBreaker("test-circuit", config)
    yield cb


@pytest.mark.asyncio
class TestCircuitBreaker:
    """Test circuit breaker functionality."""
    
    async def test_starts_closed(self, circuit_breaker):
        """Test that circuit starts closed."""
        assert circuit_breaker.state == CircuitState.CLOSED
        assert await circuit_breaker.can_execute()
    
    async def test_opens_after_failures(self, circuit_breaker):
        """Test circuit opens after failure threshold."""
        # Record failures
        for _ in range(3):
            await circuit_breaker.record_failure(Exception("Test error"))
        
        assert circuit_breaker.state == CircuitState.OPEN
        assert not await circuit_breaker.can_execute()
    
    async def test_transitions_to_half_open(self, circuit_breaker):
        """Test transition to half-open after timeout."""
        # Open circuit
        for _ in range(3):
            await circuit_breaker.record_failure(Exception("Test error"))
        
        assert circuit_breaker.state == CircuitState.OPEN
        
        # Wait for timeout
        await asyncio.sleep(0.15)
        
        # Should allow execution now
        assert await circuit_breaker.can_execute()
        assert circuit_breaker.state == CircuitState.HALF_OPEN
    
    async def test_closes_after_successes(self, circuit_breaker):
        """Test circuit closes after success threshold."""
        # Transition to half-open
        for _ in range(3):
            await circuit_breaker.record_failure(Exception("Test error"))
        
        await asyncio.sleep(0.15)
        
        # Record successes
        await circuit_breaker.record_success()
        await circuit_breaker.record_success()
        
        assert circuit_breaker.state == CircuitState.CLOSED
    
    async def test_reopens_on_failure_in_half_open(self, circuit_breaker):
        """Test circuit reopens if failure in half-open."""
        # Transition to half-open
        for _ in range(3):
            await circuit_breaker.record_failure(Exception("Test error"))
        
        await asyncio.sleep(0.15)
        
        # One success
        await circuit_breaker.record_success()
        
        # Then failure
        await circuit_breaker.record_failure(Exception("Another error"))
        
        assert circuit_breaker.state == CircuitState.OPEN
    
    async def test_resets_failure_count_on_success(self, circuit_breaker):
        """Test that success resets failure count."""
        # Record some failures
        await circuit_breaker.record_failure(Exception("Error 1"))
        await circuit_breaker.record_failure(Exception("Error 2"))
        
        # Then success
        await circuit_breaker.record_success()
        
        # Failure count should be reset
        metrics = circuit_breaker.get_metrics()
        assert metrics.failure_count == 0
    
    async def test_decorator(self, circuit_breaker):
        """Test circuit breaker decorator."""
        call_count = 0
        
        @circuit_breaker.protected
        async def protected_function():
            nonlocal call_count
            call_count += 1
            if call_count < 3:
                raise Exception("Temporary failure")
            return "success"
        
        # First calls fail
        with pytest.raises(Exception):
            await protected_function()
        
        with pytest.raises(Exception):
            await protected_function()
        
        # Circuit should open
        with pytest.raises(CircuitBreakerOpenError):
            await protected_function()
        
        assert call_count == 2


@pytest.mark.asyncio
class TestCircuitBreakerRegistry:
    """Test circuit breaker registry."""
    
    def test_singleton_registry(self):
        """Test registry is singleton."""
        from src.infrastructure.resilience.circuit_breaker import CircuitBreakerRegistry
        
        r1 = CircuitBreakerRegistry()
        r2 = CircuitBreakerRegistry()
        
        assert r1 is r2
    
    def test_get_or_create(self):
        """Test get or create returns same breaker."""
        cb1 = get_circuit_breaker("test-service")
        cb2 = get_circuit_breaker("test-service")
        
        assert cb1 is cb2
    
    async def test_health_check(self):
        """Test health check endpoint."""
        from src.infrastructure.resilience.circuit_breaker import _circuit_breaker_registry
        
        # Create some breakers
        get_circuit_breaker("healthy-service")
        
        # Get metrics
        health = await _circuit_breaker_registry.health_check()
        
        assert health["status"] in ["healthy", "unhealthy"]
        assert "circuits" in health