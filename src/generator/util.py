# mypy: disable-error-code="import-untyped,no-any-unimported,misc"
from typing import List, Tuple

import maude
from src.errors import MaudeError
from src.maude_encoder import MaudeSorts as ms
from src.trace.node import TraceNode


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


def extractTransData(term: maude.Term, mod: maude.Module) -> Tuple[int, str, str, str]:
    expSorts: List[maude.Sort] = [
        getSort(mod, ms.NAT),
        getSort(mod, ms.TTYPE),
        getSort(mod, ms.STRING),
        getSort(mod, ms.DNK_COMP),
    ]
    printFormatCodes: List[int] = [
        maude.PRINT_NUMBER,
        maude.PRINT_MIXFIX,
        maude.PRINT_MIXFIX,
        maude.PRINT_MIXFIX,
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
        args.append(arg.prettyPrint(printFormatCodes[i]))
    return int(args[0]), args[1], args[2].strip('"'), args[3]
