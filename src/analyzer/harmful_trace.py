from enum import StrEnum
from os import linesep
from typing import List

from src.model.dnk_maude_model import ElementMetadata
from src.trace.node import TraceNode
from src.util import splitIntoLines, indexInBounds


class RaceType(StrEnum):
    SWSW = "SW-SW"
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
        elsMetadata: List[ElementMetadata],
        racingTransToEls: dict[int, int],
        raceType: RaceType,
    ) -> None:
        self.nodes = nodes
        self.elsMetadata = elsMetadata
        self.racingTransToEls = racingTransToEls
        self.raceType = raceType
        self._validateRacingTransitionsDict()

    def _validateRacingTransitionsDict(self) -> None:
        for tPos, elPos in self.racingTransToEls.items():
            if not indexInBounds(tPos, len(self.nodes)):
                raise ValueError(
                    f"Racing transition position {tPos} is out of bounds for the given nodes list."
                )
            if not indexInBounds(elPos, len(self.nodes[tPos].vectorClocks)):
                raise ValueError(
                    f"Element position {elPos} is out of bounds for the given nodes list."
                )

    def toDOT(self) -> str:
        sb: List[str] = ["digraph g {"]
        for nodePos, node in enumerate(self.nodes):
            sb.append(
                f"n{nodePos} [label=<{self.__getNodeLabel(node, nodePos)}>, "
                + f'shape=rectangle, style=filled, fillcolor="{ColorScheme.NODE_BG}"];'
            )
            if nodePos == 0:  # first node does not have a transition
                continue
            label = splitIntoLines(str(node.trans), 50, 10)
            edgeColor = (
                ColorScheme.ERR_PRIMARY
                if nodePos in self.racingTransToEls
                else ColorScheme.EDGE
            )
            penwidth = 2.0 if nodePos in self.racingTransToEls else 1.0
            sb.append(
                f'n{nodePos-1} -> n{nodePos} [label="{label}", '
                + f'color="{edgeColor}", penwidth={penwidth}];'
            )
        sb.append("}")  # close digraph
        return linesep.join(sb)

    def __getNodeLabel(self, node: TraceNode, nodePos: int) -> str:
        elNames, vcLabel, prefix = "", "", ""
        for i, metadata in enumerate(self.elsMetadata):
            vc = node.vectorClocks[i]
            elName = metadata.name
            if not elName:
                elName = metadata.pType
            elNames += prefix + elName
            vcLabel += prefix
            if i == self.racingTransToEls.get(nodePos, -1):
                vcLabel += f'<font color="{ColorScheme.ERR_PRIMARY}">{vc}</font>'
            else:
                vcLabel += f"{vc}"
            prefix = ", "
        return elNames + "<br/>[" + vcLabel + "]"
