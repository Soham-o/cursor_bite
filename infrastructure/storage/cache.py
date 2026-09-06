# Cursor Bite — In-Memory Cache
# ============================================================
# Simple in-memory cache for translation results, OCR results,
# and other computed values. Reduces redundant processing.
#
# IMPORTANT: Cache does NOT store sensitive content persistently.
# Cache entries are in-memory only and are lost on restart.

import hashlib
import logging
import time
from dataclasses import dataclass, field
from typing import Any, Optional

from utils.logger import get_logger

logger = get_logger("infrastructure.storage.cache")


# ── Cache Entry ────────────────────────────────────────────────────

@dataclass
class CacheEntry:
    """A single cache entry with metadata."""

    key: str
    value: Any
    created_at: float = field(default_factory=time.time)
    expires_at: float = field(default_factory=lambda: time.time() + 300)  # 5 min default
    hit_count: int = 0

    @property
    def is_expired(self) -> bool:
        return time.time() > self.expires_at

    def touch(self) -> None:
        """Increment hit count."""
        self.hit_count += 1


# ── Cache ──────────────────────────────────────────────────────────

class Cache:
    """In-memory cache with TTL support.

    Thread-safe for single-reader/single-writer scenarios.
    For concurrent access, use external locking.

    IMPORTANT: This cache is for PERFORMANCE, not for persistence.
    Cache contents are lost on application restart.
    """

    def __init__(self, default_ttl: int = 300) -> None:
        self._cache: dict[str, CacheEntry] = {}
        self._default_ttl = default_ttl
        self._max_size = 1000  # Maximum number of entries

    # ── Key Generation ──────────────────────────────────────────

    def make_key(self, *parts: str) -> str:
        """Create a cache key from parts.

        Uses SHA-256 hash for consistent key length.
        """
        raw = ":".join(parts)
        return hashlib.sha256(raw.encode("utf-8")).hexdigest()[:32]

    # ── CRUD ────────────────────────────────────────────────────

    def get(self, key: str) -> Optional[Any]:
        """Get a value from cache.

        Returns None if key not found or expired.
        """
        entry = self._cache.get(key)
        if entry is None:
            return None

        if entry.is_expired:
            del self._cache[key]
            return None

        entry.touch()
        return entry.value

    def set(self, key: str, value: Any, ttl: Optional[int] = None) -> None:
        """Set a value in cache.

        Args:
            key: Cache key.
            value: Value to cache.
            ttl: Time-to-live in seconds (uses default if None).
        """
        # Enforce max size — evict oldest entries
        if len(self._cache) >= self._max_size:
            self._evict_oldest(10)

        expires_at = time.time() + (ttl if ttl is not None else self._default_ttl)
        self._cache[key] = CacheEntry(
            key=key,
            value=value,
            expires_at=expires_at,
        )

    def delete(self, key: str) -> bool:
        """Delete a cache entry. Returns True if it existed."""
        if key in self._cache:
            del self._cache[key]
            return True
        return False

    def clear(self) -> int:
        """Clear all cache entries. Returns number of entries cleared."""
        count = len(self._cache)
        self._cache.clear()
        logger.info(f"Cache cleared: {count} entries removed.")
        return count

    def size(self) -> int:
        """Get current number of cache entries."""
        # Clean expired first
        self._cleanup_expired()
        return len(self._cache)

    # ── Helpers ─────────────────────────────────────────────────

    def _evict_oldest(self, count: int) -> None:
        """Evict the oldest entries."""
        sorted_entries = sorted(
            self._cache.items(),
            key=lambda item: item[1].created_at,
        )
        for key, _ in sorted_entries[:count]:
            del self._cache[key]
        if count > 0:
            logger.debug(f"Evicted {count} oldest cache entries.")

    def _cleanup_expired(self) -> int:
        """Remove expired entries. Returns count removed."""
        expired_keys = [
            key for key, entry in self._cache.items()
            if entry.is_expired
        ]
        for key in expired_keys:
            del self._cache[key]
        if expired_keys:
            logger.debug(f"Cleaned up {len(expired_keys)} expired cache entries.")
        return len(expired_keys)

    # ── Translation Cache Helper ────────────────────────────────

    def translation_cache_key(
        self,
        text: str,
        source_lang: str,
        target_lang: str,
    ) -> str:
        """Create a cache key for a translation."""
        return self.make_key("translation", source_lang, target_lang, text[:100])

    def get_translation(
        self,
        text: str,
        source_lang: str,
        target_lang: str,
    ) -> Optional[str]:
        """Get a cached translation."""
        key = self.translation_cache_key(text, source_lang, target_lang)
        return self.get(key)

    def set_translation(
        self,
        text: str,
        source_lang: str,
        target_lang: str,
        result: str,
    ) -> None:
        """Cache a translation result."""
        key = self.translation_cache_key(text, source_lang, target_lang)
        self.set(key, result, ttl=600)  # 10 minutes for translations


# ── Module-level instance ──────────────────────────────────────────

cache = Cache()
"""Global cache instance."""
