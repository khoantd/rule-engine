"""
Caching module for Rule Engine.

This module provides intelligent caching mechanisms including:
- File-based caching with change detection
- LRU cache for frequently accessed data
- Memoization for expensive operations
- TTL-based cache expiration
"""

import os
import json
import hashlib
from functools import lru_cache, wraps
from typing import Any, Callable, Dict, Optional, Tuple
from pathlib import Path
from datetime import datetime, timedelta
from threading import Lock

from common.logger import get_logger
from common.config import get_config

logger = get_logger(__name__)


class FileCache:
    """
    File-based cache with change detection.
    
    This cache tracks file modification times and automatically invalidates
    cached data when source files change.
    """
    
    def __init__(self, ttl: Optional[int] = None):
        """
        Initialize file cache.
        
        Args:
            ttl: Time to live in seconds (None = no expiration, only file change detection)
        """
        self._cache: Dict[str, Tuple[Any, float, Dict[str, float]]] = {}
        self._lock = Lock()
        self.ttl = ttl or get_config().cache_ttl
        
    def _get_file_hash(self, file_path: str) -> str:
        """Generate hash for file content."""
        try:
            path = Path(file_path)
            if not path.exists():
                return ""
            
            # Use modification time and size for quick change detection
            stat = path.stat()
            hash_data = f"{stat.st_mtime}_{stat.st_size}"
            return hashlib.md5(hash_data.encode()).hexdigest()
        except Exception as e:
            logger.warning("Failed to get file hash", file_path=file_path, error=str(e))
            return ""
    
    def get(self, key: str, file_path: Optional[str] = None) -> Optional[Any]:
        """
        Get cached value if valid.
        
        Args:
            key: Cache key
            file_path: Optional file path to check for changes
        
        Returns:
            Cached value if valid, None otherwise
        """
        with self._lock:
            if key not in self._cache:
                return None
            
            value, timestamp, file_hashes = self._cache[key]
            
            # Check TTL expiration
            if self.ttl and (datetime.now().timestamp() - timestamp) > self.ttl:
                logger.debug("Cache expired (TTL)", key=key)
                del self._cache[key]
                return None
            
            # Check file changes
            if file_path:
                current_hash = self._get_file_hash(file_path)
                cached_hash = file_hashes.get(file_path)
                
                if current_hash != cached_hash:
                    logger.debug("Cache invalidated (file changed)", key=key, file_path=file_path)
                    del self._cache[key]
                    return None
            
            logger.debug("Cache hit", key=key)
            return value
    
    def set(self, key: str, value: Any, file_paths: Optional[list] = None) -> None:
        """
        Set cached value.
        
        Args:
            key: Cache key
            value: Value to cache
            file_paths: List of file paths that affect this cache entry
        """
        with self._lock:
            file_hashes = {}
            if file_paths:
                for file_path in file_paths:
                    file_hashes[file_path] = self._get_file_hash(file_path)
            
            self._cache[key] = (value, datetime.now().timestamp(), file_hashes)
            logger.debug("Cache set", key=key, file_count=len(file_paths) if file_paths else 0)
    
    def invalidate(self, key: Optional[str] = None) -> None:
        """
        Invalidate cache entry or all entries.
        
        Args:
            key: Cache key to invalidate (None = invalidate all)
        """
        with self._lock:
            if key:
                if key in self._cache:
                    del self._cache[key]
                    logger.debug("Cache invalidated", key=key)
            else:
                self._cache.clear()
                logger.debug("Cache cleared")
    
    def clear(self) -> None:
        """Clear all cache entries."""
        self.invalidate()


# Global file cache instance
_file_cache: Optional[FileCache] = None


def get_file_cache() -> FileCache:
    """Get global file cache instance."""
    global _file_cache
    if _file_cache is None:
        _file_cache = FileCache()
    return _file_cache


def memoize_with_cache(key_func: Optional[Callable] = None, 
                       file_paths: Optional[Callable] = None,
                       ttl: Optional[int] = None):
    """
    Memoization decorator with file change detection.
    
    Args:
        key_func: Function to generate cache key from arguments
        file_paths: Function to extract file paths from arguments for change detection
        ttl: Time to live in seconds
    
    Example:
        @memoize_with_cache(
            key_func=lambda file_path: f"config_{file_path}",
            file_paths=lambda file_path: [file_path]
        )
        def load_config(file_path):
            return json.load(open(file_path))
    """
    def decorator(func: Callable) -> Callable:
        cache = FileCache(ttl=ttl) if ttl else get_file_cache()
        
        @wraps(func)
        def wrapper(*args, **kwargs):
            # Generate cache key
            if key_func:
                cache_key = key_func(*args, **kwargs)
            else:
                cache_key = f"{func.__name__}_{hash(str(args) + str(kwargs))}"
            
            # Get file paths for change detection
            paths = None
            if file_paths:
                paths = file_paths(*args, **kwargs)
            
            # Check cache
            cached_value = cache.get(cache_key, file_path=paths[0] if paths else None)
            if cached_value is not None:
                return cached_value
            
            # Execute function
            result = func(*args, **kwargs)
            
            # Cache result
            cache.set(cache_key, result, file_paths=paths)
            
            return result
        
        # Add cache management methods
        wrapper.invalidate = lambda: cache.invalidate()
        wrapper.clear = lambda: cache.clear()
        
        return wrapper
    return decorator


def lru_cache_with_ttl(maxsize: int = 128, ttl: Optional[int] = None):
    """
    LRU cache decorator with optional TTL.
    
    Args:
        maxsize: Maximum cache size
        ttl: Time to live in seconds (None = no expiration)
    
    Example:
        @lru_cache_with_ttl(maxsize=256, ttl=3600)
        def expensive_operation(x, y):
            return x + y
    """
    def decorator(func: Callable) -> Callable:
        # Use standard lru_cache if no TTL
        if ttl is None:
            return lru_cache(maxsize=maxsize)(func)
        
        # Custom TTL-aware cache
        cache = {}
        cache_times = {}
        lock = Lock()
        
        @wraps(func)
        def wrapper(*args, **kwargs):
            cache_key = str(args) + str(kwargs)
            
            with lock:
                # Check TTL
                if cache_key in cache_times:
                    age = datetime.now().timestamp() - cache_times[cache_key]
                    if age > ttl:
                        del cache[cache_key]
                        del cache_times[cache_key]
                
                # Return cached if available
                if cache_key in cache:
                    logger.debug("LRU cache hit", function=func.__name__)
                    return cache[cache_key]
            
            # Execute and cache
            result = func(*args, **kwargs)
            
            with lock:
                # Implement LRU eviction
                if len(cache) >= maxsize:
                    # Remove oldest entry
                    oldest_key = min(cache_times.items(), key=lambda x: x[1])[0]
                    del cache[oldest_key]
                    del cache_times[oldest_key]
                
                cache[cache_key] = result
                cache_times[cache_key] = datetime.now().timestamp()
            
            logger.debug("LRU cache miss", function=func.__name__)
            return result
        
        # Add cache management
        wrapper.cache_clear = lambda: (cache.clear(), cache_times.clear())
        wrapper.cache_info = lambda: {
            'hits': len(cache),
            'maxsize': maxsize,
            'current_size': len(cache)
        }
        
        return wrapper
    return decorator

