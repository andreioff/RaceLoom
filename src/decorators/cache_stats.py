from dataclasses import dataclass


@dataclass
class CacheStats:
    hits: int
    misses: int
