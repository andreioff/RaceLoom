from src.analyzer.trace_parser import TraceNode
from typing import List, Tuple
from src.analyzer.trace_to_dot import traceToDOT
from enum import StrEnum
from src.model.dnk_maude_model import ElementType


class RaceType(StrEnum):
    SWCT = "SW-CT"
    CTCT = "CT-CT"


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

        self.nodes[srcNode].racingElements = racingElements
        self.nodes[racingTrans[0]].trans.causesHarmfulRace = True
        self.nodes[racingTrans[1]].trans.causesHarmfulRace = True

    def toDOT(self) -> str:
        return traceToDOT(self.nodes, self.elDict)
