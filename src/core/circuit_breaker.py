"""Circuit breaker configuration for external API calls.

This module implements the Circuit Breaker pattern to prevent cascading failures
when external APIs (SEC EDGAR, Alpha Vantage, Yahoo Finance) become unavailable
or slow.

Circuit Breaker Pattern:
    - CLOSED: Normal operation, requests pass through
    - OPEN: Too many failures, requests fail immediately
    - HALF_OPEN: Testing if service recovered, limited requests allowed

Key Features:
    - Automatic failure detection and circuit opening
    - Configurable failure thresholds per API
    - Exponential backoff timeout periods
    - State change event logging for monitoring
    - Prometheus metrics integration ready

Configuration:
    - Alpha Vantage: 5 failures in 60s opens circuit
    - SEC API: 3 failures in 120s opens circuit (stricter)
    - Yahoo Finance: 5 failures in 60s opens circuit

Usage:
    from src.core.circuit_breaker import alpha_vantage_breaker

    @alpha_vantage_breaker
    async def fetch_stock_data(symbol: str):
        # API call logic
        return await api.get(symbol)
"""

import asyncio
from functools import wraps
from typing import Any, Callable, Optional, TypeVar, cast

from loguru import logger
from pybreaker import CircuitBreaker, CircuitBreakerError

# Type variable for generic function wrapping
T = TypeVar('T')


# Circuit Breaker Event Listeners
def log_circuit_state_change(breaker: CircuitBreaker, old_state: str, new_state: str) -> None:
    """Log circuit breaker state changes for monitoring.

    Args:
        breaker: The circuit breaker instance
        old_state: Previous state (open/closed/half_open)
        new_state: New state (open/closed/half_open)
    """
    logger.warning(
        f"Circuit breaker '{breaker.name}' state changed: {old_state} -> {new_state} "
        f"(failures: {breaker.fail_counter}/{breaker.fail_max})"
    )


def log_circuit_failure(breaker: CircuitBreaker, exception: Exception) -> None:
    """Log circuit breaker failure events.

    Args:
        breaker: The circuit breaker instance
        exception: The exception that caused the failure
    """
    logger.warning(
        f"Circuit breaker '{breaker.name}' recorded failure: {type(exception).__name__}: {exception} "
        f"(failures: {breaker.fail_counter}/{breaker.fail_max})"
    )


def log_circuit_success(breaker: CircuitBreaker) -> None:
    """Log circuit breaker success events (only when recovering from failures).

    Args:
        breaker: The circuit breaker instance
    """
    if breaker.fail_counter > 0:
        logger.info(
            f"Circuit breaker '{breaker.name}' recorded success "
            f"(failures reset from {breaker.fail_counter})"
        )


# Alpha Vantage Circuit Breaker
# - Free tier has strict rate limits (5 calls/min)
# - Failures often indicate rate limiting or API key issues
# - 5 consecutive failures trigger circuit open
# - 60 second timeout before attempting recovery
alpha_vantage_breaker = CircuitBreaker(
    fail_max=5,
    timeout_duration=60,
    name="alpha_vantage",
    listeners=[
        ("state_change", log_circuit_state_change),
        ("failure", log_circuit_failure),
        ("success", log_circuit_success),
    ]
)


# SEC EDGAR Circuit Breaker
# - SEC has strict rate limits (10 requests/second)
# - More conservative failure threshold (3 failures)
# - Longer timeout (120s) to respect SEC infrastructure
# - Critical for compliance - be conservative
sec_breaker = CircuitBreaker(
    fail_max=3,
    timeout_duration=120,
    name="sec_api",
    listeners=[
        ("state_change", log_circuit_state_change),
        ("failure", log_circuit_failure),
        ("success", log_circuit_success),
    ]
)


# Yahoo Finance Circuit Breaker
# - Generally reliable but can have occasional outages
# - 5 consecutive failures trigger circuit open
# - 60 second timeout before recovery attempt
yahoo_finance_breaker = CircuitBreaker(
    fail_max=5,
    timeout_duration=60,
    name="yahoo_finance",
    listeners=[
        ("state_change", log_circuit_state_change),
        ("failure", log_circuit_failure),
        ("success", log_circuit_success),
    ]
)


