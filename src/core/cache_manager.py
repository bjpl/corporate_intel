"""Redis cache management for Corporate Intelligence Platform.

This module provides Redis connection management, initialization,
and health checking capabilities.
"""

from typing import Any, Dict, Optional

import redis.asyncio as redis
from loguru import logger

from src.core.config import get_settings

# Global Redis client instance
_redis_client: Optional[redis.Redis] = None


async def init_cache() -> redis.Redis:
    """Initialize Redis cache connection.

    Returns:
        redis.Redis: Configured async Redis client

    Raises:
        redis.ConnectionError: If connection fails
    """
    global _redis_client

    if _redis_client is not None:
        logger.info("Redis cache already initialized")
        return _redis_client

    settings = get_settings()

    try:
        # Parse Redis URL or build connection string
        redis_url = settings.redis_url

        _redis_client = redis.from_url(
            redis_url,
            encoding="utf-8",
            decode_responses=True,
            socket_connect_timeout=5,
            socket_keepalive=True,
            health_check_interval=30,
        )

        # Test connection
        await _redis_client.ping()

        logger.info(
            f"Redis cache initialized successfully at {settings.REDIS_HOST}:{settings.REDIS_PORT}"
        )

        return _redis_client

    except redis.ConnectionError as e:
        logger.error(f"Failed to connect to Redis: {e}")
        raise
    except Exception as e:
        logger.error(f"Unexpected error initializing Redis cache: {e}")
        raise


async def close_cache() -> None:
    """Close Redis cache connection gracefully."""
    global _redis_client

    if _redis_client is None:
        logger.debug("No Redis connection to close")
        return

    try:
        await _redis_client.close()
        _redis_client = None
        logger.info("Redis cache connection closed successfully")
    except Exception as e:
        logger.error(f"Error closing Redis cache connection: {e}")
        raise


async def get_cache() -> Optional[redis.Redis]:
    """Get the current Redis client instance.

    Returns:
        Optional[redis.Redis]: The Redis client if initialized, None otherwise
    """
    return _redis_client


async def check_cache_health() -> Dict[str, Any]:
    """Check Redis cache health status.

    Returns:
        Dict[str, Any]: Health status information including connectivity,
                        memory usage, and key statistics
    """
    if _redis_client is None:
        return {
            "status": "unhealthy",
            "error": "Redis client not initialized",
            "connected": False,
        }

    try:
        # Ping test
        await _redis_client.ping()

        # Get server info
        info = await _redis_client.info()

        # Get memory stats
        memory_stats = await _redis_client.info("memory")

        # Get keyspace stats
        keyspace_stats = await _redis_client.info("keyspace")

        return {
            "status": "healthy",
            "connected": True,
            "redis_version": info.get("redis_version"),
            "uptime_seconds": info.get("uptime_in_seconds"),
            "memory": {
                "used_memory_human": memory_stats.get("used_memory_human"),
                "used_memory_peak_human": memory_stats.get("used_memory_peak_human"),
                "maxmemory_human": memory_stats.get("maxmemory_human"),
            },
            "keyspace": keyspace_stats,
        }

    except redis.ConnectionError as e:
        logger.error(f"Redis health check failed - connection error: {e}")
        return {
            "status": "unhealthy",
            "error": f"Connection error: {str(e)}",
            "connected": False,
        }
    except Exception as e:
        logger.error(f"Redis health check failed: {e}")
        return {
            "status": "unhealthy",
            "error": str(e),
            "connected": False,
        }


async def clear_cache() -> bool:
    """Clear all cache entries (use with caution).

    Returns:
        bool: True if successful, False otherwise
    """
    if _redis_client is None:
        logger.warning("Cannot clear cache - Redis client not initialized")
        return False

    try:
        await _redis_client.flushdb()
        logger.warning("Redis cache cleared successfully")
        return True
    except Exception as e:
        logger.error(f"Failed to clear cache: {e}")
        return False


async def set_cache(
    key: str,
    value: Any,
    ttl: Optional[int] = None,
) -> bool:
    """Set a cache value with optional TTL.

    Args:
        key: Cache key
        value: Value to cache (will be JSON serialized)
        ttl: Time to live in seconds (None = no expiration)

    Returns:
        bool: True if successful, False otherwise
    """
    if _redis_client is None:
        logger.warning("Cannot set cache - Redis client not initialized")
        return False

    try:
        if ttl:
            await _redis_client.setex(key, ttl, value)
        else:
            await _redis_client.set(key, value)
        return True
    except Exception as e:
        logger.error(f"Failed to set cache key {key}: {e}")
        return False


async def get_cache_value(key: str) -> Optional[Any]:
    """Get a value from cache.

    Args:
        key: Cache key

    Returns:
        Optional[Any]: Cached value or None if not found
    """
    if _redis_client is None:
        logger.warning("Cannot get cache - Redis client not initialized")
        return None

    try:
        return await _redis_client.get(key)
    except Exception as e:
        logger.error(f"Failed to get cache key {key}: {e}")
        return None


async def delete_cache_key(key: str) -> bool:
    """Delete a key from cache.

    Args:
        key: Cache key to delete

    Returns:
        bool: True if key was deleted, False otherwise
    """
    if _redis_client is None:
        logger.warning("Cannot delete cache - Redis client not initialized")
        return False

    try:
        result = await _redis_client.delete(key)
        return bool(result)
    except Exception as e:
        logger.error(f"Failed to delete cache key {key}: {e}")
        return False
