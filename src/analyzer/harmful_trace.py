from dataclasses import dataclass
from enum import StrEnum
from os import linesep
from typing import List

from src.model.dnk_maude_model import ElementMetadata
from src.trace.node import TraceNode
from src.util import indexInBounds, splitIntoLines


class RaceType(StrEnum):
    SW_SW = "SW-SW"
    CT_SW = "CT->SW"
    CT_SW_CT = "CT->SW<-CT"
    CT_CT_SW = "CT->CT->SW"


@dataclass(frozen=True)
class RacingNode:
    pos: int  # position of the node in its corresponding trace
    elPos: int  # which DNK element was part of the race
    netPolicy: str  # the re-constructed network policy of this node


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
        racingNodes: List[RacingNode],
        raceType: RaceType,
    ) -> None:
        self.nodes = nodes
        self.elsMetadata = elsMetadata
        self.racingNodes = racingNodes
        self.raceType = raceType
        self._validateRacingTransitionsDict()

    def _validateRacingTransitionsDict(self) -> None:
        for racingNode in self.racingNodes:
            if not indexInBounds(racingNode.pos, len(self.nodes)):
                raise ValueError(
                    f"Racing transition position {racingNode.pos} "
                    + "is out of bounds for the given nodes list."
                )
            if not indexInBounds(
                racingNode.elPos, len(self.nodes[racingNode.pos].vectorClocks)
            ):
                raise ValueError(
                    f"Element position {racingNode.elPos} is "
                    + "out of bounds for the given nodes list."
                )

    def toDOT(self) -> str:
        sb: List[str] = ["digraph g {"]
        racingNodePositions = [rn.pos for rn in self.racingNodes]
        for nodePos, node in enumerate(self.nodes):
            sb.append(
                f"n{nodePos} [label=<{self._getNodeLabel(node, nodePos)}>, "
                + f'shape=rectangle, style=filled, fillcolor="{ColorScheme.NODE_BG}"];'
            )
            if nodePos == 0:  # first node does not have a transition
                continue
            label = splitIntoLines(str(node.trans), 50, 10)
            racingNode = self._findRacingNode(nodePos)
            if racingNode is not None:
                label += linesep * 2 + "Reconstructed network policy:" + linesep
                label += splitIntoLines(racingNode.netPolicy, 50, 10)
            edgeColor = (
                ColorScheme.ERR_PRIMARY
                if nodePos in racingNodePositions
                else ColorScheme.EDGE
            )
            penwidth = 2.0 if nodePos in racingNodePositions else 1.0
            sb.append(
                f'n{nodePos-1} -> n{nodePos} [label="{label}", '
                + f'color="{edgeColor}", penwidth={penwidth}];'
            )
        sb.append("}")  # close digraph
        return linesep.join(sb)

    def _getNodeLabel(self, node: TraceNode, nodePos: int) -> str:
        elNames, vcLabel, prefix = "", "", ""
        racingNode = self._findRacingNode(nodePos)
        for i, metadata in enumerate(self.elsMetadata):
            vc = node.vectorClocks[i]
            elName = metadata.name
            if not elName:
                elName = metadata.pType
            elNames += prefix + elName
            vcLabel += prefix
            if racingNode is not None and i == racingNode.elPos:
                vcLabel += f'<font color="{ColorScheme.ERR_PRIMARY}">{vc}</font>'
            else:
                vcLabel += f"{vc}"
            prefix = ", "
        return elNames + "<br/>[" + vcLabel + "]"

    def _findRacingNode(self, nodePos: int) -> RacingNode | None:
        for rn in self.racingNodes:
            if rn.pos == nodePos:
                return rn
        return None
