# mypy: disable-error-code="import-untyped,no-any-unimported,misc"

from abc import ABC, abstractmethod
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


class TraceGenerator(ABC):
    @abstractmethod
    def run(
        self, model: DNKMaudeModel, mod: maude.Module, depth: int
    ) -> List[List[TraceNode]]: ...

    def extractTransData(
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


class DFSTraceGenerator(TraceGenerator):
    def run(
        self, model: DNKMaudeModel, mod: maude.Module, depth: int
    ) -> List[List[TraceNode]]:
        traces: List[List[TraceNode]] = []
        startDnkExpr = MaudeEncoder.parallelSeq(model.getElementTerms())
        startVC = newVectorClocks(len(model.getElementTerms()))
        startNode = TraceNode.fromTuple(("", startVC))

        stack: List[Tuple[str, str, TraceNode, int]] = [
            (startDnkExpr, mo.TRANS_TYPE_NONE, startNode, 0)
        ]
        trace: List[TraceNode] = []
        while stack:
            (dnkExpr, transType, currTN, d) = stack.pop()
            trace = trace[:d]
            trace.append(currTN)
            if d == depth:
                traces.append(trace.copy())
                continue

            term = mod.parseTerm(MaudeEncoder.hnfCall(dnkExpr, transType))
            term.reduce()

            neighbors = extractListTerms(term, getSort(mod, ms.TDATA))
            if not neighbors:
                traces.append(trace.copy())
                continue

            for n in neighbors:
                transType, trans, dnkExpr = self.extractTransData(n, mod)
                vc = trans.updateVC(trace[-1].vectorClocks)
                stack.append((dnkExpr, transType, TraceNode(trans, vc), d + 1))

        return traces
