# mypy: disable-error-code="import-untyped,no-any-unimported,misc"

from typing import Dict, List, Tuple

import maude
from src.generator.trace_generator import (TraceGenerator, buildTraces,
                                           extractListTerms, extractTransData,
                                           getSort)
from src.maude_encoder import MaudeEncoder, MaudeModules
from src.maude_encoder import MaudeOps as mo
from src.maude_encoder import MaudeSorts as ms
from src.model.dnk_maude_model import DNKMaudeModel
from src.trace.node import TraceNode
from src.trace.transition import newTraceTransition
from src.trace.vector_clocks import newVectorClocks
from src.util import uniformSplit


class ParallelBFSTraceGenerator(TraceGenerator):
    def __init__(self, threads: int) -> None:
        super().__init__()
        # list of (node, parent index)
        self.nodes: List[Tuple[TraceNode, int]] = []
        self.threads = threads

    def reset(self) -> None:
        super().reset()
        self.nodes = []

    def getRequiredImports(self) -> List[MaudeModules]:
        return [MaudeModules.PARALLEL_HEAD_NORMAL_FORM]

    def run(
        self, model: DNKMaudeModel, mod: maude.Module, depth: int
    ) -> List[List[TraceNode]]:
        self.reset()
        startDnkExpr = MaudeEncoder.parallelSeq(model.getElementTerms())
        startVC = newVectorClocks(len(model.getElementTerms()))
        startNode = TraceNode.fromTuple(("", startVC))
        self.nodes.append((startNode, -1))

        # dnkExpr, prevTransType, currI
        currLayer: List[Tuple[str, str, int]] = [(startDnkExpr, mo.TRANS_TYPE_NONE, 0)]
        while currLayer and depth > 0:
            nextLayer, remLayer = self.__appendCachedNodes(currLayer)
            results = self.__computeNeighbors(mod, remLayer)

            for pid, neighbors in results.items():
                for prevTransType, transLabel, dnkExpr in neighbors:
                    index = self.__addNode(transLabel, pid)
                    nextLayer.append((dnkExpr, prevTransType, index))
            currLayer = nextLayer
            depth -= 1

        return buildTraces(self.nodes, self.__computeTraceEnds())

    def __addNode(self, transLabel: str, pid: int) -> int:
        trans = newTraceTransition(transLabel)
        parentNode = self.nodes[pid][0]
        vc = trans.updateVC(parentNode.vectorClocks)
        self.nodes.append((TraceNode(trans, vc), pid))
        return len(self.nodes) - 1

    def __appendCachedNodes(
        self, layer: List[Tuple[str, str, int]]
    ) -> Tuple[List[Tuple[str, str, int]], List[Tuple[str, str, int]]]:
        nextLayer: List[Tuple[str, str, int]] = []
        remLayer: List[Tuple[str, str, int]] = []
        for node in layer:
            currDnkExpr, prevTransType, currI = node
            cachedNeighbors = self.cache.get((currDnkExpr, prevTransType), [])
            if not cachedNeighbors:
                remLayer.append(node)
                self.cacheStats.misses += 1
                continue
            self.cacheStats.hits += 1
            for transType, transLabel, dnkExpr in cachedNeighbors:
                index = self.__addNode(transLabel, currI)
                nextLayer.append((dnkExpr, transType, index))
        return nextLayer, remLayer

    def __computeNeighbors(
        self, mod: maude.Module, layer: List[Tuple[str, str, int]]
    ) -> Dict[int, List[Tuple[str, str, str]]]:
        if not layer:
            return {}
        inputs = [MaudeEncoder.hnfInput(node[2], node[1], node[0]) for node in layer]
        splitInputs = uniformSplit(inputs, self.threads)
        inputTerms = [MaudeEncoder.parallelHnfWorkerInputTerm(li) for li in splitInputs]
        # Workers cannot be initialized separately because the meta interpreters
        # are deleted by the Maude library as soon as the erewrite call is done.
        # So we have to create the meta-interpreters everytime we process a layer
        workersConfig = MaudeEncoder.metaInterpretersInitCall(self.threads)

        term = mod.parseTerm(MaudeEncoder.parallelHnfCall(workersConfig, inputTerms))
        (res, _) = term.erewrite()

        neighbors = extractListTerms(res, getSort(mod, ms.TDATA))
        resultsByPid: dict[int, List[Tuple[str, str, str]]] = {}
        for n in neighbors:
            (pid, transType, transLabel, dnkExpr) = extractTransData(n, mod)
            pidList = resultsByPid.setdefault(pid, [])
            pidList.append((transType, transLabel, dnkExpr))
        for node in layer:
            self.cache.setdefault((node[0], node[1]), resultsByPid[node[2]])
        return resultsByPid

    def __computeTraceEnds(self) -> List[int]:
        isEnd: List[bool] = [True] * len(self.nodes)
        for _n, pid in self.nodes:
            if pid < 0:
                continue
            isEnd[pid] = False
        traceEnds: List[int] = []
        for i in range(len(isEnd)):
            if not isEnd[i]:
                continue
            traceEnds.append(i)
        return traceEnds
