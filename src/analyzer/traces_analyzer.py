import os
from typing import List

from src.analyzer.harmful_trace import HarmfulTrace
from src.analyzer.trace_analyzer import TraceAnalyzer, TransitionsChecker
from src.decorators.exec_time import PExecTimes, with_time_execution
from src.generator.trace_tree import TraceTree
from src.KATch_comm import KATchComm
from src.model.dnk_maude_model import ElementMetadata
from src.stats import StatsEntry, StatsGenerator
from src.trace.node import TraceNode
from src.util import exportFile

RAW_HARMFUL_TRACE_FILE_NAME = "harmful_trace_raw"
HARMFUL_TRACE_FILE_NAME = "harmful_trace"


def _hasExistingRace(trace: List[TraceNode]) -> bool:
    racingNodes: List[TraceNode] = []
    for node in trace:
        if not node.isPartOfRace():
            continue
        racingNodes.append(node)
    for i in range(len(racingNodes)):
        for j in range(len(racingNodes)):
            if i >= j:
                continue
            if racingNodes[i].isRacingWith(racingNodes[j].id):
                return True
    return False


def _markRacingNodes(trace: List[TraceNode], nodePos: List[int]) -> None:
    for p1 in nodePos:
        for p2 in nodePos:
            if p1 == p2:
                continue
            trace[p1].addRacingNode(trace[p2].id)
            trace[p2].addRacingNode(trace[p1].id)


class TracesAnalyzer(PExecTimes, StatsGenerator):
    """Class analyzing traces"""

    def __init__(
        self, katchComm: KATchComm, outputDirRaw: str, outputDirDOT: str
    ) -> None:
        self.katchComm = katchComm
        self.outputDirRaw = outputDirRaw
        self.outputDirDOT = outputDirDOT
        self.execTimes: dict[str, float] = {}
        self.harmfulRacesCount = 0

    @with_time_execution
    def run(self, traceTree: TraceTree, elsMetadata: List[ElementMetadata]) -> None:
        """Analyzes each trace in the given list, and outputs every trace posing
        a harmful race in 2 ways: once as a file containing the raw trace and the
        information about the harmful race, and once as a DOT file."""
        transChecker = TransitionsChecker(self.katchComm, elsMetadata)
        ta = TraceAnalyzer(transChecker, elsMetadata)
        for trace in traceTree.getTraceIterator():
            if _hasExistingRace(trace):
                continue
            htrace = ta.analyze(trace)
            if htrace is None:
                continue
            _markRacingNodes(trace, list(htrace.racingTransToEls.keys()))
            self.harmfulRacesCount += 1
            self.__writeRawTraceToFile(htrace)
            self.__writeDOTTraceToFile(htrace.toDOT(), htrace.raceType)
        self.__printUnexpTransMsg(transChecker)
        self.__printSkippedRaces(ta)

    def __writeRawTraceToFile(self, htrace: HarmfulTrace) -> None:
        content = f"{htrace.nodes}\n{htrace.raceType}\n" + ",".join(
            [f"(trans: {t}, el: {el})" for t, el in htrace.racingTransToEls.items()]
        )
        fileName = f"{RAW_HARMFUL_TRACE_FILE_NAME}_{
            self.harmfulRacesCount}_{htrace.raceType}.txt"
        exportFile(os.path.join(self.outputDirRaw, fileName), content)

    def __writeDOTTraceToFile(self, traceDOT: str, raceType: str) -> None:
        fileName = f"{HARMFUL_TRACE_FILE_NAME}_{self.harmfulRacesCount}_{raceType}.gv"
        exportFile(os.path.join(self.outputDirDOT, fileName), traceDOT)

    def __printUnexpTransMsg(self, transChecker: TransitionsChecker) -> None:
        unexpTransPairs = transChecker.getUnexpectedTransPairsStr("\t")
        if not unexpTransPairs:
            return
        print(
            "WARNING! Pairs of unexpected transition "
            + "types were found during analysis:"
        )
        print(unexpTransPairs)
        print(
            "This means a race occured between 2 transition types for which "
            + "no analysis behavior was programed."
        )
        print("Note: the order of the transitions matters!")

    def __printSkippedRaces(self, ta: TraceAnalyzer) -> None:
        skippedRaces = ta.getSkippedRacesStr("\t")
        if not skippedRaces:
            return
        print("Skipped races:")
        print(skippedRaces)

    def getStats(self) -> List[StatsEntry]:
        return [
            StatsEntry("harmfulRaces", "Harmful races found", self.harmfulRacesCount),
            StatsEntry(
                "traceAnalyzerExecTime",
                "Trace Analyzer execution time",
                self.getTotalExecTime(),
            ),
        ]
