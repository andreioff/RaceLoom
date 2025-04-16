# mypy: disable-error-code="import-untyped,no-any-unimported,misc"

from enum import StrEnum
from typing import Dict, Hashable, List, Tuple

import maude
from src.analyzer.trace_parser import TraceNode
from src.analyzer.trace_transition import newTraceTransition
from src.decorators.cache_stats import CacheStats
from src.errors import MaudeError
from src.maude_encoder import MaudeEncoder
from src.maude_encoder import MaudeOps as mo
from src.maude_encoder import MaudeSorts as ms
from src.model.dnk_maude_model import DNKMaudeModel
from src.otf.vector_clock import newVectorClocks
from src.otf.worklist import Queue, Stack, WorkList


def extractListTerms(term: maude.Term, elSort: maude.Sort) -> List[maude.Term]:
    if term.getSort() == elSort:
        return [term]

    elements: List[maude.Term] = []
    for argument in term.arguments():
        if argument.getSort() != elSort:
            continue
        elements.append(argument)
    return elements


def getSort(mod: maude.Module, sortName: str) -> maude.Sort:
    sort: maude.Sort | None = mod.findSort(sortName)
    if sort is None:
        raise MaudeError(f"Could not find sort '{sortName}' in the given Maude module")
    return sort


def buildTraces(
    nodes: List[Tuple[TraceNode, int]], traceEnds: List[int]
) -> List[List[TraceNode]]:
    if not traceEnds:
        return []
    traces: List[List[TraceNode]] = []
    for end in traceEnds:
        trace: List[TraceNode] = []
        i = end
        while i >= 0:
            node, nextI = nodes[i]
            trace.append(node)
            i = nextI
        trace.reverse()
        traces.append(trace)
    return traces


class SequentialTraceGenerator:
    def __init__(self, workList: WorkList[Tuple[str, str, int, int]]):
        self.workList = workList
        self.cache: Dict[Tuple[Hashable, ...], List[Tuple[str, str, str]]] = {}
        self.cacheStats = CacheStats(0, 0)

    def run(
        self, model: DNKMaudeModel, mod: maude.Module, depth: int
    ) -> List[List[TraceNode]]:
        startDnkExpr = MaudeEncoder.parallelSeq(model.getElementTerms())
        startVC = newVectorClocks(len(model.getElementTerms()))
        startNode = TraceNode.fromTuple(("", startVC))
        # list of (node, parent index)
        nodes: List[Tuple[TraceNode, int]] = [(startNode, -1)]
        traceEnds: List[int] = []

        self.workList.reset()
        self.workList.append((startDnkExpr, mo.TRANS_TYPE_NONE, 0, 0))
        while not self.workList.isEmpty():
            (dnkExpr, prevTransType, currI, d) = self.workList.pop()
            neighbors = self.__computeNeighbors(mod, dnkExpr, prevTransType)
            if not neighbors:
                traceEnds.append(currI)
                continue

            for prevTransType, transLabel, dnkExpr in neighbors:
                trans = newTraceTransition(transLabel)
                vc = trans.updateVC(nodes[currI][0].vectorClocks)
                nodes.append((TraceNode(trans, vc), currI))
                if d + 1 < depth:
                    self.workList.append(
                        (dnkExpr, prevTransType, len(nodes) - 1, d + 1)
                    )
                else:
                    traceEnds.append(len(nodes) - 1)
        return buildTraces(nodes, traceEnds)

    def __computeNeighbors(
        self, mod: maude.Module, dnkExpr: str, prevTransType: str
    ) -> List[Tuple[str, str, str]]:
        key = (dnkExpr, prevTransType)
        if key in self.cache:
            self.cacheStats.hits += 1
            return self.cache[key]

        term = mod.parseTerm(MaudeEncoder.hnfCall(dnkExpr, prevTransType))
        term.reduce()

        neighbors = extractListTerms(term, getSort(mod, ms.TDATA))
        result = [self.__extractTransData(n, mod) for n in neighbors]

        self.cache[key] = result
        self.cacheStats.misses += 1
        return result

    def __extractTransData(
        self, term: maude.Term, mod: maude.Module
    ) -> Tuple[str, str, str]:
        expSorts: List[maude.Sort] = [
            getSort(mod, ms.TTYPE),
            getSort(mod, ms.STRING),
            getSort(mod, ms.DNK_COMP),
        ]
        args: List[str] = []
        for i, arg in enumerate(term.arguments()):
            argSort = arg.getSort()
            if argSort != expSorts[i] and not argSort.leq(expSorts[i]):
                raise MaudeError(
                    "Unexpected Maude type when extracting "
                    + "head normal form result. "
                    + f"Found: '{arg.getSort()}', expected: '{expSorts[i]}'."
                )
            args.append(arg.prettyPrint(maude.PRINT_MIXFIX))
        return args[0], args[1].strip('"'), args[2]


class DFSTraceGenerator(SequentialTraceGenerator):
    def __init__(self) -> None:
        super().__init__(Stack[Tuple[str, str, int, int]]())


class BFSTraceGenerator(SequentialTraceGenerator):
    def __init__(self) -> None:
        super().__init__(Queue[Tuple[str, str, int, int]]())


class TraceGenOption(StrEnum):
    DFS = "dfs"
    BFS = "bfs"


def newTraceGenerator(option: TraceGenOption) -> SequentialTraceGenerator:
    if option == TraceGenOption.DFS:
        return DFSTraceGenerator()
    return BFSTraceGenerator()
