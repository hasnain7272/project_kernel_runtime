"""
Production-Grade Circuit Breaker Pattern Implementation

Prevents cascade failures by detecting when external services are struggling
and temporarily rejecting requests to allow recovery.

States:
- CLOSED: Normal operation, requests pass through
- OPEN: Service failing, reject requests immediately
- HALF_OPEN: Testing if service recovered
"""
import asyncio
import logging
import time
from dataclasses import dataclass
from enum import Enum
from typing import Any, Callable, Dict, List, Optional, TypeVar, Generic
from contextlib import asynccontextmanager
import functools

logger = logging.getLogger(__name__)


class CircuitState(Enum):
    """Circuit breaker states."""
    CLOSED = "closed"      # Normal operation
    OPEN = "open"          # Failing, reject requests
    HALF_OPEN = "half_open"  # Testing recovery


@dataclass
class CircuitBreakerConfig:
    """Configuration for circuit breaker."""
    failure_threshold: int = 5           # Failures before opening
    success_threshold: int = 3           # Successes to close from half-open
    timeout: float = 60.0                # Seconds before attempting recovery
    half_open_max_calls: int = 3       # Max calls in half-open state
    exceptions_to_track: tuple = (Exception,)  # Which exceptions count as failures
    

@dataclass
class CircuitMetrics:
    """Metrics for circuit breaker."""
    state: CircuitState
    failure_count: int
    success_count: int
    last_failure_time: Optional[float]
    total_calls: int
    total_failures: int
    total_successes: int
    rejection_count: int
    opened_at: Optional[float]
    closed_at: Optional[float]


class CircuitBreaker:
    """
    Thread-safe circuit breaker implementation.
    
    Usage:
        cb = CircuitBreaker("llm-api", config)
        
        @cb.protected
        async def call_llm_api():
            return await litellm.acompletion(...)
    """
    
    def __init__(self, name: str, config: Optional[CircuitBreakerConfig] = None):
        self.name = name
        self.config = config or CircuitBreakerConfig()
        
        self._state = CircuitState.CLOSED
        self._failure_count = 0
        self._success_count = 0
        self._last_failure_time: Optional[float] = None
        self._lock = asyncio.Lock()
        
        # Metrics
        self._total_calls = 0
        self._total_failures = 0
        self._total_successes = 0
        self._rejection_count = 0
        self._opened_at: Optional[float] = None
        self._closed_at: time.time()
        
    @property
    def state(self) -> CircuitState:
        """Current circuit state."""
        return self._state
    
    async def can_execute(self) -> bool:
        """Check if request can be executed."""
        async with self._lock:
            if self._state == CircuitState.CLOSED:
                return True
            
            if self._state == CircuitState.OPEN:
                # Check if timeout elapsed
                if self._last_failure_time:
                    elapsed = time.time() - self._last_failure_time
                    if elapsed >= self.config.timeout:
                        logger.info(
                            f"[CircuitBreaker:{self.name}] Timeout elapsed, "
                            "transitioning to HALF_OPEN"
                        )
                        self._state = CircuitState.HALF_OPEN
                        self._success_count = 0
                        return True
                    else:
                        self._rejection_count += 1
                        return False
                return False
            
            if self._state == CircuitState.HALF_OPEN:
                # In half-open, allow limited calls
                return self._success_count < self.config.half_open_max_calls
            
            return False
    
    async def record_success(self):
        """Record successful execution."""
        async with self._lock:
            self._success_count += 1
            self._total_successes += 1
            
            if self._state == CircuitState.HALF_OPEN:
                if self._success_count >= self.config.success_threshold:
                    logger.info(
                        f"[CircuitBreaker:{self.name}] Success threshold reached, "
                        "closing circuit"
                    )
                    self._close_circuit()
            else:
                # Reset failure count on success in closed state
                self._failure_count = 0
    
    async def record_failure(self, exception: Exception):
        """Record failed execution."""
        async with self._lock:
            # Check if we should track this exception
            if not isinstance(exception, self.config.exceptions_to_track):
                return
            
            self._failure_count += 1
            self._total_failures += 1
            self._last_failure_time = time.time()
            
            if self._state == CircuitState.CLOSED:
                if self._failure_count >= self.config.failure_threshold:
                    logger.warning(
                        f"[CircuitBreaker:{self.name}] Failure threshold "
                        f"({self.config.failure_threshold}) reached, opening circuit"
                    )
                    self._open_circuit()
            
            elif self._state == CircuitState.HALF_OPEN:
                logger.warning(
                    f"[CircuitBreaker:{self.name}] Failure in HALF_OPEN, "
                    "re-opening circuit"
                )
                self._open_circuit()
    
    def _open_circuit(self):
        """Open the circuit."""
        self._state = CircuitState.OPEN
        self._opened_at = time.time()
        self._success_count = 0
    
    def _close_circuit(self):
        """Close the circuit."""
        self._state = CircuitState.CLOSED
        self._failure_count = 0
        self._success_count = 0
        self._closed_at = time.time()
        self._opened_at = None
    
    def get_metrics(self) -> CircuitMetrics:
        """Get current metrics."""
        return CircuitMetrics(
            state=self._state,
            failure_count=self._failure_count,
            success_count=self._success_count,
            last_failure_time=self._last_failure_time,
            total_calls=self._total_calls,
            total_failures=self._total_failures,
            total_successes=self._total_successes,
            rejection_count=self._rejection_count,
            opened_at=self._opened_at,
            closed_at=self._closed_at
        )
    
    def protected(self, func: Callable) -> Callable:
        """Decorator to protect a function with this circuit breaker."""
        
        @functools.wraps(func)
        async def async_wrapper(*args, **kwargs):
            if not await self.can_execute():
                raise CircuitBreakerOpenError(
                    f"Circuit breaker '{self.name}' is OPEN"
                )
            
            try:
                result = await func(*args, **kwargs)
                await self.record_success()
                return result
            except Exception as e:
                await self.record_failure(e)
                raise
        
        @functools.wraps(func)
        def sync_wrapper(*args, **kwargs):
            if not asyncio.run(self.can_execute()):
                raise CircuitBreakerOpenError(
                    f"Circuit breaker '{self.name}' is OPEN"
                )
            
            try:
                result = func(*args, **kwargs)
                asyncio.run(self.record_success())
                return result
            except Exception as e:
                asyncio.run(self.record_failure(e))
                raise
        
        return async_wrapper if asyncio.iscoroutinefunction(func) else sync_wrapper


