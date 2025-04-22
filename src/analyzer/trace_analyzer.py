from os import linesep
from typing import Callable, List, Protocol, Tuple, TypeVar, cast

from src.analyzer.harmful_trace import HarmfulTrace, RaceType
from src.KATch_comm import KATchComm
from src.model.dnk_maude_model import ElementMetadata, ElementType
from src.trace.node import TraceNode
from src.trace.transition import ITransition, PktProcTrans, RcfgTrans


class TraceAnalyzerError(Exception):
    pass


_T1 = TypeVar("_T1", bound=ITransition)
_T2 = TypeVar("_T2", bound=ITransition)


class _TransitionCheckers(Protocol):
    def __getitem__(
        self, item: tuple[type[_T1], type[_T2]]
    ) -> Callable[[_T1, _T2], RaceType | None]: ...

    def __setitem__(
        self,
        key: tuple[type[_T1], type[_T2]],
        value: Callable[[_T1, _T2], RaceType | None],
    ) -> None: ...

    def __contains__(self, key: tuple[type[_T1], type[_T2]]) -> bool: ...


class TransitionsChecker:
    def __init__(
        self, katchComm: KATchComm, elDict: dict[int, ElementMetadata]
    ) -> None:
        self.elDict = elDict
        self.katchComm = katchComm
        self.__unexpected: dict[str, int] = {}
        self.__checks: _TransitionCheckers = cast(_TransitionCheckers, {})
        self.__checks[(PktProcTrans, RcfgTrans)] = self.checkProcRcfg
        self.__checks[(RcfgTrans, PktProcTrans)] = self.checkRcfgProc
        self.__checks[(RcfgTrans, RcfgTrans)] = self.checkRcfgRcfg

    def check(self, t1: ITransition, t2: ITransition) -> RaceType | None:
        key = (type(t1), type(t2))
        if key in self.__checks:
            return self.__checks[key](t1, t2)
        return self.checkDefault(t1, t2)

    def checkRcfgRcfg(self, t1: RcfgTrans, t2: RcfgTrans) -> RaceType | None:
        src1Type = self.elDict[t1.srcPos].pType
        src2Type = self.elDict[t2.srcPos].pType
        targetSw1Id = self.elDict[t1.dstPos].pID
        targetSw2Id = self.elDict[t2.dstPos].pID
        if (
            targetSw1Id != targetSw2Id
            or src1Type == ElementType.SW
            or src2Type == ElementType.SW
        ):
            return None

        res = self.katchComm.areNotEquiv(t1.policy, t2.policy)
        return RaceType.CTCT if res else None

    def checkProcRcfg(self, t1: PktProcTrans, t2: RcfgTrans) -> RaceType | None:
        targetSwId = self.elDict[t2.dstPos].pID
        srcSwId = self.elDict[t1.swPos].pID
        if targetSwId != srcSwId:
            return None

        res = self.katchComm.isNonEmptyDifference(t1.policy, t2.policy)
        return RaceType.SWCT if res else None

    def checkRcfgProc(self, t1: RcfgTrans, t2: PktProcTrans) -> RaceType | None:
        return self.checkProcRcfg(t2, t1)

    def checkDefault(self, t1: ITransition, t2: ITransition) -> RaceType | None:
        key = f"({type(t1).__name__}, {type(t2).__name__})"
        if key in self.__unexpected:
            self.__unexpected[key] += 1
            return None

        self.__unexpected[key] = 1
        return None

    def getUnexpectedTransPairsStr(self, prefix: str = "") -> str:
        sb: List[str] = []
        for key, value in self.__unexpected.items():
            sb.append(f"{prefix}{key}: {value} occurrences")
        return linesep.join(sb)


class TraceAnalyzer:
    def __init__(
        self, transChecker: TransitionsChecker, elDict: dict[int, ElementMetadata]
    ) -> None:
        self.transChecker = transChecker
        self.elDict = elDict
        self.trace: List[TraceNode] = []
        self.__skippedRaces: dict[RaceType, int] = {}

    def analyze(self, trace: List[TraceNode]) -> HarmfulTrace | None:
        """Does not account for policies/flow rules that are appended to a flow table.
        Raises TraceAnalyzerError if something goes wrong during the analysis."""
        self.trace = trace
        self.__validateTrace()

        for i, node in enumerate(self.trace):
            posPairs = node.getIncmpPosPairs()
            for el1, el2 in posPairs:
                res = self.__checkRace(i, el1, el2)
                if res is not None:
                    return HarmfulTrace(
                        self.trace, self.elDict, i, res[0], (el1, el2), res[1]
                    )
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
            print(
                f"Warning: unknown type for element at position {
                    el1} or {el2}"
            )
            return None
        if (
            self.elDict[el1].pType == ElementType.SW
            and self.elDict[el2].pType == ElementType.SW
        ):
            self.__addSkippedRace(RaceType.SWSW)
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

    def __addSkippedRace(self, rt: RaceType) -> None:
        if rt not in self.__skippedRaces:
            self.__skippedRaces[rt] = 1
            return
        self.__skippedRaces[rt] += 1

    def getSkippedRacesStr(self, prefix: str = "") -> str:
        sb: List[str] = []
        for key, value in self.__skippedRaces.items():
            sb.append(f"{prefix}{key}: {value} times")
        return linesep.join(sb)
