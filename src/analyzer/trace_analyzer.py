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
        self, katchComm: KATchComm, elsMetadata: List[ElementMetadata]
    ) -> None:
        self.elsMetadata = elsMetadata
        self.katchComm = katchComm
        self._unexpected: dict[str, int] = {}
        self._checks: _TransitionCheckers = cast(_TransitionCheckers, {})
        self._checks[(PktProcTrans, RcfgTrans)] = self._checkProcRcfg
        self._checks[(RcfgTrans, PktProcTrans)] = self._checkRcfgProc
        self._checks[(RcfgTrans, RcfgTrans)] = self._checkRcfgRcfg

    def check(self, t1: ITransition, t2: ITransition) -> RaceType | None:
        key = (type(t1), type(t2))
        if key in self._checks:
            return self._checks[key](t1, t2)
        return self._addUnexpectedTransPair(t1, t2)

    def _checkRcfgRcfg(self, t1: RcfgTrans, t2: RcfgTrans) -> RaceType | None:
        src1Type = self.elsMetadata[t1.srcPos].pType
        src2Type = self.elsMetadata[t2.srcPos].pType
        targetSw1Id = self.elsMetadata[t1.dstPos].pID
        targetSw2Id = self.elsMetadata[t2.dstPos].pID
        if (
            targetSw1Id != targetSw2Id
            or src1Type == ElementType.SW
            or src2Type == ElementType.SW
        ):
            return None

        res = self.katchComm.areNotEquiv(t1.policy, t2.policy)
        return RaceType.CT_SW_CT if res else None

    def _checkProcRcfg(self, t1: PktProcTrans, t2: RcfgTrans) -> RaceType | None:
        targetSwId = self.elsMetadata[t2.dstPos].pID
        srcSwId = self.elsMetadata[t1.swPos].pID
        rcfgSrcType = self.elsMetadata[t2.srcPos].pType
        if targetSwId != srcSwId or rcfgSrcType == ElementType.SW:
            return None

        res = self.katchComm.isNonEmptyDifference(t1.policy, t2.policy)
        return RaceType.CT_SW if res else None

    def _checkRcfgProc(self, t1: RcfgTrans, t2: PktProcTrans) -> RaceType | None:
        return self._checkProcRcfg(t2, t1)

    def _addUnexpectedTransPair(
        self, t1: ITransition, t2: ITransition
    ) -> RaceType | None:
        key = f"({type(t1).__name__}, {type(t2).__name__})"
        if key in self._unexpected:
            self._unexpected[key] += 1
            return None

        self._unexpected[key] = 1
        return None

    def getUnexpectedTransPairsStr(self, prefix: str = "") -> str:
        sb: List[str] = []
        for key, value in self._unexpected.items():
            sb.append(f"{prefix}{key}: {value} occurrences")
        return linesep.join(sb)


def _validateTrace(trace: List[TraceNode], elsMetadata: List[ElementMetadata]) -> None:
    """Raises TraceAnalyzerError if the vector clocks of any nodes in
    the given trace does not match the number of elements of
    the elements' metadata list."""
    elsNr = len(elsMetadata)
    for i, node in enumerate(trace):
        if i > 0 and node.trans.getSource() is None:
            raise TraceAnalyzerError(
                f"Transition of trace node {i} has no source element, "
                + "so it is likely an empty transition. "
                + "Only the first node of the trace can have an empty transition."
            )

        if i > 0 and not node.trans.hasValidPositions(elsMetadata):
            raise TraceAnalyzerError(
                f"Unknown type for elements that are part of transition of node {i}. "
                + "This may suggest that the wrong DNK model information "
                + f"was passed to {TraceAnalyzer.__name__}."
            )
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


class TraceAnalyzer:
    def __init__(
        self, transChecker: TransitionsChecker, elsMetadata: List[ElementMetadata]
    ) -> None:
        self._transChecker = transChecker
        self._elsMetadata = elsMetadata
        self._trace: List[TraceNode] = []
        # maps element position to last node with a transition generated by element
        self._elLastNode: dict[int, int] = {}
        self.__skippedRaces: dict[RaceType, int] = {}

    def analyze(self, trace: List[TraceNode]) -> HarmfulTrace | None:
        """Does not account for policies/flow rules that are appended to a flow table.
        Raises TraceAnalyzerError if something goes wrong during the analysis."""
        self._trace = trace
        self._elLastNode = {}
        _validateTrace(self._trace, self._elsMetadata)
        for i, node in enumerate(self._trace):
            if i == 0 and not node.trans.policy:
                continue  # skip empty start node
            el1 = node.trans.getSource()
            if el1 is None:
                raise TraceAnalyzerError("Found transition without source")
            # for rcfgs, we don't update the last node of the switch (i.e. the
            # destination of the rcfg) because we are interested in races
            # where the switch processes a packet.
            self._elLastNode[el1] = i
            for el2 in self._findElementsRacingWith(el1):
                res = self._checkRace(el1, el2)
                if res is None:
                    continue
                return HarmfulTrace(self._trace, self._elsMetadata, res[0], res[1])
        return None

    def _findElementsRacingWith(self, el1: int) -> List[int]:
        racingElements: List[int] = []
        vc1 = self._trace[self._elLastNode[el1]].vectorClocks[el1]
        for el2, node2Pos in self._elLastNode.items():
            if el2 == el1:
                continue
            vc2 = self._trace[node2Pos].vectorClocks[el2]
            if (vc1[el1] <= vc2[el1] and vc1[el2] <= vc2[el2]) or (
                vc1[el1] >= vc2[el1] and vc1[el2] >= vc2[el2]
            ):
                continue
            racingElements.append(el2)
        return racingElements

    def _checkRace(self, el1: int, el2: int) -> Tuple[dict[int, int], RaceType] | None:
        if (
            self._elsMetadata[el1].pType == ElementType.SW
            and self._elsMetadata[el2].pType == ElementType.SW
        ):
            self._addSkippedRace(RaceType.SW_SW)
            return None

        node1Pos = self._elLastNode[el1]
        node2Pos = self._elLastNode[el2]
        raceType = self._transChecker.check(
            self._trace[node1Pos].trans, self._trace[node2Pos].trans
        )
        if raceType is not None:
            return {node1Pos: el1, node2Pos: el2}, raceType
        return None

    def _addSkippedRace(self, rt: RaceType) -> None:
        if rt not in self.__skippedRaces:
            self.__skippedRaces[rt] = 1
            return
        self.__skippedRaces[rt] += 1

    def getSkippedRacesStr(self, prefix: str = "") -> str:
        sb: List[str] = []
        for key, value in self.__skippedRaces.items():
            sb.append(f"{prefix}{key}: {value} times")
        return linesep.join(sb)
