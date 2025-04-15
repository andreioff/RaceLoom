from enum import StrEnum
from os import linesep
from typing import List, Tuple

from src.analyzer.trace_parser import TraceNode
from src.model.dnk_maude_model import ElementType
from src.util import splitIntoLines


class RaceType(StrEnum):
    SWCT = "SW-CT"
    CTCT = "CT-CT"


class ColorScheme(StrEnum):
    ERR_PRIMARY = "#FF2400"
    ERR_SECONDARY = "#FF9280"
    ACCENT = "#F2F4FB"
    NODE_BG = "#F2F4FB"
    EDGE = "#000000"


class HarmfulTrace:
    def __init__(
        self,
        nodes: List[TraceNode],
        elDict: dict[int, ElementType],
        srcNode: int,
        racingTrans: Tuple[int, int],
        racingElements: Tuple[int, int],
        raceType: RaceType,
    ) -> None:
        self.nodes = nodes
        self.elDict = elDict
        self.srcNode = srcNode
        self.racingTrans = racingTrans
        self.racingElements = racingElements
        self.raceType = raceType

    def toDOT(self) -> str:
        sb: List[str] = ["digraph g {"]
        for nodeId, node in enumerate(self.nodes):
            isSource: bool = nodeId == self.srcNode
            fillColor = self.__getNodeColor(node, isSource)
            sb.append(
                f"n{nodeId} [label=<{self.__getNodeLabel(node, isSource)}>, "
                + f'shape=rectangle, style=filled, fillcolor="{fillColor}"];'
            )
            if nodeId == 0:  # first node does not have a transition
                continue
            label = splitIntoLines(str(node.trans), 50, 10)
            edgeColor = (
                ColorScheme.ERR_PRIMARY
                if nodeId in self.racingTrans
                else ColorScheme.EDGE
            )
            penwidth = 2.0 if nodeId in self.racingTrans else 1.0
            sb.append(
                f'n{nodeId-1} -> n{nodeId} [label="{label}", '
                + f'color="{edgeColor}", penwidth={penwidth}];'
            )
        sb.append("}")  # close digraph
        return linesep.join(sb)

    def __getNodeColor(self, node: TraceNode, isSource: bool) -> str:
        if isSource:
            return ColorScheme.ERR_PRIMARY
        if len(node.getIncmpPosPairs()) > 0:
            return ColorScheme.ERR_SECONDARY
        return ColorScheme.NODE_BG

    def __getNodeLabel(self, node: TraceNode, isSource: bool) -> str:
        typeLabel = ""
        vcLabel = ""
        prefix = ""
        for i, vc in enumerate(node.vectorClocks):
            typeLabel += prefix + self.elDict[i]
            vcLabel += prefix
            if isSource and i in self.racingElements:
                vcLabel += f'<font color="{ColorScheme.ACCENT}">{vc}</font>'
            else:
                vcLabel += f"{vc}"
            prefix = ", "
        return typeLabel + "<br/>[" + vcLabel + "]"
