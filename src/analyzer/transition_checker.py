from os import linesep
from typing import Callable, List, Protocol, Tuple, TypeVar, cast

from src.analyzer.harmful_trace import RaceType
from src.KATch_comm import KATchComm
from src.model.dnk_maude_model import ElementMetadata, ElementType
from src.trace.transition import ITransition, PktProcTrans, RcfgTrans

_T1 = TypeVar("_T1", bound=ITransition)
_T2 = TypeVar("_T2", bound=ITransition)


class _TransitionCheckers(Protocol):
    def __getitem__(
        self, item: tuple[type[_T1], type[_T2]]
    ) -> List[Callable[[_T1, _T2], Tuple[RaceType | None, bool]]]: ...

    def __setitem__(
        self,
        key: tuple[type[_T1], type[_T2]],
        value: List[Callable[[_T1, _T2], Tuple[RaceType | None, bool]]],
    ) -> None: ...

    def __contains__(self, key: tuple[type[_T1], type[_T2]]) -> bool: ...


class TransitionsChecker:
    def __init__(
        self,
        katchComm: KATchComm,
        elsMetadata: List[ElementMetadata],
        skippedRaces: List[RaceType] | None = None,
    ) -> None:
        self.elsMetadata = elsMetadata
        self.katchComm = katchComm
        self._skipped: dict[str, int] = {}
        self._skippedRaces: List[RaceType] = (
            [] if skippedRaces is None else skippedRaces
        )

        self._checks: _TransitionCheckers = cast(_TransitionCheckers, {})
        self._checks[(PktProcTrans, PktProcTrans)] = [self._checkSWSW]
        self._checks[(PktProcTrans, RcfgTrans)] = [self._checkSWCT]
        self._checks[(RcfgTrans, PktProcTrans)] = [self._checkCTSW]
        self._checks[(RcfgTrans, RcfgTrans)] = [self._checkCTSWCT, self._checkCTCTSW]

    def check(self, t1: ITransition, t2: ITransition) -> RaceType | None:
        key = (type(t1), type(t2))
        if key not in self._checks:
            return None
        checks = self._checks[key]
        for check in checks:
            res, satisfiesReqs = check(t1, t2)
            if satisfiesReqs:
                return res
        return None

    def _checkSWSW(
        self, t1: PktProcTrans, t2: PktProcTrans
    ) -> Tuple[RaceType | None, bool]:
        self._addSkippedRace(RaceType.SW_SW)
        return None, True

    def _checkCTSWCT(
        self, t1: RcfgTrans, t2: RcfgTrans
    ) -> Tuple[RaceType | None, bool]:
        src1Type = self.elsMetadata[t1.srcPos].pType
        src2Type = self.elsMetadata[t2.srcPos].pType
        targetSw1Id = self.elsMetadata[t1.dstPos].pID
        targetSw2Id = self.elsMetadata[t2.dstPos].pID
        if (
            targetSw1Id != targetSw2Id
            or src1Type == ElementType.SW
            or src2Type == ElementType.SW
        ):
            return None, False

        if RaceType.CT_SW_CT in self._skippedRaces:
            self._addSkippedRace(RaceType.CT_SW_CT)
            return None, True

        # harmful if the new policy of CT1 is not equivalent
        # to the new policy from CT2
        res = self.katchComm.areNotEquiv(t1.policy, t2.policy)
        return RaceType.CT_SW_CT if res else None, True

    def _checkCTCTSW(
        self, t1: RcfgTrans, t2: RcfgTrans
    ) -> Tuple[RaceType | None, bool]:
        res1 = self._satisfiesCTCTSWPreReqs(t1, t2)
        res2 = self._satisfiesCTCTSWPreReqs(t2, t1)

        if not res1 and not res2:
            return None, False
        if not res1 and res2:
            t1, t2 = t2, t1

        if RaceType.CT_CT_SW in self._skippedRaces:
            self._addSkippedRace(RaceType.CT_CT_SW)
            return None, True

        # harmful if the new policy of the updating controller (t1) does not cover
        # the same packets as the new policy installed by the updated controller (t2)
        res = self.katchComm.isNonEmptyDifference(t2.policy, t1.policy)
        return RaceType.CT_CT_SW if res else None, True

    def _satisfiesCTCTSWPreReqs(self, t1: RcfgTrans, t2: RcfgTrans) -> bool:
        src1 = self.elsMetadata[t1.srcPos]
        src2 = self.elsMetadata[t2.srcPos]
        dst1 = self.elsMetadata[t1.dstPos]
        dst2 = self.elsMetadata[t2.dstPos]

        return (
            src1.pType == ElementType.CT
            and dst1.pType == ElementType.CT
            and src2.pType == ElementType.CT
            and dst2.pType == ElementType.SW
            and dst1.pID == src2.pID
        )

    def _checkSWCT(
        self, t1: PktProcTrans, t2: RcfgTrans
    ) -> Tuple[RaceType | None, bool]:
        return self._checkCTSW(t2, t1)

    def _checkCTSW(
        self, t1: RcfgTrans, t2: PktProcTrans
    ) -> Tuple[RaceType | None, bool]:
        targetSwId = self.elsMetadata[t1.dstPos].pID
        srcSwId = self.elsMetadata[t2.swPos].pID
        rcfgSrcType = self.elsMetadata[t1.srcPos].pType
        if targetSwId != srcSwId or rcfgSrcType == ElementType.SW:
            return None, False

        if RaceType.CT_SW in self._skippedRaces:
            self._addSkippedRace(RaceType.CT_SW)
            return None, True
        # harmful if the new policy does not cover the same packets
        # covered by the current policy of the switch
        res = self.katchComm.isNonEmptyDifference(t2.policy, t1.policy)
        return RaceType.CT_SW if res else None, True

    def _addSkippedRace(self, rt: RaceType) -> None:
        if rt not in self._skipped:
            self._skipped[rt] = 1
            return
        self._skipped[rt] += 1

    def getSkippedRacesStr(self, prefix: str = "") -> str:
        sb: List[str] = []
        for key, value in self._skipped.items():
            sb.append(f"{prefix}{key}: {value} times")
        return linesep.join(sb)
