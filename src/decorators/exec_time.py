from __future__ import annotations

from abc import ABC
from functools import wraps
from math import fsum
from time import perf_counter
from typing import Callable, Concatenate, Dict, Protocol


class _PExecTimes(Protocol):
    _wrapperExecTimes: Dict[str, float]


class ExecTimes(_PExecTimes, ABC):
    """Class for storing execution times of methods."""

    def __init__(self) -> None:
        self._wrapperExecTimes: Dict[str, float] = {}
        self._otherExecTimes: Dict[str, float] = {}

    def getWrapperTotalExecTime(self) -> float:
        return fsum(self._wrapperExecTimes.values())

    def resetExecTimes(self) -> None:
        self._wrapperExecTimes = {}
        self._otherExecTimes = {}

    def addExecTime(self, key: str, time: float) -> None:
        if key not in self._otherExecTimes:
            self._otherExecTimes[key] = 0.0
        self._otherExecTimes[key] += time

    def getExecTime(self, key: str) -> float:
        return self._otherExecTimes.get(key, 0.0)


def with_time_execution[M: _PExecTimes, **P, R](
    method: Callable[Concatenate[M, P], R],
) -> Callable[Concatenate[M, P], R]:
    """Decorator to time method execution and store it in an instance attribute."""

    @wraps(method)
    def wrapper(self: M, /, *args: P.args, **kwargs: P.kwargs) -> R:
        start_time = perf_counter()
        result: R = method(self, *args, **kwargs)  # Call the actual method
        end_time = perf_counter()
        if method.__name__ not in self._wrapperExecTimes:
            self._wrapperExecTimes[method.__name__] = end_time - start_time
            return result
        self._wrapperExecTimes[method.__name__] += end_time - start_time
        return result

    return wrapper
