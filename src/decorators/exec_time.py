from __future__ import annotations

from abc import ABC
from functools import wraps
from math import fsum
from time import perf_counter
from typing import Protocol, Dict, Callable, Concatenate


class _PExecTimes(Protocol):
    execTimes: Dict[str, float]


class ExecTimes(_PExecTimes, ABC):
    """Class for storing execution times of methods."""

    def __init__(self) -> None:
        self.execTimes: Dict[str, float] = {}

    def getTotalExecTime(self) -> float:
        return fsum(self.execTimes.values())


def with_time_execution[M: _PExecTimes, **P, R](
    method: Callable[Concatenate[M, P], R],
) -> Callable[Concatenate[M, P], R]:
    """Decorator to time method execution and store it in an instance attribute."""

    @wraps(method)
    def wrapper(self: M, /, *args: P.args, **kwargs: P.kwargs) -> R:
        start_time = perf_counter()
        result: R = method(self, *args, **kwargs)  # Call the actual method
        end_time = perf_counter()
        if method.__name__ not in self.execTimes:
            self.execTimes[method.__name__] = end_time - start_time
            return result
        self.execTimes[method.__name__] += end_time - start_time
        return result

    return wrapper
