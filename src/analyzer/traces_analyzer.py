import os
from typing import List

from src.analyzer.harmful_trace import HarmfulTrace
from src.analyzer.trace_analyzer import (TraceAnalyzer, TraceAnalyzerError,
                                         TransitionsChecker)
from src.decorators.exec_time import PExecTimes, with_time_execution
from src.KATch_comm import KATchComm
from src.model.dnk_maude_model import ElementMetadata
from src.stats import StatsEntry, StatsGenerator
from src.trace.node import TraceNode
from src.util import exportFile

RAW_HARMFUL_TRACE_FILE_NAME = "harmful_trace_raw"
HARMFUL_TRACE_FILE_NAME = "harmful_trace"


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
    def analyzeFile(
        self, traces: List[List[TraceNode]], elDict: dict[int, ElementMetadata]
    ) -> None:
        """Analyzes each trace in the given list, and outputs every trace posing
        a harmful race in 2 ways: once as a file containing the raw trace and the
        information about the harmful race, and once as a DOT file."""
        transChecker = TransitionsChecker(self.katchComm, elDict)
        ta = TraceAnalyzer(transChecker, elDict)
        for trace in traces:
            htrace = ta.analyze(trace)
            if htrace is None:
                continue
            self.harmfulRacesCount += 1
            self.__writeRawTraceToFile(htrace)
            self.__writeDOTTraceToFile(htrace.toDOT(), htrace.raceType)
        self.__printUnexpTransMsg(transChecker)
        self.__printSkippedRaces(ta)

    def __writeRawTraceToFile(self, htrace: HarmfulTrace) -> None:
        content = (
            f"{htrace.nodes}\n{htrace.raceType}\n"
            + f"{htrace.racingTrans[0]},{htrace.racingTrans[1]}"
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
