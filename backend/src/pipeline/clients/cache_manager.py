"""
Cache Manager for API responses

Provides caching layer for UMLS and OHDSI API responses to improve
performance and reduce API calls.

Supports:
- In-memory LRU cache (default)
- Redis cache (optional, for distributed caching)
"""

from __future__ import annotations

import json
import logging
import time
from dataclasses import dataclass
from functools import lru_cache
from typing import Any, Dict, Optional

logger = logging.getLogger(__name__)


@dataclass
class CacheStats:
    """Cache statistics."""
    hits: int = 0
    misses: int = 0
    total_requests: int = 0
    hit_rate: float = 0.0


class CacheManager:
    """
    Cache manager with LRU in-memory cache and optional Redis support.

    Usage:
        >>> cache = CacheManager()
        >>> cache.set("key", {"data": "value"}, ttl=3600)
        >>> result = cache.get("key")
        >>> print(result)
        {'data': 'value'}
    """

    def __init__(
        self,
        backend: str = "memory",
        redis_url: Optional[str] = None,
        max_size: int = 10000,
        default_ttl: int = 604800  # 7 days in seconds
    ):
        """
        Initialize cache manager.

        Args:
            backend: Cache backend ("memory" or "redis")
            redis_url: Redis connection URL (required if backend="redis")
            max_size: Maximum cache size for memory backend
            default_ttl: Default TTL in seconds
        """
        self.backend = backend
        self.default_ttl = default_ttl
        self.max_size = max_size

        # Statistics
        self._hits = 0
        self._misses = 0

        # Memory cache (always available as fallback)
        self._memory_cache: Dict[str, Dict[str, Any]] = {}

        # Redis client (optional)
        self._redis_client = None
        if backend == "redis" and redis_url:
            try:
                import redis
                self._redis_client = redis.from_url(redis_url, decode_responses=True)
                self._redis_client.ping()
                logger.info(f"Redis cache initialized: {redis_url}")
            except ImportError:
                logger.warning("Redis package not installed, falling back to memory cache")
                self.backend = "memory"
            except Exception as e:
                logger.warning(f"Redis connection failed: {e}, falling back to memory cache")
                self.backend = "memory"
        else:
            logger.info("Using in-memory cache")

    def get(self, key: str) -> Optional[Any]:
        """
        Get value from cache.

        Args:
            key: Cache key

        Returns:
            Cached value or None if not found or expired
        """
        try:
            if self.backend == "redis" and self._redis_client:
                value = self._redis_get(key)
            else:
                value = self._memory_get(key)

            if value is not None:
                self._hits += 1
                logger.debug(f"Cache HIT: {key}")
                return value
            else:
                self._misses += 1
                logger.debug(f"Cache MISS: {key}")
                return None

        except Exception as e:
            logger.error(f"Cache get error for key {key}: {e}")
            self._misses += 1
            return None

    def set(self, key: str, value: Any, ttl: Optional[int] = None):
        """
        Set value in cache.

        Args:
            key: Cache key
            value: Value to cache
            ttl: Time-to-live in seconds (None = default_ttl)
        """
        ttl = ttl or self.default_ttl

        try:
            if self.backend == "redis" and self._redis_client:
                self._redis_set(key, value, ttl)
            else:
                self._memory_set(key, value, ttl)

            logger.debug(f"Cache SET: {key} (TTL: {ttl}s)")

        except Exception as e:
            logger.error(f"Cache set error for key {key}: {e}")

    def delete(self, key: str):
        """
        Delete key from cache.

        Args:
            key: Cache key
        """
        try:
            if self.backend == "redis" and self._redis_client:
                self._redis_client.delete(key)
            else:
                self._memory_cache.pop(key, None)

            logger.debug(f"Cache DELETE: {key}")

        except Exception as e:
            logger.error(f"Cache delete error for key {key}: {e}")

    def clear(self, pattern: Optional[str] = None):
        """
        Clear cache entries matching pattern.

        Args:
            pattern: Key pattern (e.g., "umls:*") or None for all keys
        """
        try:
            if self.backend == "redis" and self._redis_client:
                if pattern:
                    keys = self._redis_client.keys(pattern)
                    if keys:
                        self._redis_client.delete(*keys)
                else:
                    self._redis_client.flushdb()
            else:
                if pattern:
                    # Simple pattern matching for memory cache
                    pattern_prefix = pattern.rstrip("*")
                    keys_to_delete = [k for k in self._memory_cache.keys() if k.startswith(pattern_prefix)]
                    for key in keys_to_delete:
                        del self._memory_cache[key]
                else:
                    self._memory_cache.clear()

            logger.info(f"Cache cleared: {pattern or 'all'}")

        except Exception as e:
            logger.error(f"Cache clear error: {e}")

    def get_stats(self) -> CacheStats:
        """
        Get cache statistics.

        Returns:
            Cache statistics
        """
        total = self._hits + self._misses
        hit_rate = self._hits / total if total > 0 else 0.0

        return CacheStats(
            hits=self._hits,
            misses=self._misses,
            total_requests=total,
            hit_rate=hit_rate
        )

    def _memory_get(self, key: str) -> Optional[Any]:
        """Get from memory cache."""
        if key not in self._memory_cache:
            return None

        entry = self._memory_cache[key]
        expiry = entry.get("expiry", 0)

        # Check expiration
        if expiry > 0 and time.time() > expiry:
            del self._memory_cache[key]
            return None

        return entry.get("value")

    def _memory_set(self, key: str, value: Any, ttl: int):
        """Set in memory cache."""
        # Implement simple LRU eviction if cache is full
        if len(self._memory_cache) >= self.max_size:
            # Remove oldest entries (simple FIFO for now)
            keys_to_remove = list(self._memory_cache.keys())[:100]
            for k in keys_to_remove:
                del self._memory_cache[k]

        expiry = time.time() + ttl if ttl > 0 else 0
        self._memory_cache[key] = {
            "value": value,
            "expiry": expiry
        }

    def _redis_get(self, key: str) -> Optional[Any]:
        """Get from Redis cache."""
        if not self._redis_client:
            return None

        value = self._redis_client.get(key)
        if value is None:
            return None

        try:
            return json.loads(value)
        except json.JSONDecodeError:
            return value

    def _redis_set(self, key: str, value: Any, ttl: int):
        """Set in Redis cache."""
        if not self._redis_client:
            return

        # Serialize value
        if isinstance(value, (dict, list)):
            serialized = json.dumps(value)
        else:
            serialized = str(value)

        self._redis_client.setex(key, ttl, serialized)


__all__ = ["CacheManager", "CacheStats"]
