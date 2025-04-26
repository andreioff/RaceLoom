# mypy: disable-error-code="import-untyped,no-any-unimported,misc"
from typing import List, Tuple

import maude
from src.generator.trace_generator import TraceGenerator
from src.generator.trace_tree import TraceTree
from src.generator.util import extractListTerms, extractTransData, getSort
from src.generator.worklist import Queue, Stack, WorkList
from src.maude_encoder import MaudeEncoder, MaudeModules
from src.maude_encoder import MaudeOps as mo
from src.maude_encoder import MaudeSorts as ms
from src.model.dnk_maude_model import DNKMaudeModel
from src.trace.node import TraceNode
from src.trace.transition import newTraceTransition
from src.trace.vector_clocks import newVectorClocks
from src.tracer_config import TracerConfig


class SequentialTraceGenerator(TraceGenerator):
    def __init__(
        self, config: TracerConfig, workList: WorkList[Tuple[str, str, TraceNode, int]]
    ):
        super().__init__(config)
        self.workList = workList

    def getMaudeImports(self) -> List[MaudeModules]:
        return [MaudeModules.HEAD_NORMAL_FORM]

    def _generateTraces(
        self, model: DNKMaudeModel, mod: maude.Module, depth: int
    ) -> TraceTree:
        startDnkExpr = MaudeEncoder.parallelSeq(model.getElementTerms())
        startVC = newVectorClocks(len(model.getElementTerms()))
        startNode = TraceNode.fromTuple(("", startVC))
        traceTree = TraceTree()
        traceTree.addNode(startNode)

        self.workList.reset()
        self.workList.append((startDnkExpr, mo.TRANS_TYPE_NONE, startNode, 0))
        while not self.workList.isEmpty():
            (dnkExpr, prevTransType, parentNode, d) = self.workList.pop()
            neighbors = self.__computeNeighbors(mod, dnkExpr, prevTransType)

            for prevTransType, transLabel, dnkExpr in neighbors:
                trans = newTraceTransition(transLabel)
                vc = trans.updateVC(parentNode.vectorClocks)
                node = TraceNode(trans, vc)
                traceTree.addNode(node, parentNode.id)
                if d + 1 < depth:
                    self.workList.append((dnkExpr, prevTransType, node, d + 1))
        return traceTree

    def __computeNeighbors(
        self, mod: maude.Module, dnkExpr: str, prevTransType: str
    ) -> List[Tuple[str, str, str]]:
        key = (dnkExpr, prevTransType)
        if key in self.cache:
            self.cacheStats.hits += 1
            return self.cache[key]

        term = mod.parseTerm(MaudeEncoder.hnfCall(0, dnkExpr, prevTransType))
        term.reduce()

        neighbors = extractListTerms(term, getSort(mod, ms.TDATA))
        result: List[Tuple[str, str, str]] = []
        for n in neighbors:
            (_, prevTransType, transLabel, dnkExpr) = extractTransData(n, mod)
            result.append((prevTransType, transLabel, dnkExpr))

        self.cache[key] = result
        self.cacheStats.misses += 1
        return result


class DFSTraceGenerator(SequentialTraceGenerator):
    def __init__(self, config: TracerConfig) -> None:
        super().__init__(config, Stack[Tuple[str, str, TraceNode, int]]())


class BFSTraceGenerator(SequentialTraceGenerator):
    def __init__(self, config: TracerConfig) -> None:
        super().__init__(config, Queue[Tuple[str, str, TraceNode, int]]())
