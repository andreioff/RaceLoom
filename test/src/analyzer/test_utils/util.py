from dataclasses import dataclass
from typing import List, Self, Tuple

import src.trace.vector_clocks as vcs
from src.analyzer.harmful_trace import RaceType, RacingNode
from src.model.dnk_maude_model import ElementMetadata, ElementType
from src.trace.node import TraceNode
from src.trace.transition import PktProcTrans, RcfgTrans, TraceTransition
from src.util import DyNetKATSymbols as sym


def raceSafetyDict(safetyProp: str) -> dict[RaceType, str]:
    return {
        RaceType.CT_SW: safetyProp,
        RaceType.CT_SW_CT: safetyProp,
        RaceType.CT_CT_SW: safetyProp,
    }


@dataclass
class SafetyPropertyData:
    prop: str
    passingFlowRules: List[str]
    failingFlowRules: List[str]


@dataclass
class TraceData:
    metadata: List[ElementMetadata]
    trace: List[TraceNode]
    safetyProp: str
    racingNodes: List[RacingNode]


class Metadata:
    def __init__(self) -> None:
        self.elements: List[ElementMetadata] = []

    def addBigSw(
        self,
        channels: List[List[str]] | None = None,
        initialFts: List[str] | None = None,
    ) -> Self:
        """Channels: List of channels for every inner switch.
        Must not repeat between the inner switches!"""
        metadata = ElementMetadata(
            pID=len(self.elements),
            pType=ElementType.SW,
            switchChannels=channels or [],
            initialFTs=initialFts or [sym.ZERO for _chs in channels],
        )
        self.elements.append(metadata)
        return self

    def addCt(self) -> Self:
        metadata = ElementMetadata(
            pID=len(self.elements),
            pType=ElementType.CT,
        )
        self.elements.append(metadata)
        return self

    def getSwChannel(self, bigSwIndx: int, innerSwIndx: int, chIndex: int = 0) -> str:
        return self.elements[bigSwIndx].switchChannels[innerSwIndx][0]

    def buildBigSwPolicy(self, bigSwIndx: int, *changedFts: Tuple[int, str]) -> str:
        fts = self.elements[bigSwIndx].initialFTs.copy()
        for pos, newFt in changedFts:
            fts[pos] = newFt
        link = self.elements[bigSwIndx].link
        concatFts = f" {sym.OR} ".join(fts)
        netPol = f"({concatFts}) {sym.AND} ({link})"
        return f"({netPol}) {sym.AND} ({netPol}){sym.STAR}"


class TraceBuilder:
    def __init__(self, metadata: Metadata) -> None:
        self.metadata: Metadata = metadata
        self.vectorClocks: List[List[int]] = vcs.newVectorClocks(len(metadata.elements))
        self.trace: List[TraceNode] = []

    def addStartNode(self) -> Self:
        self.trace.append(TraceNode(TraceTransition(), self.vectorClocks))
        return self

    def forward(self, policy: str, bigSwIndx: int) -> Self:
        self.vectorClocks = vcs.incrementVC(self.vectorClocks, bigSwIndx)
        self.trace.append(TraceNode(PktProcTrans(policy, bigSwIndx), self.vectorClocks))
        return self

    def rcfgSw(
        self, policy: str, srcIndx: int, swIndx: int, chIndx: Tuple[int, int] = (0, 0)
    ) -> Self:
        self.vectorClocks = vcs.transferVC(self.vectorClocks, srcIndx, swIndx)
        ch = self.metadata.getSwChannel(swIndx, *chIndx)
        self.trace.append(
            TraceNode(RcfgTrans(policy, srcIndx, swIndx, ch), self.vectorClocks)
        )
        return self

    def rcfgCt(self, policy: str, srcIndx: int, targetIndx: int, ch: str) -> Self:
        self.vectorClocks = vcs.transferVC(self.vectorClocks, srcIndx, targetIndx)
        self.trace.append(
            TraceNode(RcfgTrans(policy, srcIndx, targetIndx, ch), self.vectorClocks)
        )
        return self

    def build(self) -> List[TraceNode]:
        return self.trace
