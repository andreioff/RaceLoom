# mypy: disable-error-code="import-untyped,no-any-unimported,misc"

from typing import Dict, List, Tuple

import maude
from src.generator.trace_generator import TraceGenerator
from src.generator.trace_tree import TraceTree
from src.generator.util import extractListTerms, extractTransData, getSort
from src.maude_encoder import MaudeEncoder, MaudeModules
from src.maude_encoder import MaudeOps as mo
from src.maude_encoder import MaudeSorts as ms
from src.model.dnk_maude_model import DNKMaudeModel
from src.trace.node import TraceNode
from src.trace.transition import newTraceTransition
from src.trace.vector_clocks import newVectorClocks
from src.tracer_config import TracerConfig
from src.util import uniformSplit


class ParallelBFSTraceGenerator(TraceGenerator):
    def __init__(self, config: TracerConfig) -> None:
        super().__init__(config)
        self.traceTree = TraceTree()

    def reset(self) -> None:
        super().reset()
        self.traceTree = TraceTree()

    def getMaudeImports(self) -> List[MaudeModules]:
        return [MaudeModules.PARALLEL_HEAD_NORMAL_FORM]

    def _generateTraces(
        self, model: DNKMaudeModel, mod: maude.Module, depth: int
    ) -> TraceTree:
        self.reset()
        startDnkExpr = MaudeEncoder.parallelSeq(model.getElementTerms())
        startVC = newVectorClocks(len(model.getElementTerms()))
        startNode = TraceNode.fromTuple(("", startVC))
        self.traceTree.addNode(startNode)

        # currNode to (dnkExpr, previous transition type)
        currLayer: dict[TraceNode, Tuple[str, str]] = {
            startNode: (startDnkExpr, mo.TRANS_TYPE_NONE)
        }
        while currLayer and depth > 0:
            nodeToIndex, uniqueDNKData = self.__getUniqueDNKData(currLayer)
            results: List[Tuple[List[Tuple[str, str, str]], bool]] = [
                ([], False) for _ in range(len(uniqueDNKData))
            ]  # list of (results, is computed)
            self.__addCachedResults(uniqueDNKData, results)
            self.__addNextTransitions(mod, uniqueDNKData, results)

            nextLayer: dict[TraceNode, Tuple[str, str]] = {}
            for parentNode, index in nodeToIndex.items():
                for prevTransType, transLabel, dnkExpr in results[index][0]:
                    node = self.__addNewNode(transLabel, parentNode)
                    nextLayer[node] = (dnkExpr, prevTransType)
            currLayer = nextLayer
            depth -= 1

        return self.traceTree

    def __addNewNode(self, transLabel: str, parentNode: TraceNode) -> TraceNode:
        trans = newTraceTransition(transLabel)
        vc = trans.updateVC(parentNode.vectorClocks)
        node = TraceNode(trans, vc)
        self.traceTree.addNode(node, parentNode.id)
        return node

    def __addCachedResults(
        self,
        dnkData: List[Tuple[str, str]],
        results: List[Tuple[List[Tuple[str, str, str]], bool]],
    ) -> None:
        for i, entry in enumerate(dnkData):
            cachedNeighbors = self.cache.get(entry, [])
            if not cachedNeighbors:
                self.cacheStats.misses += 1
                continue
            self.cacheStats.hits += 1
            results[i] = (cachedNeighbors, True)

    def __getUniqueDNKData(
        self, layer: dict[TraceNode, Tuple[str, str]]
    ) -> Tuple[dict[TraceNode, int], List[Tuple[str, str]]]:
        if not layer:
            return {}, []
        nodeToIndex: dict[TraceNode, int] = {}
        dnkDataToIndex: dict[Tuple[str, str], int] = {}
        nextIndex = 0
        for node, dnkTup in layer.items():
            i = dnkDataToIndex.get(dnkTup, -1)
            if i == -1:
                dnkDataToIndex[dnkTup] = nextIndex
                nodeToIndex[node] = nextIndex
                nextIndex += 1
                continue
            nodeToIndex[node] = i
        return nodeToIndex, list(dnkDataToIndex.keys())

    def __addNextTransitions(
        self,
        mod: maude.Module,
        dnkData: List[Tuple[str, str]],
        results: List[Tuple[List[Tuple[str, str, str]], bool]],
    ) -> None:
        inputTerms = self.__makeMaudeInput(dnkData, results)
        # Workers cannot be initialized separately because the meta interpreters
        # are deleted by the Maude library as soon as the erewrite call is done.
        # So we have to create the meta-interpreters everytime we process a layer
        workersConfig = MaudeEncoder.metaInterpretersInitCall(self.config.threads)

        term = mod.parseTerm(MaudeEncoder.parallelHnfCall(workersConfig, inputTerms))
        (res, _) = term.erewrite()

        neighbors = extractListTerms(res, getSort(mod, ms.TDATA))
        for n in neighbors:
            (index, transType, transLabel, dnkExpr) = extractTransData(n, mod)
            results[index][0].append((transType, transLabel, dnkExpr))
        for i, entry in enumerate(dnkData):
            self.cache.setdefault(entry, results[i][0])
            results[i] = (results[i][0], True)

    def __makeMaudeInput(
        self,
        dnkData: List[Tuple[str, str]],
        results: List[Tuple[List[Tuple[str, str, str]], bool]],
    ) -> List[str]:
        if not dnkData:
            return []
        inputs: List[str] = []
        for i, t in enumerate(dnkData):
            if results[i][1]:
                continue
            inputs.append(MaudeEncoder.hnfInput(i, t[1], t[0]))
        splitInputs = uniformSplit(inputs, self.config.threads)
        return [MaudeEncoder.parallelHnfWorkerInputTerm(li) for li in splitInputs]