class CircuitBreakerOpenError(Exception):
    """Raised when circuit breaker is open."""
    pass


class CircuitBreakerRegistry:
    """Registry of circuit breakers for different services."""
    
    _instance = None
    _breakers: Dict[str, CircuitBreaker] = {}
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance
    
    def get_or_create(
        self,
        name: str,
        config: Optional[CircuitBreakerConfig] = None
    ) -> CircuitBreaker:
        """Get existing or create new circuit breaker."""
        if name not in self._breakers:
            self._breakers[name] = CircuitBreaker(name, config)
            logger.info(f"[CircuitBreakerRegistry] Created breaker for '{name}'")
        return self._breakers[name]
    
    def get(self, name: str) -> Optional[CircuitBreaker]:
        """Get existing circuit breaker."""
        return self._breakers.get(name)
    
    def get_all_metrics(self) -> Dict[str, CircuitMetrics]:
        """Get metrics for all circuit breakers."""
        return {name: cb.get_metrics() for name, cb in self._breakers.items()}
    
    async def health_check(self) -> Dict[str, Any]:
        """Health check for all circuit breakers."""
        open_circuits = [
            name for name, cb in self._breakers.items()
            if cb.state == CircuitState.OPEN
        ]
        
        return {
            "status": "unhealthy" if open_circuits else "healthy",
            "total_circuits": len(self._breakers),
            "open_circuits": open_circuits,
            "circuits": {
                name: {
                    "state": cb.state.value,
                    "failure_count": cb._failure_count,
                    "success_count": cb._success_count
                }
                for name, cb in self._breakers.items()
            }
        }


# Global registry
_circuit_breaker_registry = CircuitBreakerRegistry()


def get_circuit_breaker(
    name: str,
    config: Optional[CircuitBreakerConfig] = None
) -> CircuitBreaker:
    """Get or create a circuit breaker."""
    return _circuit_breaker_registry.get_or_create(name, config)


# Pre-configured circuit breakers for common services

LLM_CIRCUIT_BREAKER = CircuitBreakerConfig(
    failure_threshold=3,      # LLM APIs can fail fast
    success_threshold=2,
    timeout=30.0,              # Shorter timeout for LLM
    exceptions_to_track=(Exception,)
)

SANDBOX_CIRCUIT_BREAKER = CircuitBreakerConfig(
    failure_threshold=5,       # Sandbox can be flaky
    success_threshold=3,
    timeout=60.0,
    exceptions_to_track=(Exception,)
)

DATABASE_CIRCUIT_BREAKER = CircuitBreakerConfig(
    failure_threshold=10,      # DB is critical, more lenient
    success_threshold=5,
    timeout=120.0,
    exceptions_to_track=(Exception,)
)


# Convenience decorators

def with_circuit_breaker(
    name: str,
    config: Optional[CircuitBreakerConfig] = None
):
    """Decorator factory for circuit breaker protection."""
    breaker = get_circuit_breaker(name, config)
    return breaker.protected


def with_llm_circuit_breaker(func: Callable) -> Callable:
    """Protect LLM calls with circuit breaker."""
    breaker = get_circuit_breaker("llm-api", LLM_CIRCUIT_BREAKER)
    return breaker.protected(func)


def with_sandbox_circuit_breaker(func: Callable) -> Callable:
    """Protect sandbox calls with circuit breaker."""
    breaker = get_circuit_breaker("sandbox", SANDBOX_CIRCUIT_BREAKER)
    return breaker.protected(func)


def with_database_circuit_breaker(func: Callable) -> Callable:
    """Protect database calls with circuit breaker."""
    breaker = get_circuit_breaker("database", DATABASE_CIRCUIT_BREAKER)
    return breaker.protected(func)