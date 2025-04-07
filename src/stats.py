from os import linesep
from typing import List
from abc import ABC, abstractmethod
from dataclasses import dataclass


@dataclass
class StatsEntry:
    key: str
    prettyName: str
    value: int | float | str


class StatsCollector:
    def __init__(self) -> None:
        self.__stats: List[StatsEntry] = []

    def addEntries(self, newStats: List[StatsEntry]) -> None:
        self.__stats.extend(newStats)

    def keys(self, sep: str) -> str:
        return sep.join([se.key for se in self.__stats])

    def values(self, sep: str) -> str:
        return sep.join([f"{se.value}" for se in self.__stats])

    def toPrettyStr(self) -> str:
        return linesep.join([f"{se.prettyName}: {se.value}" for se in self.__stats])


class StatsGenerator(ABC):
    @abstractmethod
    def getStats(self) -> List[StatsEntry]:
        return []
