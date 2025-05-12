import os
from typing import List

from src.analyzer.traces_analyzer import TracesAnalyzer
from src.generator.trace_generator_factory import (TraceGenOption,
                                                   newTraceGenerator)
from src.generator.trace_tree import TraceTree
from src.KATch_comm import KATchComm
from src.model.dnk_maude_model import DNKMaudeModel
from src.stats import StatsEntry
from src.tracer_config import TracerConfig
from src.util import createDir, exportFile

_TRACES_FILE_NAME = "traces"
_HARMFUL_TRACES_DIR_NAME = "harmful_traces"
_HARMFUL_TRACES_RAW_DIR_NAME = "harmful_traces_raw"


class Tracer:
    def __init__(
        self, config: TracerConfig, genStrategy: TraceGenOption, dnkModel: DNKMaudeModel
    ) -> None:
        self.config = config
        self.dnkModel = dnkModel
        self.__traceGen = newTraceGenerator(genStrategy, config)
        self.__traceTree: TraceTree = TraceTree()
        self.__initTraceAnalyzer()

    def __initTraceAnalyzer(self) -> None:
        outputDirRaw = os.path.join(
            self.config.outputDirPath, _HARMFUL_TRACES_RAW_DIR_NAME
        )
        outputDirDOT = os.path.join(self.config.outputDirPath, _HARMFUL_TRACES_DIR_NAME)
        createDir(outputDirRaw)
        createDir(outputDirDOT)
        self.__katchComm = KATchComm(self.config.katchPath, self.config.outputDirPath)
        self.__traceAnalyzer = TracesAnalyzer(
            self.__katchComm, outputDirRaw, outputDirDOT
        )

    def generateTraces(self, depth: int) -> bool:
        self.__traceTree = self.__traceGen.run(self.dnkModel, depth)

        if self.__traceTree.traceCount() == 0:
            return False
        self.__writeTracesToFile()
        return True

    def __writeTracesToFile(self) -> None:
        tracesFilePath = os.path.join(
            self.config.outputDirPath,
            f"{_TRACES_FILE_NAME}_{self.config.inputFileName}.txt",
        )
        exportFile(
            tracesFilePath,
            os.linesep.join([str(t) for t in self.__traceTree.getTraceIterator()]),
        )

    def analyzeTraces(self) -> None:
        self.__traceAnalyzer.run(self.__traceTree, self.dnkModel.getElementsMetadata())

    def getTraceGenerationStats(self) -> List[StatsEntry]:
        return self.__traceGen.getStats()

    def getTraceAnalysisStats(self) -> List[StatsEntry]:
        return self.__katchComm.getStats() + self.__traceAnalyzer.getStats()

    def getTotalExecTime(self) -> float:
        return (
            self.__traceGen.getWrapperTotalExecTime()
            + self.__traceAnalyzer.getWrapperTotalExecTime()
        )
