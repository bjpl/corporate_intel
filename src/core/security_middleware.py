"""Security middleware for API protection."""

import time
from collections import defaultdict
from typing import Callable, Dict

from fastapi import Request, Response, status
from fastapi.responses import JSONResponse
from loguru import logger
from starlette.middleware.base import BaseHTTPMiddleware

from src.core.config import get_settings


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    """Add security headers to all responses."""

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """Add security headers to response."""
        response = await call_next(request)

        # Security headers
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["X-XSS-Protection"] = "1; mode=block"
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"

        # Content Security Policy
        response.headers["Content-Security-Policy"] = (
            "default-src 'self'; "
            "script-src 'self' 'unsafe-inline' 'unsafe-eval'; "
            "style-src 'self' 'unsafe-inline'; "
            "img-src 'self' data: https:; "
            "font-src 'self' data:; "
            "connect-src 'self'"
        )

        # HSTS (Strict Transport Security) - only in production
        settings = get_settings()
        if settings.ENVIRONMENT == "production":
            response.headers["Strict-Transport-Security"] = (
                "max-age=31536000; includeSubDomains; preload"
            )

        # Remove server header
        response.headers["Server"] = "Corporate Intel API"

        return response


class RateLimitMiddleware(BaseHTTPMiddleware):
    """Rate limiting middleware to prevent abuse."""

    def __init__(self, app, requests_per_minute: int = 60):
        """Initialize rate limiter.

        Args:
            app: FastAPI application instance
            requests_per_minute: Maximum requests allowed per minute per IP
        """
        super().__init__(app)
        self.requests_per_minute = requests_per_minute
        self.rate_limit_window = 60  # seconds

        # Store: {ip: [(timestamp, endpoint), ...]}
        self.request_history: Dict[str, list] = defaultdict(list)

        # Cleanup interval
        self.last_cleanup = time.time()
        self.cleanup_interval = 300  # 5 minutes

    def _get_client_ip(self, request: Request) -> str:
        """Extract client IP from request."""
        # Check for proxy headers first
        forwarded_for = request.headers.get("X-Forwarded-For")
        if forwarded_for:
            return forwarded_for.split(",")[0].strip()

        real_ip = request.headers.get("X-Real-IP")
        if real_ip:
            return real_ip

        # Fall back to direct connection
        if request.client:
            return request.client.host

        return "unknown"

    def _is_whitelisted(self, request: Request) -> bool:
        """Check if endpoint should bypass rate limiting."""
        # Health check endpoints
        if request.url.path.startswith("/health"):
            return True

        # Metrics endpoint
        if request.url.path.startswith("/metrics"):
            return True

        # OpenAPI docs
        if request.url.path in ["/docs", "/redoc", "/openapi.json"]:
            return True

        return False

    def _cleanup_old_requests(self, client_ip: str, current_time: float):
        """Remove requests outside the rate limit window."""
        cutoff_time = current_time - self.rate_limit_window

        if client_ip in self.request_history:
            self.request_history[client_ip] = [
                (ts, endpoint)
                for ts, endpoint in self.request_history[client_ip]
                if ts > cutoff_time
            ]

            # Remove IP if no recent requests
            if not self.request_history[client_ip]:
                del self.request_history[client_ip]

    def _periodic_cleanup(self, current_time: float):
        """Periodically clean up all old requests."""
        if current_time - self.last_cleanup > self.cleanup_interval:
            cutoff_time = current_time - self.rate_limit_window

            # Clean up all IPs
            for client_ip in list(self.request_history.keys()):
                self.request_history[client_ip] = [
                    (ts, endpoint)
                    for ts, endpoint in self.request_history[client_ip]
                    if ts > cutoff_time
                ]

                if not self.request_history[client_ip]:
                    del self.request_history[client_ip]

            self.last_cleanup = current_time
            logger.debug(f"Cleaned up rate limit history. Active IPs: {len(self.request_history)}")

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """Check rate limit and process request."""
        # Skip rate limiting for whitelisted endpoints
        if self._is_whitelisted(request):
            return await call_next(request)

        # Get client identifier
        client_ip = self._get_client_ip(request)
        current_time = time.time()

        # Periodic cleanup
        self._periodic_cleanup(current_time)

        # Clean up old requests for this client
        self._cleanup_old_requests(client_ip, current_time)

        # Check rate limit
        request_count = len(self.request_history[client_ip])

        if request_count >= self.requests_per_minute:
            logger.warning(
                f"Rate limit exceeded for {client_ip}: {request_count} requests in "
                f"{self.rate_limit_window}s (limit: {self.requests_per_minute})"
            )

            # Calculate retry-after
            oldest_request = min(ts for ts, _ in self.request_history[client_ip])
            retry_after = int(oldest_request + self.rate_limit_window - current_time) + 1

            return JSONResponse(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                content={
                    "detail": f"Rate limit exceeded. Maximum {self.requests_per_minute} requests per minute.",
                    "retry_after": retry_after,
                },
                headers={
                    "Retry-After": str(retry_after),
                    "X-RateLimit-Limit": str(self.requests_per_minute),
                    "X-RateLimit-Remaining": "0",
                    "X-RateLimit-Reset": str(int(oldest_request + self.rate_limit_window)),
                },
            )

        # Record request
        self.request_history[client_ip].append((current_time, request.url.path))

        # Process request
        response = await call_next(request)

        # Add rate limit headers to response
        remaining = self.requests_per_minute - (request_count + 1)
        response.headers["X-RateLimit-Limit"] = str(self.requests_per_minute)
        response.headers["X-RateLimit-Remaining"] = str(max(0, remaining))
        response.headers["X-RateLimit-Reset"] = str(int(current_time + self.rate_limit_window))

        return response


class RequestLoggingMiddleware(BaseHTTPMiddleware):
    """Log all requests for security monitoring."""

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """Log request details."""
        start_time = time.time()

        # Get client IP
        client_ip = request.headers.get("X-Forwarded-For", request.client.host if request.client else "unknown")

        # Log request
        logger.info(
            f"Request: {request.method} {request.url.path} from {client_ip}"
        )

        # Process request
        try:
            response = await call_next(request)

            # Calculate duration
            duration = time.time() - start_time

            # Log response
            logger.info(
                f"Response: {response.status_code} for {request.method} {request.url.path} "
                f"({duration:.3f}s)"
            )

            # Add timing header
            response.headers["X-Response-Time"] = f"{duration:.3f}s"

            return response

        except Exception as e:
            duration = time.time() - start_time
            logger.error(
                f"Error processing {request.method} {request.url.path}: {str(e)} "
                f"({duration:.3f}s)",
                exc_info=True
            )
            raise
