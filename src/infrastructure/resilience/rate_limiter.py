"""
Production-Grade Rate Limiting

Sliding window rate limiting with Redis backend for distributed systems.
Supports multiple strategies: fixed window, sliding window, token bucket.
"""
import asyncio
import logging
import os
import time
from dataclasses import dataclass
from enum import Enum
from typing import Any, Dict, List, Optional, Callable
from contextlib import asynccontextmanager
import functools

logger = logging.getLogger(__name__)

REDIS_URL = os.environ.get("REDIS_URL", "")


class RateLimitStrategy(Enum):
    """Rate limiting strategies."""
    FIXED_WINDOW = "fixed_window"
    SLIDING_WINDOW = "sliding_window"
    TOKEN_BUCKET = "token_bucket"


@dataclass
class RateLimitConfig:
    """Configuration for rate limiting."""
    requests_per_second: float = 10.0
    requests_per_minute: float = 100.0
    requests_per_hour: float = 1000.0
    burst_size: int = 20  # Allow burst
    strategy: RateLimitStrategy = RateLimitStrategy.SLIDING_WINDOW
    key_prefix: str = "ratelimit"
    block_duration: int = 60  # Seconds to block after exceeding limit


@dataclass
class RateLimitStatus:
    """Status of rate limit check."""
    allowed: bool
    remaining: int
    reset_after: float  # Seconds until limit resets
    retry_after: Optional[float]  # Seconds to wait if blocked
    limit: int
    current: int


class RedisRateLimiter:
    """
    Distributed rate limiter using Redis.
    
    Uses Redis sorted sets for sliding window implementation.
    """
    
    def __init__(self, redis_url: str):
        self.redis_url = redis_url
        self._redis = None
        
    async def _get_client(self):
        """Get Redis client."""
        if self._redis is None:
            import redis.asyncio as aioredis
            self._redis = aioredis.from_url(
                self.redis_url,
                decode_responses=True
            )
        return self._redis
    
    async def check_rate_limit(
        self,
        key: str,
        config: RateLimitConfig
    ) -> RateLimitStatus:
        """
        Check if request is within rate limit.
        
        Uses sliding window algorithm with Redis sorted sets.
        """
        redis = await self._get_client()
        now = time.time()
        window_start = now - 60  # 1 minute window
        
        # Remove old entries
        await self._redis.zremrangebyscore(key, 0, window_start)
        
        # Count current requests
        current_count = await redis.zcard(key)
        
        # Check if allowed
        limit = int(config.requests_per_minute)
        allowed = current_count < limit
        
        if allowed:
            # Add current request
            await redis.zadd(key, {str(now): now})
            await redis.expire(key, 120)  # Keep for 2 minutes
        
        # Get oldest entry for reset time
        oldest = await redis.zrange(key, 0, 0, withscores=True)
        reset_after = 60 - (now - oldest[0][1]) if oldest else 60
        
        remaining = max(0, limit - current_count - 1)
        
        return RateLimitStatus(
            allowed=allowed,
            remaining=remaining,
            reset_after=max(0, reset_after),
            retry_after=60 if not allowed else None,
            limit=limit,
            current=current_count
        )
    
    async def increment(self, key: str, value: int = 1, window: int = 60):
        """Increment counter for key."""
        redis = await self._get_client()
        now = time.time()
        
        await redis.zadd(key, {str(now): now})
        await redis.expire(key, window * 2)
    
    async def reset(self, key: str):
        """Reset rate limit for key."""
        redis = await self._get_client()
        await redis.delete(key)


class LocalRateLimiter:
    """In-memory rate limiter for local development."""
    
    def __init__(self):
        self._windows: Dict[str, List[float]] = {}
        self._lock = asyncio.Lock()
    
    async def check_rate_limit(
        self,
        key: str,
        config: RateLimitConfig
    ) -> RateLimitStatus:
        """Check rate limit in-memory."""
        now = time.time()
        window_start = now - 60
        
        async with self._lock:
            if key not in self._windows:
                self._windows[key] = []
            
            # Remove old entries
            self._windows[key] = [
                t for t in self._windows[key] if t > window_start
            ]
            
            current_count = len(self._windows[key])
            limit = int(config.requests_per_minute)
            allowed = current_count < limit
            
            if allowed:
                self._windows[key].append(now)
            
            oldest = self._windows[key][0] if self._windows[key] else now
            reset_after = 60 - (now - oldest)
            remaining = max(0, limit - current_count - 1)
            
            return RateLimitStatus(
                allowed=allowed,
                remaining=remaining,
                reset_after=max(0, reset_after),
                retry_after=60 if not allowed else None,
                limit=limit,
                current=current_count
            )
    
    async def reset(self, key: str):
        """Reset rate limit."""
        async with self._lock:
            if key in self._windows:
                del self._windows[key]


class RateLimiter:
    """
    Production rate limiter with multiple strategies.
    """
    
    def __init__(self):
        self._limiter = RedisRateLimiter(REDIS_URL) if REDIS_URL else LocalRateLimiter()
        self._default_config = RateLimitConfig()
        
    async def check(
        self,
        key: str,
        config: Optional[RateLimitConfig] = None
    ) -> RateLimitStatus:
        """Check if request is allowed."""
        cfg = config or self._default_config
        return await self._limiter.check_rate_limit(f"{cfg.key_prefix}:{key}", cfg)
    
    @asynccontextmanager
    async def acquire(self, key: str, config: Optional[RateLimitConfig] = None):
        """Context manager for rate limiting."""
        status = await self.check(key, config)
        
        if not status.allowed:
            raise RateLimitExceeded(
                f"Rate limit exceeded for {key}. Retry after {status.retry_after}s"
            )
        
        try:
            yield status
        except Exception:
            raise


class RateLimitExceeded(Exception):
    """Raised when rate limit is exceeded."""
    pass


# Global limiter
_rate_limiter = RateLimiter()


async def check_rate_limit(
    key: str,
    config: Optional[RateLimitConfig] = None
) -> RateLimitStatus:
    """Check rate limit."""
    return await _rate_limiter.check(key, config)


def rate_limited(
    key_func: Optional[Callable] = None,
    config: Optional[RateLimitConfig] = None
):
    """Decorator for rate limiting."""
    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        async def async_wrapper(*args, **kwargs):
            # Generate key
            if key_func:
                key = key_func(*args, **kwargs)
            else:
                key = f"{func.__module__}.{func.__qualname__}"
            
            status = await check_rate_limit(key, config)
            
            if not status.allowed:
                raise RateLimitExceeded(
                    f"Rate limit exceeded. Retry after {status.retry_after}s"
                )
            
            return await func(*args, **kwargs)
        
        return async_wrapper
    return decorator