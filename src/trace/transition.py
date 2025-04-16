import re
from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import List, Self

from src.errors import ParseError
from src.trace.vector_clocks import incrementVC, transferVC


@dataclass(frozen=True)
class ITransition(ABC):
    policy: str

    @abstractmethod
    def isModifyingVCPos(self, pos: int) -> bool: ...

    @abstractmethod
    def updateVC(self, vc: List[List[int]]) -> List[List[int]]: ...


@dataclass(frozen=True)
class TraceTransition(ITransition):
    def __init__(self) -> None:
        super().__init__("")

    def isModifyingVCPos(self, pos: int) -> bool:
        return False

    def updateVC(self, vcs: List[List[int]]) -> List[List[int]]:
        return vcs

    def __str__(self) -> str:
        return ""


@dataclass(frozen=True)
class PktProcTrans(ITransition):
    swPos: int

    def isModifyingVCPos(self, pos: int) -> bool:
        return self.swPos == pos

    @classmethod
    def fromStr(cls, s: str) -> Self:
        res = re.search(r"proc\('([^']*)',([0-9]+)\)", s)
        if res is None:
            raise ParseError(f"'{s}' is not a valid packet processing transition")

        t = cls(str(res.group(1)), int(res.group(2)))
        return t

    def updateVC(self, vcs: List[List[int]]) -> List[List[int]]:
        return incrementVC(vcs, self.swPos)

    def __str__(self) -> str:
        return f"proc('{self.policy}', {self.swPos})"


@dataclass(frozen=True)
class RcfgTrans(ITransition):
    srcPos: int
    dstPos: int
    channel: str

    def isModifyingVCPos(self, pos: int) -> bool:
        return self.srcPos == pos or self.dstPos == pos

    @classmethod
    def fromStr(cls, s: str) -> Self:
        res = re.search(r"rcfg\(([^,]*), '([^']*)', ([0-9]+), ([0-9]+)\)", s)
        if res is None:
            raise ParseError(f"'{s}' is not a valid reconfiguration transition")

        t = cls(
            str(res.group(2)),
            int(res.group(3)),
            int(res.group(4)),
            str(res.group(1)),
        )
        return t

    def updateVC(self, vcs: List[List[int]]) -> List[List[int]]:
        return transferVC(vcs, self.srcPos, self.dstPos)

    def __str__(self) -> str:
        return f"rcfg({self.channel}, '{self.policy}', {self.srcPos}, {self.dstPos})"


def newTraceTransition(transStr: str) -> ITransition:
    if transStr[:4] == "proc":
        return PktProcTrans.fromStr(transStr)
    if transStr[:4] == "rcfg":
        return RcfgTrans.fromStr(transStr)
    return TraceTransition()
