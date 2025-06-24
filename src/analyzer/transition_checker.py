from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
from os import linesep
from typing import List, Protocol, Tuple, TypeVar, cast

from src.analyzer.harmful_trace import RaceType
from src.analyzer.util import (buildNetworkPolicy, elementIsActiveInBetween,
                               elementIsRcfgTargetInBetween,
                               reconstructElementFTs)
from src.KATch_comm import KATchComm
from src.model.dnk_maude_model import ElementMetadata, ElementType
from src.trace.node import TraceNode
from src.trace.transition import ITransition, PktProcTrans, RcfgTrans

_T1 = TypeVar("_T1", bound=ITransition)
_T2 = TypeVar("_T2", bound=ITransition)


@dataclass(frozen=True)
class TransCheckResult:
    raceType: RaceType
    netPolicy1: str
    netPolicy2: str


class RaceHandler[_T1, _T2](ABC):
    def __init__(self, tc: TransitionsChecker, raceType: RaceType) -> None:
        self.tc = tc
        self.raceType = raceType

    @abstractmethod
    def validate(
        self,
        trace: List[TraceNode],
        t1: Tuple[_T1, int],
        t2: Tuple[_T2, int],
    ) -> bool: ...

    @abstractmethod
    def check(
        self,
        trace: List[TraceNode],
        t1: Tuple[_T1, int],
        t2: Tuple[_T2, int],
    ) -> TransCheckResult | None: ...

    def _reconstructRcfg(
        self, fts: List[str], policy: str, targetEl: int, targetFTChannel: str
    ) -> str:
        """
        If the given node position does not contain a rcfg transition, it
        returns the policy of the node's transition.
        """
        targetFt = self.tc.elsMetadata[targetEl].findSwitchIndex(targetFTChannel)
        if targetFt == -1:
            raise ValueError("Could not match network switch based on rcfg channel")
        fts[targetFt] = policy
        return buildNetworkPolicy(fts, self.tc.elsMetadata[targetEl].link)


class SWSWRaceHandler(RaceHandler[PktProcTrans, PktProcTrans]):
    def __init__(self, tc: TransitionsChecker) -> None:
        super().__init__(tc, RaceType.SW_SW)

    def validate(
        self,
        trace: List[TraceNode],
        t1: Tuple[PktProcTrans, int],
        t2: Tuple[PktProcTrans, int],
    ) -> bool:
        return True

    def check(
        self,
        trace: List[TraceNode],
        t1: Tuple[PktProcTrans, int],
        t2: Tuple[PktProcTrans, int],
    ) -> TransCheckResult | None:
        return None


class CTSWCTRaceHandler(RaceHandler[RcfgTrans, RcfgTrans]):
    def __init__(self, tc: TransitionsChecker) -> None:
        super().__init__(tc, RaceType.CT_SW_CT)

    def validate(
        self,
        trace: List[TraceNode],
        t1: Tuple[RcfgTrans, int],
        t2: Tuple[RcfgTrans, int],
    ) -> bool:
        if self.raceType not in self.tc.safetyProps:
            return False
        src1Type = self.tc.elsMetadata[t1[0].srcPos].pType
        src2Type = self.tc.elsMetadata[t2[0].srcPos].pType
        targetSw1Id = self.tc.elsMetadata[t1[0].dstPos].pID
        targetSw2Id = self.tc.elsMetadata[t2[0].dstPos].pID
        if not (
            targetSw1Id == targetSw2Id
            and src1Type == ElementType.CT
            and src2Type == ElementType.CT
            and not elementIsActiveInBetween(trace, t1[1], t2[1], t1[0].srcPos)
            and not elementIsRcfgTargetInBetween(trace, t1[1], t2[1], t1[0].dstPos)
        ):
            return False
        return True

    def check(
        self,
        trace: List[TraceNode],
        t1: Tuple[RcfgTrans, int],
        t2: Tuple[RcfgTrans, int],
    ) -> TransCheckResult | None:
        # Reconstruction is done up to the rcfg (possibly including the other rcfg
        # as well!). This is because not all pairs of racing rcfgs may be harmful,
        # e.g. when the rcfgs target different flow tables of the same element.
        swFts = reconstructElementFTs(trace, self.tc.elsMetadata, t1[1], t1[0].dstPos)
        pol1 = self._reconstructRcfg(swFts, t1[0].policy, t1[0].dstPos, t1[0].channel)
        swFts = reconstructElementFTs(trace, self.tc.elsMetadata, t2[1], t2[0].dstPos)
        pol2 = self._reconstructRcfg(swFts, t2[0].policy, t2[0].dstPos, t2[0].channel)

        # harmful if the new policy of CT1 is not equivalent to the new policy from CT2
        res1 = self.tc.katchComm.checkProperty(self.tc.safetyProps[self.raceType], pol1)
        res2 = self.tc.katchComm.checkProperty(self.tc.safetyProps[self.raceType], pol2)
        if res1 == res2:
            return None
        return TransCheckResult(self.raceType, pol1, pol2)


