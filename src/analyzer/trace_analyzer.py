from typing import Callable, List, Protocol, Tuple, TypeVar, cast
from src.analyzer.harmful_trace import HarmfulTrace, RaceType

from src.analyzer.trace_parser import (
    PktProcTrans,
    RcfgTrans,
    TraceNode,
    TraceTransition,
)
from src.KATch_comm import KATchComm
from src.model.dnk_maude_model import ElementType


class TraceAnalyzerError(Exception):
    pass


_T1 = TypeVar("_T1", bound=TraceTransition)
_T2 = TypeVar("_T2", bound=TraceTransition)


class _TransitionCheckers(Protocol):
    def __getitem__(
        self, item: tuple[type[_T1], type[_T2]]
    ) -> Callable[[_T1, _T2], RaceType | None]: ...

    def __setitem__(
        self, key: tuple[type[_T1], type[_T2]], value: Callable[[_T1, _T2], RaceType | None]
    ) -> None: ...

    def __contains__(self, key: tuple[type[_T1], type[_T2]]) -> bool: ...


class TransitionsChecker:
    def __init__(self, katchComm: KATchComm, elDict: dict[int, ElementType]) -> None:
        self.elDict = elDict
        self.katchComm = katchComm
        self.__checks: _TransitionCheckers = cast(_TransitionCheckers, {})
        self.__checks[(PktProcTrans, RcfgTrans)] = self.checkProcRcfg
        self.__checks[(RcfgTrans, RcfgTrans)] = self.checkRcfgRcfg

    def check(self, t1: TraceTransition, t2: TraceTransition) -> RaceType | None:
        key = (type(t1), type(t2))
        if key in self.__checks:
            return self.__checks[key](t1, t2)
        return self.checkDefault(t1, t2)

    def checkRcfgRcfg(self, t1: RcfgTrans, t2: RcfgTrans) -> RaceType | None:
        # TODO AND THERE ARE NO OTHER RCFGs in between that modify the same switch
        if (
            t1.dstPos != t2.dstPos
            or self.elDict[t1.srcPos] == ElementType.SW
            or self.elDict[t2.srcPos] == ElementType.SW
        ):
            return None

        res = self.katchComm.areNotEquiv(t1.policy, t2.policy)
        return RaceType.CTCT if res else None

    def checkProcRcfg(self, t1: PktProcTrans, t2: RcfgTrans) -> RaceType | None:
        if t2.dstPos != t1.swPos:
            return None

        res = self.katchComm.isNonEmptyDifference(t1.policy, t2.policy)
        return RaceType.SWCT if res else None

    def checkDefault(self, t1: TraceTransition, t2: TraceTransition) -> RaceType | None:
        print(
            "Found race between unexpected transitions:\n"
            + f"\t type t1 is: '{type(t1)}', and type t2 is: '{type(t2)}'"
        )
        return None


class TraceAnalyzer:
    def __init__(
        self,
        transChecker: TransitionsChecker,
        elDict: dict[int, ElementType],
        trace: List[TraceNode],
    ) -> None:
        self.elDict: dict[int, ElementType] = elDict
        self.trace: List[TraceNode] = trace
        self.transChecker = transChecker
        self.__validateTrace()

    def analyze(self) -> HarmfulTrace | None:
        """ Does not account for policies/flow rules that are appended to a flow table.
        Raises TraceAnalyzerError if something goes wrong during the analysis."""
        for i, node in enumerate(self.trace):
            posPairs = node.getIncmpPosPairs()
            for el1, el2 in posPairs:
                res = self.__checkRace(i, el1, el2)
                if res is not None:
                    return HarmfulTrace(self.trace, self.elDict, i, res[0], (el1, el2), res[1])
        return None

    def __validateTrace(self) -> None:
        """Raises TraceAnalyzerError if given trace is invalid"""
        elsNr = len(self.elDict)
        for i, node in enumerate(self.trace):
            if len(node.vectorClocks) != elsNr:
                raise TraceAnalyzerError(
                    f"Number of vector clocks of trace node {i} does "
                    + f"not match the number of expected elements ({elsNr})"
                )
            for vc in node.vectorClocks:
                if len(vc) != elsNr:
                    raise TraceAnalyzerError(
                        f"Vector clock size of trace node {i} does not match "
                        + f"the number of expected elements ({elsNr})"
                    )

    def __findTransitions(
        self, startNodePos: int, elPos1: int, elPos2: int
    ) -> Tuple[int, int] | None:
        """Returns a sorted pair of indicies pointing to the transitions that
        caused the incomparable vector clocks of the node at index 'startNodePos',
        or None if there is no such pair."""
        t1Pos, t2Pos = -1, -1
        for p in range(startNodePos, 0, -1):
            if t1Pos == -1 and self.trace[p].trans.isModifyingVCPos(elPos1):
                t1Pos = p
            elif t2Pos == -1 and self.trace[p].trans.isModifyingVCPos(elPos2):
                t2Pos = p
        if t1Pos == -1 or t2Pos == -1:
            return None
        return (t1Pos, t2Pos) if t1Pos < t2Pos else (t2Pos, t1Pos)

    def __checkRace(
        self, startNodePos: int, el1: int, el2: int
    ) -> Tuple[Tuple[int, int], RaceType] | None:
        if el1 not in self.elDict or el2 not in self.elDict:
            print(f"Warning: unknown type for element at position {
                  el1} or {el2}")
            return None
        if self.elDict[el1] == ElementType.SW and self.elDict[el2] == ElementType.SW:
            print("Skipping SW-SW race...")
            return None
        ps = self.__findTransitions(startNodePos, el1, el2)
        if ps is None:
            return None

        raceType = self.transChecker.check(
            self.trace[ps[0]].trans, self.trace[ps[1]].trans
        )
        if raceType is not None:
            return ps, raceType

        return None
