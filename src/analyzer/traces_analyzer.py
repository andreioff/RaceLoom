import os
from typing import List, Tuple

from src.analyzer.harmful_trace import HarmfulTrace, RaceType
from src.analyzer.trace_analyzer import TraceAnalyzer
from src.analyzer.transition_checker import TransitionsChecker
from src.decorators.exec_time import ExecTimes, with_time_execution
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
            if racingNodes[i].isRacingWith(racingNodes[j]):
                return True
    return False


def _markRacingNodes(trace: List[TraceNode], nodePos: List[int]) -> None:
    for p1 in nodePos:
        for p2 in nodePos:
            if p1 >= p2:
                continue
            trace[p1].addRacingNode(trace[p2])


def _getSoonerRace(
    htrace1: HarmfulTrace,
    htrace2: HarmfulTrace,
) -> HarmfulTrace:
    transIndicies1 = tuple(rn.pos for rn in htrace1.racingNodes)
    transIndicies2 = tuple(rn.pos for rn in htrace2.racingNodes)
    if transIndicies1 <= transIndicies2:
        return htrace1
    return htrace2


class TracesAnalyzer(ExecTimes, StatsGenerator):
    """Class analyzing traces"""

    def __init__(
        self,
        katchComm: KATchComm,
        safetyProps: dict[RaceType, str],
        outputDirRaw: str,
        outputDirDOT: str,
    ) -> None:
        ExecTimes.__init__(self)
        StatsGenerator.__init__(self)
        self.katchComm = katchComm
        self.safetyProps = safetyProps
        self.outputDirRaw = outputDirRaw
        self.outputDirDOT = outputDirDOT
        self.harmfulRacesCount = 0

    @with_time_execution
    def run(self, traceTree: TraceTree, elsMetadata: List[ElementMetadata]) -> None:
        """Analyzes each trace in the given list, and outputs every trace posing
        a harmful race in 2 ways: once as a file containing the raw trace and the
        information about the harmful race, and once as a DOT file."""
        transChecker = TransitionsChecker(self.katchComm, self.safetyProps, elsMetadata)
        ta = TraceAnalyzer(transChecker, elsMetadata)
        htraces: List[HarmfulTrace] = []
        for trace in traceTree.getTraceIterator():
            if _hasExistingRace(trace):
                continue
            htrace = ta.analyze(trace)
            if htrace is None:
                continue
            htraces.append(htrace)
            _markRacingNodes(trace, [rn.pos for rn in htrace.racingNodes])
        htraces = self.__filterHarmfulRaces(htraces)
        self.harmfulRacesCount = len(htraces)
        self.__writeHarmfulTracesToFile(htraces)
        self.__printSkippedRaces(transChecker)

    def __filterHarmfulRaces(
        self, harmfulTraces: List[HarmfulTrace]
    ) -> List[HarmfulTrace]:
        # transition strings tuple to HarmfulTrace
        filtered: dict[Tuple[str, ...], HarmfulTrace] = {}
        for htrace in harmfulTraces:
            transIndicies = [rn.pos for rn in htrace.racingNodes]
            key = tuple(str(htrace.nodes[i].trans) for i in transIndicies)
            currBest = filtered.get(key, None)
            if currBest is None:
                filtered[key] = htrace
                continue
            currBest = _getSoonerRace(currBest, htrace)
            filtered[key] = currBest
        return list(filtered.values())

    def __writeHarmfulTracesToFile(self, htraces: List[HarmfulTrace]) -> None:
        for i, htrace in enumerate(htraces):
            self.__writeRawTraceToFile(htrace, i)
            self.__writeDOTTraceToFile(htrace.toDOT(), htrace.raceType, i)

    def __writeRawTraceToFile(self, htrace: HarmfulTrace, traceNumber: int) -> None:
        content = f"{htrace.nodes}\n{htrace.raceType}\n" + os.linesep.join(
            [
                f'(trans: {rn.pos}, el: {rn.elPos}, networkPolicy: "{rn.netPolicy}")'
                for rn in htrace.racingNodes
            ]
        )
        fileName = f"{RAW_HARMFUL_TRACE_FILE_NAME}_{traceNumber}_{htrace.raceType}.txt"
        exportFile(os.path.join(self.outputDirRaw, fileName), content)

    def __writeDOTTraceToFile(
        self, traceDOT: str, raceType: str, traceNumber: int
    ) -> None:
        fileName = f"{HARMFUL_TRACE_FILE_NAME}_{traceNumber}_{raceType}.gv"
        exportFile(os.path.join(self.outputDirDOT, fileName), traceDOT)

    def __printSkippedRaces(self, transChecker: TransitionsChecker) -> None:
        skippedRaces = transChecker.getSkippedRacesStr("\t")
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
                self.getWrapperTotalExecTime(),
            ),
        ]
