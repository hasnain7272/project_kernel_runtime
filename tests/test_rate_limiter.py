"""Tests for rate limiting."""
import pytest
import pytest_asyncio
from src.infrastructure.resilience.rate_limiter import (
    RateLimitConfig, 
    RateLimitStrategy
)


class TestRateLimitConfig:
    """Test rate limit configuration."""
    
    def test_default_config(self):
        """Test default configuration."""
        config = RateLimitConfig()
        assert config.requests_per_minute == 60
        assert config.requests_per_hour == 500
        assert config.strategy == RateLimitStrategy.SLIDING_WINDOW
    
    def test_custom_config(self):
        """Test custom configuration."""
        config = RateLimitConfig(
            requests_per_minute=10,
            requests_per_hour=100
        )
        assert config.requests_per_minute == 10
        assert config.requests_per_hour == 100


class TestLocalRateLimiter:
    """Test local rate limiter."""
    
    @pytest_asyncio.fixture
    async def limiter(self):
        from src.infrastructure.resilience.rate_limiter import LocalRateLimiter
        return LocalRateLimiter()
    
    @pytest.mark.asyncio
    async def test_allows_under_limit(self, limiter):
        """Allow requests under the limit."""
        config = RateLimitConfig(requests_per_minute=2)
        
        status1 = await limiter.check_rate_limit("user-1", config)
        assert status1.allowed
        
        status2 = await limiter.check_rate_limit("user-1", config)
        assert status2.allowed
    
    @pytest.mark.asyncio
    async def test_blocks_over_limit(self, limiter):
        """Block requests over the limit."""
        config = RateLimitConfig(requests_per_minute=1)
        
        await limiter.check_rate_limit("user-1", config)
        status = await limiter.check_rate_limit("user-1", config)
        
        assert not status.allowed
        assert status.retry_after is not None
    
    @pytest.mark.asyncio
    async def test_separate_limits_per_user(self, limiter):
        """Each user has separate limits."""
        config = RateLimitConfig(requests_per_minute=1)
        
        await limiter.check_rate_limit("user-1", config)
        
        # Different user should still be allowed
        status = await limiter.check_rate_limit("user-2", config)
        assert status.allowed


class TestRateLimitedDecorator:
    """Test rate limiting decorator."""
    
    @pytest.mark.asyncio
    async def test_decorator_allows_under_limit(self):
        """Decorator allows requests under limit."""
        from src.infrastructure.resilience.rate_limiter import rate_limited
        
        call_count = 0
        
        @rate_limited(key_func=lambda: "test-key")
        async def test_func():
            nonlocal call_count
            call_count += 1
            return "success"
        
        result = await test_func()
        assert result == "success"
        assert call_count == 1
    
    @pytest.mark.asyncio
    async def test_decorator_blocks_over_limit(self):
        """Decorator blocks requests over limit."""
        from src.infrastructure.resilience.rate_limiter import rate_limited, RateLimitConfig, RateLimitStrategy
        
        config = RateLimitConfig(requests_per_minute=0, strategy=RateLimitStrategy.FIXED_WINDOW)
        
        @rate_limited(key_func=lambda: "test-key", config=config)
        async def test_func():
            return "success"
        
        with pytest.raises(Exception) as exc_info:
            await test_func()
        
        assert "Rate limit" in str(exc_info.value) or "429" in str(exc_info.value)