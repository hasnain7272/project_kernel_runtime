"""
Health check endpoints for Project Kernel Runtime.
"""

import asyncio
import time
from typing import Dict, Any, Optional
from fastapi import FastAPI, HTTPException, status
from fastapi.responses import JSONResponse

from .tracing import get_tracer
from .metrics import get_meter
from .logging import get_logger, log_api_request

logger = get_logger("health")


class HealthChecker:
    """Health checker for monitoring service health."""
    
    def __init__(self):
        self.start_time = time.time()
        self.checks = {}
        self._register_default_checks()
    
    def _register_default_checks(self):
        """Register default health checks."""
        self.register_check("database", self._check_database)
        self.register_check("redis", self._check_redis)
        self.register_check("llm_provider", self._check_llm_provider)
        self.register_check("mcp_server", self._check_mcp_server)
        self.register_check("storage", self._check_storage)
    
    def register_check(self, name: str, check_func):
        """Register a health check function."""
        self.checks[name] = check_func
        logger.info(f"Registered health check: {name}")
    
    async def run_checks(self) -> Dict[str, Any]:
        """Run all registered health checks."""
        results = {
            "status": "healthy",
            "timestamp": time.time(),
            "uptime_seconds": time.time() - self.start_time,
            "checks": {}
        }
        
        overall_healthy = True
        
        for name, check_func in self.checks.items():
            try:
                start_time = time.time()
                result = await check_func()
                duration = (time.time() - start_time) * 1000
                
                results["checks"][name] = {
                    "status": "healthy" if result else "unhealthy",
                    "duration_ms": duration,
                    "timestamp": time.time()
                }
                
                if not result:
                    overall_healthy = False
                    
            except Exception as e:
                results["checks"][name] = {
                    "status": "error",
                    "error": str(e),
                    "duration_ms": 0,
                    "timestamp": time.time()
                }
                overall_healthy = False
        
        results["status"] = "healthy" if overall_healthy else "unhealthy"
        
        return results
    
    async def _check_database(self) -> bool:
        """Check database connectivity."""
        # Placeholder for actual database check
        # In a real implementation, this would check actual database connectivity
        return True
    
    async def _check_redis(self) -> bool:
        """Check Redis connectivity."""
        # Placeholder for actual Redis check
        # In a real implementation, this would check actual Redis connectivity
        return True
    
    async def _check_llm_provider(self) -> bool:
        """Check LLM provider connectivity."""
        # Placeholder for actual LLM provider check
        # In a real implementation, this would check actual LLM provider connectivity
        return True
    
    async def _check_mcp_server(self) -> bool:
        """Check MCP server connectivity."""
        # Placeholder for actual MCP server check
        # In a real implementation, this would check actual MCP server connectivity
        return True
    
    async def _check_storage(self) -> bool:
        """Check storage connectivity."""
        # Placeholder for actual storage check
        # In a real implementation, this would check actual storage connectivity
        return True


# Global health checker instance
_health_checker: Optional[HealthChecker] = None


def get_health_checker() -> HealthChecker:
    """Get the global health checker instance."""
    global _health_checker
    if _health_checker is None:
        _health_checker = HealthChecker()
    return _health_checker


def setup_health_check_routes(app: FastAPI):
    """Setup health check routes for FastAPI application."""
    
    @app.get("/health", response_model=Dict[str, Any])
    async def health_check():
        """Basic health check endpoint."""
        logger.info("Health check requested")
        
        try:
            results = await get_health_checker().run_checks()
            log_api_request(
                method="GET",
                path="/health",
                status_code=200 if results["status"] == "healthy" else 503,
                duration_ms=0,  # Will be measured by middleware
                trace_id=None
            )
            
            if results["status"] == "healthy":
                return results
            else:
                raise HTTPException(
                    status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                    detail=results
                )
                
        except Exception as e:
            logger.error(f"Health check failed: {e}")
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail={"status": "unhealthy", "error": str(e)}
            )
    
    @app.get("/health/ready", response_model=Dict[str, Any])
    async def readiness_check():
        """Readiness check endpoint - checks if service is ready to accept traffic."""
        logger.info("Readiness check requested")
        
        try:
            results = await get_health_checker().run_checks()
            
            # For readiness, we might have stricter requirements
            critical_checks = ["database", "llm_provider"]
            all_critical_healthy = all(
                results["checks"].get(check, {}).get("status") == "healthy"
                for check in critical_checks
            )
            
            if all_critical_healthy:
                return {
                    "status": "ready",
                    "timestamp": time.time(),
                    "critical_checks": critical_checks,
                    "results": results
                }
            else:
                raise HTTPException(
                    status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                    detail={
                        "status": "not_ready",
                        "critical_checks": critical_checks,
                        "results": results
                    }
                )
                
        except Exception as e:
            logger.error(f"Readiness check failed: {e}")
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail={"status": "not_ready", "error": str(e)}
            )
    
    @app.get("/health/live", response_model=Dict[str, Any])
    async def liveness_check():
        """Liveness check endpoint - checks if service is running."""
        logger.info("Liveness check requested")
        
        try:
            # Simple liveness check - just verify the service is running
            return {
                "status": "alive",
                "timestamp": time.time(),
                "uptime_seconds": time.time() - get_health_checker().start_time
            }
        except Exception as e:
            logger.error(f"Liveness check failed: {e}")
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail={"status": "dead", "error": str(e)}
            )
    
    @app.get("/health/metrics", response_model=Dict[str, Any])
    async def metrics_check():
        """Metrics endpoint - returns service metrics."""
        logger.info("Metrics check requested")
        
        try:
            # Get basic metrics
            meter = get_meter()
            
            # This would typically use the actual OpenTelemetry metrics API
            # For now, return basic service metrics
            return {
                "status": "healthy",
                "timestamp": time.time(),
                "uptime_seconds": time.time() - get_health_checker().start_time,
                "metrics": {
                    "service_name": "project-kernel-runtime",
                    "version": "1.0.0"
                }
            }
        except Exception as e:
            logger.error(f"Metrics check failed: {e}")
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail={"status": "error", "error": str(e)}
            )


def register_custom_health_check(name: str, check_func):
    """Register a custom health check function."""
    get_health_checker().register_check(name, check_func)
    logger.info(f"Registered custom health check: {name}")


def setup_circuit_breaker():
    """Setup circuit breaker for external service calls."""
    # This is a placeholder for circuit breaker implementation
    # In a real implementation, this would use a library like pybreaker
    pass


def setup_rate_limiting():
    """Setup rate limiting for API endpoints."""
    # This is a placeholder for rate limiting implementation
    # In a real implementation, this would use a library like slowapi
    pass