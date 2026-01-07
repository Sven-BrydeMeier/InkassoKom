"""
Redis Cache Integration for InkassoKom
"""
import os
import json
import ssl
from typing import Any, Optional
from datetime import timedelta

# Try to import Redis
try:
    import redis
    HAS_REDIS = True
except ImportError:
    HAS_REDIS = False

# Try to import Streamlit for secrets
try:
    import streamlit as st
    HAS_STREAMLIT = True
except ImportError:
    HAS_STREAMLIT = False


class RedisCache:
    """Redis cache wrapper with automatic serialization."""

    DEFAULT_TTL = 300  # 5 minutes

    def __init__(self, url: Optional[str] = None):
        """Initialize Redis connection."""
        self._client = None
        self._url = url or self._get_redis_url()
        self._connected = False
        self._error_message = None

        if HAS_REDIS and self._url:
            try:
                connection_kwargs = {
                    'decode_responses': True,
                    'socket_timeout': 10,
                    'socket_connect_timeout': 10
                }

                # For rediss:// URLs (SSL), we need to configure SSL cert verification
                # Cloud services like Upstash use valid certs, so we can use default settings
                # But some services might need relaxed verification
                if self._url.startswith('rediss://'):
                    # Let redis-py handle SSL from the URL scheme
                    # Just relax cert requirements for compatibility
                    connection_kwargs['ssl_cert_reqs'] = None

                self._client = redis.from_url(
                    self._url,
                    **connection_kwargs
                )
                # Test connection
                self._client.ping()
                self._connected = True
            except Exception as e:
                self._error_message = str(e)
                print(f"Redis connection error: {e}")
                self._client = None
                self._connected = False

    def _should_use_ssl(self) -> bool:
        """Check if SSL should be used based on secrets or environment."""
        if HAS_STREAMLIT:
            try:
                redis_secrets = st.secrets.get("redis", {})
                if redis_secrets.get("ssl", False):
                    return True
            except Exception:
                pass
        return os.getenv("REDIS_SSL", "false").lower() == "true"

    def _get_redis_url(self) -> Optional[str]:
        """Get Redis URL from secrets or environment."""
        # Try Streamlit secrets first
        if HAS_STREAMLIT:
            try:
                # Try [redis] section
                redis_secrets = st.secrets.get("redis", {})
                if redis_secrets:
                    url = redis_secrets.get("url", redis_secrets.get("REDIS_URL"))
                    if url:
                        return url

                # Try various common key names at top level
                for key in ["REDIS_URL", "UPSTASH_REDIS_URL", "REDIS_TLS_URL", "redis_url"]:
                    url = st.secrets.get(key)
                    if url:
                        return url
            except Exception:
                pass

        # Fall back to environment variables
        for key in ["REDIS_URL", "UPSTASH_REDIS_URL", "REDIS_TLS_URL"]:
            url = os.getenv(key)
            if url:
                return url

        return None

    @property
    def is_connected(self) -> bool:
        """Check if Redis is connected."""
        return self._connected and self._client is not None

    def _make_key(self, namespace: str, key: str) -> str:
        """Create namespaced cache key."""
        return f"inkassokom:{namespace}:{key}"

    def get(self, namespace: str, key: str) -> Optional[Any]:
        """Get value from cache."""
        if not self.is_connected:
            return None

        try:
            cache_key = self._make_key(namespace, key)
            value = self._client.get(cache_key)
            if value:
                return json.loads(value)
        except Exception:
            pass

        return None

    def set(
        self,
        namespace: str,
        key: str,
        value: Any,
        ttl: Optional[int] = None
    ) -> bool:
        """Set value in cache."""
        if not self.is_connected:
            return False

        try:
            cache_key = self._make_key(namespace, key)
            serialized = json.dumps(value, default=str)
            self._client.setex(
                cache_key,
                ttl or self.DEFAULT_TTL,
                serialized
            )
            return True
        except Exception:
            return False

    def delete(self, namespace: str, key: str) -> bool:
        """Delete value from cache."""
        if not self.is_connected:
            return False

        try:
            cache_key = self._make_key(namespace, key)
            self._client.delete(cache_key)
            return True
        except Exception:
            return False

    def delete_pattern(self, namespace: str, pattern: str = "*") -> int:
        """Delete all keys matching pattern in namespace."""
        if not self.is_connected:
            return 0

        try:
            full_pattern = self._make_key(namespace, pattern)
            keys = self._client.keys(full_pattern)
            if keys:
                return self._client.delete(*keys)
        except Exception:
            pass

        return 0

    def clear_namespace(self, namespace: str) -> int:
        """Clear all keys in a namespace."""
        return self.delete_pattern(namespace, "*")

    def get_or_set(
        self,
        namespace: str,
        key: str,
        factory_fn,
        ttl: Optional[int] = None
    ) -> Any:
        """Get from cache or compute and store."""
        value = self.get(namespace, key)
        if value is not None:
            return value

        value = factory_fn()
        self.set(namespace, key, value, ttl)
        return value

    # Convenience methods for common operations

    def cache_case(self, case_id: str, case_data: dict, ttl: int = 600):
        """Cache case data."""
        return self.set("cases", case_id, case_data, ttl)

    def get_cached_case(self, case_id: str) -> Optional[dict]:
        """Get cached case data."""
        return self.get("cases", case_id)

    def invalidate_case(self, case_id: str):
        """Invalidate case cache."""
        self.delete("cases", case_id)

    def cache_documents(self, case_id: str, documents: list, ttl: int = 600):
        """Cache documents for a case."""
        return self.set("documents", case_id, documents, ttl)

    def get_cached_documents(self, case_id: str) -> Optional[list]:
        """Get cached documents."""
        return self.get("documents", case_id)

    def cache_user_session(self, user_id: str, session_data: dict, ttl: int = 3600):
        """Cache user session data."""
        return self.set("sessions", user_id, session_data, ttl)

    def get_user_session(self, user_id: str) -> Optional[dict]:
        """Get cached user session."""
        return self.get("sessions", user_id)

    def get_stats(self) -> dict:
        """Get cache statistics."""
        if not self.is_connected:
            return {
                "connected": False,
                "error": self._error_message,
                "url_configured": bool(self._url)
            }

        try:
            info = self._client.info()
            return {
                "connected": True,
                "used_memory": info.get("used_memory_human", "N/A"),
                "connected_clients": info.get("connected_clients", 0),
                "total_keys": self._client.dbsize(),
                "uptime_days": info.get("uptime_in_days", 0)
            }
        except Exception as e:
            return {"connected": False, "error": str(e)}


# Global cache instance
_cache_instance: Optional[RedisCache] = None


def get_cache() -> RedisCache:
    """Get or create global cache instance."""
    global _cache_instance

    if _cache_instance is None:
        _cache_instance = RedisCache()

    return _cache_instance


def cache_enabled() -> bool:
    """Check if caching is enabled and working."""
    return get_cache().is_connected


# Decorator for caching function results
def cached(namespace: str, ttl: int = 300):
    """Decorator to cache function results."""
    def decorator(func):
        def wrapper(*args, **kwargs):
            cache = get_cache()
            if not cache.is_connected:
                return func(*args, **kwargs)

            # Create cache key from function name and arguments
            key_parts = [func.__name__]
            key_parts.extend(str(arg) for arg in args)
            key_parts.extend(f"{k}={v}" for k, v in sorted(kwargs.items()))
            cache_key = ":".join(key_parts)

            # Try to get from cache
            result = cache.get(namespace, cache_key)
            if result is not None:
                return result

            # Compute and cache
            result = func(*args, **kwargs)
            cache.set(namespace, cache_key, result, ttl)
            return result

        return wrapper
    return decorator
