from __future__ import annotations
from functools import wraps
from typing import Protocol, Dict, Callable, Concatenate, Hashable, Tuple
from dataclasses import dataclass


@dataclass
class CacheStats:
    hits: int
    misses: int


class PBoolCache(Protocol):
    cache: Dict[str, Dict[Tuple[Hashable, ...], bool]]
    cacheStats: Dict[str, CacheStats]

    def getTotalCacheHits(self) -> int:
        return sum([stats.hits for stats in self.cacheStats.values()])

    def getTotalCacheMisses(self) -> int:
        return sum([stats.misses for stats in self.cacheStats.values()])


def with_bool_cache[M: PBoolCache, **P](method: Callable[Concatenate[M, P], bool]) -> Callable[Concatenate[M, P], bool]:
    """Decorator to cache method results and store them in an instance attribute of the method's class."""
    @wraps(method)
    def wrapper(self: M, /, *args: P.args, **kwargs: P.kwargs) -> bool:
        c = self.cache.setdefault(method.__name__, {})
        cs = self.cacheStats.setdefault(method.__name__, CacheStats(0, 0))

        key = (*args, tuple(**kwargs))
        if key in c:
            cs.hits += 1
            return c[key]
        result = method(self, *args, **kwargs)

        c[key] = result
        cs.misses += 1
        return result
    return wrapper
