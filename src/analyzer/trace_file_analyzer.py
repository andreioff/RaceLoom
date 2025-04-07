import os
from typing import Tuple, List

from src.analyzer.trace_analyzer import (
    TraceAnalyzer,
    TraceAnalyzerError,
    TransitionsChecker,
)
from src.analyzer.trace_parser import ParseError, TraceParser
from src.analyzer.harmful_trace import HarmfulTrace, RaceType
from src.KATch_comm import KATchComm
from src.model.dnk_maude_model import ElementType
from src.util import exportFile
from src.decorators.exec_time import PExecTimes, with_time_execution
from src.stats import StatsGenerator, StatsEntry

RAW_HARMFUL_TRACE_FILE_NAME = "harmful_trace_raw"
HARMFUL_TRACE_FILE_NAME = "harmful_trace"


class TraceFileAnalyzer(PExecTimes, StatsGenerator):
    """Class for reading and analyzing trace files."""

    def __init__(
        self, katchComm: KATchComm, outputDirRaw: str, outputDirDOT: str
    ) -> None:
        self.katchComm = katchComm
        self.outputDirRaw = outputDirRaw
        self.outputDirDOT = outputDirDOT
        self.execTimes: dict[str, float] = {}
        self.harmfulRacesCount = 0

    @with_time_execution
    def analyzeFile(self, traceFilePath: str, elDict: dict[int, ElementType]) -> None:
        """Parses and analyzes each trace in the given file (1 trace per line), and outputs every
        trace posing a harmful race in 2 ways: once as a file containing the raw trace and the information about
        the harmful race, and once as a DOT file."""
        traceFile = open(traceFilePath, "r", newline="\n")
        transChecker = TransitionsChecker(self.katchComm, elDict)
        lineCount = 0
        for line in traceFile:
            traceStr = line.strip().replace("\\", "")
            htrace = self.__analyzeTrace(lineCount, traceStr, transChecker, elDict)
            if htrace is not None:
                self.harmfulRacesCount += 1
                self.__writeRawTraceToFile(
                    traceStr, htrace.racingTrans, htrace.raceType
                )
                self.__writeDOTTraceToFile(htrace.toDOT())
            lineCount += 1
        traceFile.close()
        self.__printUnexpTransMsg(transChecker)

    def __analyzeTrace(
        self,
        lineNr: int,
        traceStr: str,
        transChecker: TransitionsChecker,
        elDict: dict[int, ElementType],
    ) -> HarmfulTrace | None:
        try:
            trace = TraceParser.parse(traceStr)
            ta = TraceAnalyzer(
                transChecker,
                elDict,
                trace,
            )
            return ta.analyze()
        except SyntaxError:
            print(
                f"On line {
                    lineNr}: Argument 'traceStr' does not contain valid Python3 syntax."
            )
        except ParseError as e:
            print(f"On line {lineNr}: {e}")
        except TraceAnalyzerError as e:
            print(f"On line {lineNr}: {e}")

        return None

    def __writeRawTraceToFile(
        self, traceStr: str, transPos: Tuple[int, int], raceType: RaceType
    ) -> None:
        content = f"{traceStr}\n{raceType}\n{transPos[0]},{transPos[1]}"
        fileName = f"{RAW_HARMFUL_TRACE_FILE_NAME}_{
            self.harmfulRacesCount}.txt"
        exportFile(os.path.join(self.outputDirRaw, fileName), content)

    def __writeDOTTraceToFile(self, traceDOT: str) -> None:
        fileName = f"{HARMFUL_TRACE_FILE_NAME}_{self.harmfulRacesCount}.gv"
        exportFile(os.path.join(self.outputDirDOT, fileName), traceDOT)

    def __printUnexpTransMsg(self, transChecker: TransitionsChecker) -> None:
        unexpTransPairs = transChecker.getUnexpectedTransPairs("\t")
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

    def getStats(self) -> List[StatsEntry]:
        return [
            StatsEntry("harmfulRaces", "Harmful races found", self.harmfulRacesCount),
            StatsEntry(
                "traceAnalyzerExecTime",
                "Trace Analyzer execution time",
                self.getTotalExecTime(),
            ),
        ]
