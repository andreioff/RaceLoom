from abc import ABC, abstractmethod
from dataclasses import dataclass
from enum import StrEnum
from typing import List, Self

from src.stats import StatsEntry, StatsGenerator


class ElementType(StrEnum):
    CT = "CT"
    SW = "SW"


@dataclass(frozen=True)
class ElementMetadata:
    """Data related to a DNK element"""

    # id of the parent network component being modeled, e.g. multiple DNK
    # elements may model different parts of the same switch
    pID: int
    pType: ElementType  # type of parent component
    name: str = ""


class DNKModelError(Exception):
    pass


class DNKMaudeModel(StatsGenerator, ABC):
    @classmethod
    @abstractmethod
    def fromJson(cls, jsonStr: str) -> Self: ...

    @abstractmethod
    def getBranchCounts(self) -> str: ...

    @abstractmethod
    def getElementTerms(self) -> List[str]: ...

    @abstractmethod
    def getMaudeModuleName(self) -> str: ...

    @abstractmethod
    def getElementMetadataDict(self) -> dict[int, ElementMetadata]: ...

    def getStats(self) -> List[StatsEntry]:
        return [
            StatsEntry(
                "modelBranchCounts", "Network model branches", self.getBranchCounts()
            )
        ]
