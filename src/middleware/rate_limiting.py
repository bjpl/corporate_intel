"""
API Rate Limiting Middleware

Implements token bucket algorithm for rate limiting with Redis backend.
Supports per-API-key, per-IP, and per-user rate limiting strategies.
"""

import time
from typing import Callable, Optional, Tuple
from datetime import datetime, timedelta

from fastapi import Request, Response, HTTPException, status
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware
from loguru import logger
import redis.asyncio as aioredis
from redis.asyncio import Redis

from src.core.config import get_settings


class RateLimiter:
    """Token bucket rate limiter with Redis backend."""

    def __init__(
        self,
        redis_client: Redis,
        requests_per_minute: int = 60,
        burst_size: int = 100,
    ):
        """
        Initialize rate limiter.

        Args:
            redis_client: Redis client for storing rate limit data
            requests_per_minute: Maximum requests allowed per minute
            burst_size: Maximum burst capacity (tokens in bucket)
        """
        self.redis = redis_client
        self.rate = requests_per_minute / 60.0  # Requests per second
        self.burst_size = burst_size
        self.refill_rate = self.rate  # Tokens added per second

    async def is_allowed(
        self,
        key: str,
        tokens_requested: int = 1,
    ) -> Tuple[bool, dict]:
        """
        Check if request is allowed under rate limit.

        Args:
            key: Unique identifier for rate limiting (API key, IP, user ID)
            tokens_requested: Number of tokens to consume (default: 1)

        Returns:
            Tuple of (is_allowed, rate_limit_info)
        """
        now = time.time()
        bucket_key = f"ratelimit:{key}"

        # Lua script for atomic token bucket implementation
        lua_script = """
        local bucket_key = KEYS[1]
        local capacity = tonumber(ARGV[1])
        local refill_rate = tonumber(ARGV[2])
        local tokens_requested = tonumber(ARGV[3])
        local now = tonumber(ARGV[4])

        -- Get current bucket state
        local bucket = redis.call('HMGET', bucket_key, 'tokens', 'last_refill')
        local tokens = tonumber(bucket[1])
        local last_refill = tonumber(bucket[2])

        -- Initialize bucket if doesn't exist
        if tokens == nil then
            tokens = capacity
            last_refill = now
        end

        -- Calculate tokens to add based on time elapsed
        local time_elapsed = now - last_refill
        local tokens_to_add = time_elapsed * refill_rate
        tokens = math.min(capacity, tokens + tokens_to_add)

        -- Check if we can consume requested tokens
        local allowed = 0
        if tokens >= tokens_requested then
            tokens = tokens - tokens_requested
            allowed = 1
        end

        -- Update bucket state
        redis.call('HMSET', bucket_key, 'tokens', tokens, 'last_refill', now)
        redis.call('EXPIRE', bucket_key, 3600)  -- Expire after 1 hour of inactivity

        return {allowed, math.floor(tokens), capacity}
        """

        try:
            # Execute Lua script atomically
            result = await self.redis.eval(
                lua_script,
                1,  # Number of keys
                bucket_key,
                self.burst_size,
                self.refill_rate,
                tokens_requested,
                now,
            )

            allowed = bool(result[0])
            remaining = int(result[1])
            limit = int(result[2])

            # Calculate reset time (when bucket will be full again)
            tokens_needed = limit - remaining
            seconds_to_reset = tokens_needed / self.refill_rate if self.refill_rate > 0 else 0
            reset_time = datetime.utcnow() + timedelta(seconds=seconds_to_reset)

            rate_limit_info = {
                "limit": limit,
                "remaining": remaining,
                "reset": int(reset_time.timestamp()),
                "reset_iso": reset_time.isoformat(),
            }

            if not allowed:
                logger.warning(
                    f"Rate limit exceeded for key: {key}",
                    extra={"key": key, "rate_limit_info": rate_limit_info},
                )

            return allowed, rate_limit_info

        except Exception as e:
            logger.error(f"Rate limiting error: {e}", exc_info=True)
            # On error, allow request but log the issue
            return True, {
                "limit": self.burst_size,
                "remaining": self.burst_size,
                "reset": int((datetime.utcnow() + timedelta(minutes=1)).timestamp()),
            }

    async def reset_limit(self, key: str) -> None:
        """Reset rate limit for a specific key."""
        bucket_key = f"ratelimit:{key}"
        await self.redis.delete(bucket_key)
        logger.info(f"Rate limit reset for key: {key}")


