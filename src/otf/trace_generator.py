# mypy: disable-error-code="import-untyped,no-any-unimported,misc"

from typing import List, Tuple

import maude
from src.analyzer.trace_parser import TraceNode
from src.analyzer.trace_transition import ITransition, newTraceTransition
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
            (dnkExpr, transType, currI, d) = self.workList.pop()

            term = mod.parseTerm(MaudeEncoder.hnfCall(dnkExpr, transType))
            term.reduce()

            neighbors = extractListTerms(term, getSort(mod, ms.TDATA))
            if not neighbors:
                traceEnds.append(currI)
                continue

            for n in neighbors:
                transType, trans, dnkExpr = self.__extractTransData(n, mod)
                vc = trans.updateVC(nodes[currI][0].vectorClocks)
                nodes.append((TraceNode(trans, vc), currI))
                if d + 1 < depth:
                    self.workList.append((dnkExpr, transType, len(nodes) - 1, d + 1))
                else:
                    traceEnds.append(len(nodes) - 1)
        return buildTraces(nodes, traceEnds)

    def __extractTransData(
        self, term: maude.Term, mod: maude.Module
    ) -> Tuple[str, ITransition, str]:
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
        trans = newTraceTransition(args[1].strip('"'))
        return args[0], trans, args[2]


class DFSTraceGenerator(SequentialTraceGenerator):
    def __init__(self) -> None:
        super().__init__(Stack[Tuple[str, str, int, int]]())


class BFSTraceGenerator(SequentialTraceGenerator):
    def __init__(self) -> None:
        super().__init__(Queue[Tuple[str, str, int, int]]())
