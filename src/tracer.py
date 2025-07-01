import os
from typing import List

from src.analyzer.harmful_trace import RaceType
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
        self,
        config: TracerConfig,
        genStrategy: TraceGenOption,
        dnkModel: DNKMaudeModel,
        safetyProps: dict[RaceType, str],
    ) -> None:
        self.config = config
        self.dnkModel = dnkModel
        self.safetyProps = safetyProps
        self._traceGen = newTraceGenerator(genStrategy, config)
        self._traceTree: TraceTree = TraceTree(self.dnkModel)
        self._initTraceAnalyzer()

    def _initTraceAnalyzer(self) -> None:
        outputDirRaw = os.path.join(
            self.config.outputDirPath, _HARMFUL_TRACES_RAW_DIR_NAME
        )
        outputDirDOT = os.path.join(self.config.outputDirPath, _HARMFUL_TRACES_DIR_NAME)
        createDir(outputDirRaw)
        createDir(outputDirDOT)
        self._katchComm = KATchComm(self.config.katchPath, self.config.outputDirPath)
        self._traceAnalyzer = TracesAnalyzer(
            self._katchComm, self.safetyProps, outputDirRaw, outputDirDOT
        )

    def generateTraces(self, depth: int) -> bool:
        self._traceTree = self._traceGen.run(self.dnkModel, depth)

        if self._traceTree.traceCount() == 0:
            return False
        return True

    def analyzeTraces(self) -> None:
        self._traceAnalyzer.run(self._traceTree, self.dnkModel.getElementsMetadata())

    def getTraceGenerationStats(self) -> List[StatsEntry]:
        return self._traceGen.getStats()

    def getTraceAnalysisStats(self) -> List[StatsEntry]:
        return self._katchComm.getStats() + self._traceAnalyzer.getStats()

    def getTotalExecTime(self) -> float:
        return (
            self._traceGen.getWrapperTotalExecTime()
            + self._traceAnalyzer.getWrapperTotalExecTime()
        )
