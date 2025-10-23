from __future__ import annotations

import copy
import time
from collections import OrderedDict
from typing import Any


class TTLCache:
    """Lightweight in-process cache with TTL support."""

    def __init__(self, maxsize: int = 256, ttl: float = 600.0) -> None:
        self.maxsize = maxsize
        self.ttl = ttl
        self._store: OrderedDict[str, tuple[float, Any]] = OrderedDict()

    def get(self, key: str) -> Any | None:
        if key not in self._store:
            return None
        expires_at, value = self._store.get(key, (0.0, None))
        if expires_at < time.monotonic():
            self._store.pop(key, None)
            return None
        # Refresh LRU ordering.
        self._store.move_to_end(key)
        return copy.deepcopy(value)

    def set(self, key: str, value: Any) -> None:
        expires_at = time.monotonic() + self.ttl
        self._store[key] = (expires_at, copy.deepcopy(value))
        self._store.move_to_end(key)
        while len(self._store) > self.maxsize:
            self._store.popitem(last=False)


def make_analysis_cache_key(deal_id: int, question: str | None) -> str:
    normalized = (question or "").strip().lower()
    return f"{deal_id}:{normalized}"


analyses_cache = TTLCache()
