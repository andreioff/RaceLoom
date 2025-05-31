import os
from typing import List

from src.analyzer.traces_analyzer import TracesAnalyzer
from src.generator.trace_generator_factory import (TraceGenOption,
                                                   newTraceGenerator)
from src.generator.trace_tree import TraceTree
from src.KATch_comm import KATchComm
from src.model.dnk_maude_model import DNKMaudeModel, ElementType
from src.stats import StatsEntry
from src.trace.transition import RcfgTrans
from src.tracer_config import TracerConfig
from src.util import DyNetKATSymbols as sym
from src.util import createDir, exportFile

_TRACES_FILE_NAME = "traces"
_HARMFUL_TRACES_DIR_NAME = "harmful_traces"
_HARMFUL_TRACES_RAW_DIR_NAME = "harmful_traces_raw"


class TracerError(Exception):
    pass


def _buildNetworkPolicy(fts: List[str], link: str) -> str:
    if not fts:
        return sym.ZERO
    ftsStr = f" {sym.OR} ".join(fts)
    oneStepStr = f"({ftsStr}) {sym.AND} ({link})"
    return f"({oneStepStr}) {sym.AND} ({oneStepStr}){sym.STAR}"


def _reconstructRcfgs(traceTree: TraceTree) -> None:
    """Iterates through all traces in the tree and applies the update of any
    switch reconfiguration to the flow table of the target switch up until that
    point, then assigns the policy of the reconfiguration to the result"""
    dm = traceTree.dnkModel
    nodeIdToOldPolicy: dict[int, str] = {}
    for trace in traceTree.getTraceIterator():
        # tracks the flow tables of all elements throughout the trace
        currNet = [metad.initialFTs.copy() for metad in dm.elsMetadata]
        for node in trace:
            # anything that is not a reconfiguration to a switch is skipped
            if not isinstance(node.trans, RcfgTrans):
                continue
            metad = dm.elsMetadata[node.trans.dstPos]
            if metad.pType != ElementType.SW:
                continue
            fts = currNet[node.trans.dstPos]
            swToModify = metad.findSwitchIndex(node.trans.channel)
            if swToModify == -1:
                raise TracerError(
                    "Could not match network switch based on rcfg channel"
                )
            # apply the reconfiguration to the target element and store the result
            oldPolicy = nodeIdToOldPolicy.get(node.id, None)
            if oldPolicy is not None:
                fts[swToModify] = oldPolicy
                continue
            fts[swToModify] = node.trans.policy
            nodeIdToOldPolicy[node.id] = node.trans.policy
            node.trans.setPolicy(_buildNetworkPolicy(fts, metad.link))


class Tracer:
    def __init__(
        self, config: TracerConfig, genStrategy: TraceGenOption, dnkModel: DNKMaudeModel
    ) -> None:
        self.config = config
        self.dnkModel = dnkModel
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
            self._katchComm, outputDirRaw, outputDirDOT
        )

    def generateTraces(self, depth: int) -> bool:
        self._traceTree = self._traceGen.run(self.dnkModel, depth)
        _reconstructRcfgs(self._traceTree)

        if self._traceTree.traceCount() == 0:
            return False
        self._writeTracesToFile()
        return True

    def _writeTracesToFile(self) -> None:
        tracesFilePath = os.path.join(
            self.config.outputDirPath,
            f"{_TRACES_FILE_NAME}_{self.config.inputFileName}.txt",
        )
        exportFile(
            tracesFilePath,
            os.linesep.join([str(t) for t in self._traceTree.getTraceIterator()]),
        )

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