# Async-aware circuit breaker decorator
def async_circuit_breaker(breaker: CircuitBreaker, fallback: Optional[Callable] = None):
    """Decorator to wrap async functions with circuit breaker protection.

    This decorator handles both sync and async circuit breaker calls,
    ensuring compatibility with async/await patterns used throughout
    the application.

    Args:
        breaker: CircuitBreaker instance to use
        fallback: Optional fallback function to call when circuit is open

    Returns:
        Decorated function with circuit breaker protection

    Example:
        @async_circuit_breaker(alpha_vantage_breaker, fallback=get_cached_data)
        async def fetch_data(ticker: str):
            return await api.get(ticker)
    """
    def decorator(func: Callable[..., T]) -> Callable[..., T]:
        @wraps(func)
        async def wrapper(*args: Any, **kwargs: Any) -> T:
            try:
                # Circuit breaker call returns the result directly for async functions
                # pybreaker handles both sync and async functions automatically
                result = breaker.call(func, *args, **kwargs)

                # If the result is a coroutine, await it
                if asyncio.iscoroutine(result):
                    return await result
                return result

            except CircuitBreakerError as e:
                # Circuit is OPEN - service is down
                logger.error(
                    f"Circuit breaker '{breaker.name}' is OPEN - service unavailable. "
                    f"Failing fast to prevent cascading failures."
                )

                # Call fallback if provided
                if fallback:
                    logger.info(f"Using fallback strategy for '{breaker.name}'")
                    fallback_result = fallback(*args, **kwargs)
                    if asyncio.iscoroutine(fallback_result):
                        return await fallback_result
                    return fallback_result

                # Re-raise if no fallback
                raise

        return cast(Callable[..., T], wrapper)
    return decorator


# Fallback Strategies
# These are called when circuit breakers are OPEN


async def alpha_vantage_fallback(*args, **kwargs) -> dict:
    """Fallback strategy when Alpha Vantage API is unavailable.

    Returns empty dict with warning - caller should handle gracefully.
    """
    logger.warning("Alpha Vantage API unavailable - returning empty data")
    return {}


async def sec_fallback(*args, **kwargs) -> dict:
    """Fallback strategy when SEC EDGAR API is unavailable.

    Returns empty dict with warning - caller should handle gracefully.
    """
    logger.warning("SEC EDGAR API unavailable - returning empty data")
    return {}


async def yahoo_finance_fallback(*args, **kwargs) -> dict:
    """Fallback strategy when Yahoo Finance API is unavailable.

    Returns empty dict with warning - caller should handle gracefully.
    """
    logger.warning("Yahoo Finance API unavailable - returning empty data")
    return {}


# Circuit Breaker Status Monitoring

def get_circuit_breaker_status() -> dict[str, Any]:
    """Get status of all circuit breakers for monitoring/health checks.

    Returns:
        Dict containing status of all circuit breakers

    Example:
        {
            "alpha_vantage": {
                "state": "closed",
                "failure_count": 0,
                "failure_threshold": 5,
                "timeout_duration": 60
            },
            ...
        }
    """
    return {
        "alpha_vantage": {
            "state": alpha_vantage_breaker.current_state,
            "failure_count": alpha_vantage_breaker.fail_counter,
            "failure_threshold": alpha_vantage_breaker.fail_max,
            "timeout_duration": alpha_vantage_breaker.timeout_duration,
        },
        "sec_api": {
            "state": sec_breaker.current_state,
            "failure_count": sec_breaker.fail_counter,
            "failure_threshold": sec_breaker.fail_max,
            "timeout_duration": sec_breaker.timeout_duration,
        },
        "yahoo_finance": {
            "state": yahoo_finance_breaker.current_state,
            "failure_count": yahoo_finance_breaker.fail_counter,
            "failure_threshold": yahoo_finance_breaker.fail_max,
            "timeout_duration": yahoo_finance_breaker.timeout_duration,
        },
    }


def reset_all_circuit_breakers() -> None:
    """Reset all circuit breakers to closed state.

    Useful for:
    - Manual recovery after fixing external API issues
    - Testing scenarios
    - Forced recovery in maintenance windows
    """
    logger.info("Resetting all circuit breakers to closed state")
    for breaker in [alpha_vantage_breaker, sec_breaker, yahoo_finance_breaker]:
        try:
            # Reset the breaker state
            breaker._state = breaker._closed_state
            breaker._fail_counter = 0
            logger.info(f"Reset circuit breaker '{breaker.name}'")
        except Exception as e:
            logger.error(f"Failed to reset circuit breaker '{breaker.name}': {e}")
