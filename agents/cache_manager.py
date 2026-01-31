"""
Phase 3: Caching Layer Implementation
In-memory caching for expensive operations

Author: Srikanth Bhakthan - Microsoft  
Date: October 28, 2025
"""

import time
import hashlib
import json
from typing import Any, Optional, Dict, Callable
from datetime import datetime, timedelta
from functools import wraps
import logging

logger = logging.getLogger(__name__)


class CacheManager:
    """In-memory cache with TTL and LRU eviction"""
    
    def __init__(self, default_ttl: int = 3600, max_size: int = 1000):
        self.cache: Dict[str, Dict[str, Any]] = {}
        self.default_ttl = default_ttl
        self.max_size = max_size
        self.access_times: Dict[str, float] = {}
        self.hits = 0
        self.misses = 0
        self.evictions = 0
        logger.info(f"🗄️ Cache initialized (TTL: {default_ttl}s, Max: {max_size})")
    
    def _generate_key(self, prefix: str, *args, **kwargs) -> str:
        """Generate cache key from arguments"""
        key_data = {'args': str(args), 'kwargs': str(sorted(kwargs.items()))}
        key_str = json.dumps(key_data, sort_keys=True)
        key_hash = hashlib.md5(key_str.encode()).hexdigest()[:16]
        return f"{prefix}:{key_hash}"
    
    def get(self, key: str) -> Optional[Any]:
        """Get value from cache"""
        if key not in self.cache:
            self.misses += 1
            return None
        
        entry = self.cache[key]
        if datetime.now() > entry['expires_at']:
            del self.cache[key]
            if key in self.access_times:
                del self.access_times[key]
            self.misses += 1
            return None
        
        self.access_times[key] = time.time()
        self.hits += 1
        return entry['value']
    
    def set(self, key: str, value: Any, ttl: Optional[int] = None):
        """Set value in cache"""
        if len(self.cache) >= self.max_size:
            self._evict_lru()
        
        ttl = ttl or self.default_ttl
        self.cache[key] = {
            'value': value,
            'expires_at': datetime.now() + timedelta(seconds=ttl),
            'cached_at': datetime.now()
        }
        self.access_times[key] = time.time()
    
    def _evict_lru(self):
        """Evict least recently used entry"""
        if self.access_times:
            lru_key = min(self.access_times.items(), key=lambda x: x[1])[0]
            del self.cache[lru_key]
            del self.access_times[lru_key]
            self.evictions += 1
    
    def get_stats(self) -> Dict[str, Any]:
        """Get cache statistics"""
        total = self.hits + self.misses
        hit_rate = (self.hits / total * 100) if total > 0 else 0
        return {
            'size': len(self.cache),
            'max_size': self.max_size,
            'hits': self.hits,
            'misses': self.misses,
            'evictions': self.evictions,
            'hit_rate': hit_rate
        }


_cache_manager = None

def get_cache_manager() -> CacheManager:
    """Get global cache manager"""
    global _cache_manager
    if _cache_manager is None:
        _cache_manager = CacheManager()
    return _cache_manager


def create_cache_manager(default_ttl: int = 3600, max_size: int = 1000):
    """Factory for cache manager"""
    return CacheManager(default_ttl, max_size)
