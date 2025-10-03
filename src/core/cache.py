"""Redis caching implementation with aiocache."""

import json
from functools import wraps
from typing import Any, Callable, Optional

import redis.asyncio as redis
from aiocache import Cache
from aiocache.serializers import JsonSerializer
from loguru import logger

from src.core.config import get_settings

# Global cache instance
_cache: Optional[Cache] = None


def get_cache() -> Cache:
    """Get or create cache instance."""
    global _cache
    
    if _cache is None:
        settings = get_settings()
        
        _cache = Cache(
            Cache.REDIS,
            endpoint=settings.REDIS_HOST,
            port=settings.REDIS_PORT,
            password=settings.REDIS_PASSWORD.get_secret_value() if settings.REDIS_PASSWORD else None,
            db=settings.REDIS_DB,
            serializer=JsonSerializer(),
            namespace="corporate_intel",
        )
        
        logger.info("Redis cache initialized")
    
    return _cache


async def get_redis_client() -> redis.Redis:
    """Get Redis client for advanced operations."""
    settings = get_settings()
    
    client = redis.Redis(
        host=settings.REDIS_HOST,
        port=settings.REDIS_PORT,
        password=settings.REDIS_PASSWORD.get_secret_value() if settings.REDIS_PASSWORD else None,
        db=settings.REDIS_DB,
        decode_responses=True,
    )
    
    return client


def cache_key_wrapper(
    prefix: str = "",
    expire: int = 3600,
    key_builder: Optional[Callable] = None,
):
    """
    Decorator for caching function results.
    
    Args:
        prefix: Cache key prefix
        expire: TTL in seconds
        key_builder: Custom function to build cache key from arguments
    """
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        async def wrapper(*args, **kwargs):
            # Build cache key
            if key_builder:
                cache_key = key_builder(*args, **kwargs)
            else:
                # Default key builder
                key_parts = [prefix] if prefix else []
                
                # Add positional arguments
                for arg in args:
                    if hasattr(arg, "__dict__"):
                        # Skip complex objects like database sessions
                        continue
                    key_parts.append(str(arg))
                
                # Add keyword arguments
                for k, v in sorted(kwargs.items()):
                    if k in ["db", "current_user", "cache"]:
                        # Skip dependency injection arguments
                        continue
                    key_parts.append(f"{k}:{v}")
                
                cache_key = ":".join(key_parts)
            
            # Get cache
            cache = get_cache()
            
            # Try to get from cache
            try:
                cached_value = await cache.get(cache_key)
                if cached_value is not None:
                    logger.debug(f"Cache hit: {cache_key}")
                    return cached_value
            except Exception as e:
                logger.warning(f"Cache get error: {e}")
            
            # Execute function
            result = await func(*args, **kwargs)
            
            # Store in cache
            try:
                await cache.set(cache_key, result, ttl=expire)
                logger.debug(f"Cache set: {cache_key} (TTL: {expire}s)")
            except Exception as e:
                logger.warning(f"Cache set error: {e}")
            
            return result
        
        return wrapper
    return decorator


class CacheManager:
    """Advanced cache management operations."""
    
    def __init__(self):
        self.cache = get_cache()
    
    async def invalidate_pattern(self, pattern: str):
        """Invalidate all keys matching a pattern."""
        client = await get_redis_client()
        
        # Find all keys matching pattern
        keys = []
        async for key in client.scan_iter(match=f"corporate_intel:{pattern}"):
            keys.append(key)
        
        # Delete keys
        if keys:
            await client.delete(*keys)
            logger.info(f"Invalidated {len(keys)} cache keys matching pattern: {pattern}")
    
    async def get_metrics(self) -> dict:
        """Get cache metrics."""
        client = await get_redis_client()
        
        info = await client.info("stats")
        memory = await client.info("memory")
        
        return {
            "connected_clients": info.get("connected_clients", 0),
            "used_memory": memory.get("used_memory_human", "0"),
            "total_connections_received": info.get("total_connections_received", 0),
            "total_commands_processed": info.get("total_commands_processed", 0),
            "keyspace_hits": info.get("keyspace_hits", 0),
            "keyspace_misses": info.get("keyspace_misses", 0),
            "hit_rate": self._calculate_hit_rate(
                info.get("keyspace_hits", 0),
                info.get("keyspace_misses", 0)
            ),
        }
    
    @staticmethod
    def _calculate_hit_rate(hits: int, misses: int) -> float:
        """Calculate cache hit rate."""
        total = hits + misses
        if total == 0:
            return 0.0
        return round(hits / total * 100, 2)
    
    async def warm_cache(self, keys: dict[str, Any]):
        """Pre-populate cache with data."""
        for key, value in keys.items():
            await self.cache.set(key, value)
        
        logger.info(f"Warmed cache with {len(keys)} keys")
    
    async def clear_all(self):
        """Clear all cache entries."""
        client = await get_redis_client()
        await client.flushdb()
        logger.warning("Cleared all cache entries")


# Singleton cache manager
_cache_manager: Optional[CacheManager] = None


def get_cache_manager() -> CacheManager:
    """Get or create cache manager instance."""
    global _cache_manager
    
    if _cache_manager is None:
        _cache_manager = CacheManager()
    
    return _cache_manager