class CTCTSWRaceHandler(RaceHandler[RcfgTrans, RcfgTrans]):
    def __init__(self, tc: TransitionsChecker) -> None:
        super().__init__(tc, RaceType.CT_CT_SW)

    def validate(
        self,
        trace: List[TraceNode],
        t1: Tuple[RcfgTrans, int],
        t2: Tuple[RcfgTrans, int],
    ) -> bool:
        if self.raceType not in self.tc.safetyProps:
            return False
        if t1[1] > t2[1]:
            t1, t2 = t2, t1

        src1 = self.tc.elsMetadata[t1[0].srcPos]
        src2 = self.tc.elsMetadata[t2[0].srcPos]
        dst1 = self.tc.elsMetadata[t1[0].dstPos]
        dst2 = self.tc.elsMetadata[t2[0].dstPos]

        if not (
            src1.pType == ElementType.CT
            and dst1.pType == ElementType.SW
            and src2.pType == ElementType.CT
            and dst2.pType == ElementType.CT
            and src1.pID == dst2.pID
            and not elementIsActiveInBetween(trace, t1[1], t2[1], t1[0].srcPos)
            and not elementIsRcfgTargetInBetween(trace, t1[1], t2[1], t1[0].dstPos)
        ):
            return False
        return True

    def check(
        self,
        trace: List[TraceNode],
        t1: Tuple[RcfgTrans, int],
        t2: Tuple[RcfgTrans, int],
    ) -> TransCheckResult | None:
        swapped = False
        if t1[1] > t2[1]:
            t1, t2 = t2, t1
            swapped = True

        ct1Rcfg, ct2Rcfg, sw = t1[0], t2[0], t1[0].dstPos
        swFts = reconstructElementFTs(trace, self.tc.elsMetadata, min(t1[1], t2[1]), sw)
        pol1 = self._reconstructRcfg(swFts, ct1Rcfg.policy, sw, ct1Rcfg.channel)
        pol2 = self._reconstructRcfg(swFts, ct2Rcfg.policy, sw, ct1Rcfg.channel)

        res1 = self.tc.katchComm.checkProperty(self.tc.safetyProps[self.raceType], pol1)
        res2 = self.tc.katchComm.checkProperty(self.tc.safetyProps[self.raceType], pol2)
        # harmful if one of the policies satisfies the property, but the other does not
        if res1 == res2:
            return None
        if swapped:
            pol1, pol2 = pol2, pol1
        return TransCheckResult(self.raceType, pol1, pol2)


