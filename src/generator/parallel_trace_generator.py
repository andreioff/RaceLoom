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

        # dnkExpr, prevTransType, currNode
        currLayer: List[Tuple[str, str, TraceNode]] = [
            (startDnkExpr, mo.TRANS_TYPE_NONE, startNode)
        ]
        while currLayer and depth > 0:
            nextLayer, remLayer = self.__appendCachedNodes(currLayer)
            results = self.__computeNeighbors(mod, remLayer)

            for _, _, parentNode in remLayer:
                neighbors = results.get(parentNode.id, None)
                if neighbors is None:
                    continue
                for prevTransType, transLabel, dnkExpr in neighbors:
                    node = self.__addNewNode(transLabel, parentNode)
                    nextLayer.append((dnkExpr, prevTransType, node))
            currLayer = nextLayer
            depth -= 1

        return self.traceTree

    def __addNewNode(self, transLabel: str, parentNode: TraceNode) -> TraceNode:
        trans = newTraceTransition(transLabel)
        vc = trans.updateVC(parentNode.vectorClocks)
        node = TraceNode(trans, vc)
        self.traceTree.addNode(node, parentNode.id)
        return node

    def __appendCachedNodes(
        self, layer: List[Tuple[str, str, TraceNode]]
    ) -> Tuple[List[Tuple[str, str, TraceNode]], List[Tuple[str, str, TraceNode]]]:
        nextLayer: List[Tuple[str, str, TraceNode]] = []
        remLayer: List[Tuple[str, str, TraceNode]] = []
        for data in layer:
            currDnkExpr, prevTransType, parentNode = data
            cachedNeighbors = self.cache.get((currDnkExpr, prevTransType), [])
            if not cachedNeighbors:
                remLayer.append(data)
                self.cacheStats.misses += 1
                continue
            self.cacheStats.hits += 1
            for transType, transLabel, dnkExpr in cachedNeighbors:
                node = self.__addNewNode(transLabel, parentNode)
                nextLayer.append((dnkExpr, transType, node))
        return nextLayer, remLayer

    def __computeNeighbors(
        self, mod: maude.Module, layer: List[Tuple[str, str, TraceNode]]
    ) -> Dict[int, List[Tuple[str, str, str]]]:
        if not layer:
            return {}
        # TODO Also look through the layer and see if there are any duplicates that get computed multiple times
        inputs = [MaudeEncoder.hnfInput(node[2].id, node[1], node[0]) for node in layer]
        splitInputs = uniformSplit(inputs, self.config.threads)
        inputTerms = [MaudeEncoder.parallelHnfWorkerInputTerm(li) for li in splitInputs]
        # Workers cannot be initialized separately because the meta interpreters
        # are deleted by the Maude library as soon as the erewrite call is done.
        # So we have to create the meta-interpreters everytime we process a layer
        workersConfig = MaudeEncoder.metaInterpretersInitCall(self.config.threads)

        term = mod.parseTerm(MaudeEncoder.parallelHnfCall(workersConfig, inputTerms))
        (res, _) = term.erewrite()

        neighbors = extractListTerms(res, getSort(mod, ms.TDATA))
        resultsByPid: dict[int, List[Tuple[str, str, str]]] = {}
        for n in neighbors:
            (pid, transType, transLabel, dnkExpr) = extractTransData(n, mod)
            pidList = resultsByPid.setdefault(pid, [])
            pidList.append((transType, transLabel, dnkExpr))
        for node in layer:
            self.cache.setdefault((node[0], node[1]), resultsByPid[node[2].id])
        return resultsByPid