class RateLimitMiddleware(BaseHTTPMiddleware):
    """FastAPI middleware for rate limiting."""

    def __init__(
        self,
        app,
        redis_client: Redis,
        default_requests_per_minute: int = 60,
        default_burst_size: int = 100,
    ):
        """
        Initialize rate limit middleware.

        Args:
            app: FastAPI application
            redis_client: Redis client for rate limiting
            default_requests_per_minute: Default rate limit
            default_burst_size: Default burst capacity
        """
        super().__init__(app)
        self.limiter = RateLimiter(
            redis_client,
            requests_per_minute=default_requests_per_minute,
            burst_size=default_burst_size,
        )
        self.settings = get_settings()

    async def dispatch(
        self,
        request: Request,
        call_next: Callable,
    ) -> Response:
        """Process request with rate limiting."""

        # Skip rate limiting for health checks
        if request.url.path in ["/health", "/metrics"]:
            return await call_next(request)

        # Determine rate limit key (priority: API key > User ID > IP)
        rate_limit_key = self._get_rate_limit_key(request)

        # Check rate limit
        allowed, rate_info = await self.limiter.is_allowed(rate_limit_key)

        if not allowed:
            # Rate limit exceeded
            return JSONResponse(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                content={
                    "error": "Rate limit exceeded",
                    "message": "Too many requests. Please try again later.",
                    "rate_limit": rate_info,
                },
                headers={
                    "X-RateLimit-Limit": str(rate_info["limit"]),
                    "X-RateLimit-Remaining": "0",
                    "X-RateLimit-Reset": str(rate_info["reset"]),
                    "Retry-After": str(
                        max(1, rate_info["reset"] - int(time.time()))
                    ),
                },
            )

        # Process request
        response = await call_next(request)

        # Add rate limit headers to response
        response.headers["X-RateLimit-Limit"] = str(rate_info["limit"])
        response.headers["X-RateLimit-Remaining"] = str(rate_info["remaining"])
        response.headers["X-RateLimit-Reset"] = str(rate_info["reset"])

        return response

    def _get_rate_limit_key(self, request: Request) -> str:
        """
        Determine rate limit key from request.

        Priority order:
        1. API Key (from X-API-Key header)
        2. User ID (from authentication)
        3. Client IP address
        """
        # Check for API key
        api_key = request.headers.get("X-API-Key")
        if api_key:
            return f"apikey:{api_key}"

        # Check for authenticated user
        if hasattr(request.state, "user") and request.state.user:
            user_id = getattr(request.state.user, "id", None)
            if user_id:
                return f"user:{user_id}"

        # Fall back to IP address
        client_ip = self._get_client_ip(request)
        return f"ip:{client_ip}"

    def _get_client_ip(self, request: Request) -> str:
        """Extract client IP address from request."""
        # Check X-Forwarded-For header (behind proxy)
        forwarded_for = request.headers.get("X-Forwarded-For")
        if forwarded_for:
            # Get first IP in chain
            return forwarded_for.split(",")[0].strip()

        # Check X-Real-IP header
        real_ip = request.headers.get("X-Real-IP")
        if real_ip:
            return real_ip

        # Fall back to direct client
        return request.client.host if request.client else "unknown"


# Dependency for accessing rate limiter in routes
async def get_rate_limiter(request: Request) -> RateLimiter:
    """Dependency to get rate limiter instance."""
    if not hasattr(request.app.state, "rate_limiter"):
        raise RuntimeError("Rate limiter not initialized in application state")
    return request.app.state.rate_limiter


# Configuration for different API tiers
RATE_LIMIT_TIERS = {
    "free": {
        "requests_per_minute": 60,
        "burst_size": 100,
    },
    "basic": {
        "requests_per_minute": 300,
        "burst_size": 500,
    },
    "premium": {
        "requests_per_minute": 1000,
        "burst_size": 2000,
    },
    "enterprise": {
        "requests_per_minute": 5000,
        "burst_size": 10000,
    },
}


async def get_tier_rate_limiter(
    tier: str,
    redis_client: Redis,
) -> RateLimiter:
    """
    Get rate limiter configured for specific tier.

    Args:
        tier: Tier name (free, basic, premium, enterprise)
        redis_client: Redis client

    Returns:
        Configured RateLimiter instance
    """
    config = RATE_LIMIT_TIERS.get(tier, RATE_LIMIT_TIERS["free"])
    return RateLimiter(
        redis_client,
        requests_per_minute=config["requests_per_minute"],
        burst_size=config["burst_size"],
    )