class CTSWRaceHandler(RaceHandler[RcfgTrans, PktProcTrans]):
    def __init__(self, tc: TransitionsChecker) -> None:
        super().__init__(tc, RaceType.CT_SW)

    def validate(
        self,
        trace: List[TraceNode],
        t1: Tuple[RcfgTrans, int],
        t2: Tuple[PktProcTrans, int],
    ) -> bool:
        if self.raceType not in self.tc.safetyProps:
            return False
        targetSwId = self.tc.elsMetadata[t1[0].dstPos].pID
        srcSwId = self.tc.elsMetadata[t2[0].swPos].pID
        rcfgSrcType = self.tc.elsMetadata[t1[0].srcPos].pType
        if not (
            targetSwId == srcSwId
            and rcfgSrcType == ElementType.CT
            and not elementIsActiveInBetween(trace, t1[1], t2[1], t2[0].swPos)
        ):
            return False
        return True

    def check(
        self,
        trace: List[TraceNode],
        t1: Tuple[RcfgTrans, int],
        t2: Tuple[PktProcTrans, int],
    ) -> TransCheckResult | None:
        swFts = reconstructElementFTs(trace, self.tc.elsMetadata, t1[1], t1[0].dstPos)
        pol1 = self._reconstructRcfg(swFts, t1[0].policy, t1[0].dstPos, t1[0].channel)

        res1 = self.tc.katchComm.checkProperty(self.tc.safetyProps[self.raceType], pol1)
        res2 = self.tc.katchComm.checkProperty(
            self.tc.safetyProps[self.raceType], t2[0].policy
        )
        # harmful if one of the policies satisfies the property, but the other does not
        if res1 == res2:
            return None
        return TransCheckResult(self.raceType, pol1, t2[0].policy)


class SWCTRaceHandler(RaceHandler[PktProcTrans, RcfgTrans]):
    def __init__(self, tc: TransitionsChecker) -> None:
        super().__init__(tc, RaceType.CT_SW)
        self.handler = CTSWRaceHandler(tc)

    def validate(
        self,
        trace: List[TraceNode],
        t1: Tuple[PktProcTrans, int],
        t2: Tuple[RcfgTrans, int],
    ) -> bool:
        return self.handler.validate(trace, t2, t1)

    def check(
        self,
        trace: List[TraceNode],
        t1: Tuple[PktProcTrans, int],
        t2: Tuple[RcfgTrans, int],
    ) -> TransCheckResult | None:
        res = self.handler.check(trace, t2, t1)
        if res is not None:
            # reverse network policies to match input parameters
            return TransCheckResult(res.raceType, res.netPolicy2, res.netPolicy1)
        return res


class _RaceHandlersDict(Protocol):
    def __getitem__(
        self, item: tuple[type[_T1], type[_T2]]
    ) -> List[RaceHandler[_T1, _T2]]: ...

    def __setitem__(
        self,
        key: tuple[type[_T1], type[_T2]],
        value: List[RaceHandler[_T1, _T2]],
    ) -> None: ...

    def __contains__(self, key: tuple[type[_T1], type[_T2]]) -> bool: ...


class TransitionsChecker:
    def __init__(
        self,
        katchComm: KATchComm,
        safetyProps: dict[RaceType, str],
        elsMetadata: List[ElementMetadata],
        skippedRaces: List[RaceType] | None = None,
    ) -> None:
        self.elsMetadata = elsMetadata
        self.katchComm = katchComm
        self.safetyProps = safetyProps
        self._skipped: dict[str, int] = {}
        self._skippedRaces: List[RaceType] = (
            [] if skippedRaces is None else skippedRaces
        )
        self._skippedRaces.append(RaceType.SW_SW)

        self._handlers: _RaceHandlersDict = cast(_RaceHandlersDict, {})
        self._handlers[(PktProcTrans, PktProcTrans)] = [SWSWRaceHandler(self)]
        self._handlers[(PktProcTrans, RcfgTrans)] = [SWCTRaceHandler(self)]
        self._handlers[(RcfgTrans, PktProcTrans)] = [CTSWRaceHandler(self)]
        self._handlers[(RcfgTrans, RcfgTrans)] = [
            CTSWCTRaceHandler(self),
            CTCTSWRaceHandler(self),
        ]

    def check(
        self, trace: List[TraceNode], t1Pos: int, t2Pos: int
    ) -> TransCheckResult | None:
        t1 = trace[t1Pos].trans
        t2 = trace[t2Pos].trans
        key = (type(t1), type(t2))
        if key not in self._handlers:
            return None
        handlers = self._handlers[key]
        for handler in handlers:
            if handler.raceType in self._skippedRaces:
                self._addSkippedRace(handler.raceType)
                return None
            args = (trace, (t1, t1Pos), (t2, t2Pos))
            if handler.validate(*args):
                return handler.check(*args)
        return None

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
