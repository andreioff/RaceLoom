from dataclasses import dataclass
from os import linesep
from typing import Callable, List, Protocol, Tuple, TypeVar, cast

from src.analyzer.harmful_trace import RaceType
from src.KATch_comm import KATchComm
from src.model.dnk_maude_model import ElementMetadata, ElementType
from src.trace.node import TraceNode
from src.trace.transition import ITransition, PktProcTrans, RcfgTrans
from src.util import DyNetKATSymbols as sym
from src.util import indexInBounds

_T1 = TypeVar("_T1", bound=ITransition)
_T2 = TypeVar("_T2", bound=ITransition)


@dataclass(frozen=True)
class TransCheckResult:
    raceType: RaceType
    netPolicy1: str
    netPolicy2: str


def _buildNetworkPolicy(fts: List[str], link: str) -> str:
    if not fts:
        return sym.ZERO
    ftsStr = f" {sym.OR} ".join(fts)
    oneStepStr = f"({ftsStr}) {sym.AND} ({link})"
    return f"({oneStepStr}) {sym.AND} ({oneStepStr}){sym.STAR}"


def _reconstructElementFTs(
    trace: List[TraceNode], elsMetadata: List[ElementMetadata], end: int, targetEl: int
) -> List[str]:
    """Iterates through the given trace up until 'end'
    and applies any reconfiguration to 'targetEl'.
    Returns the list of updated flow tables of 'targetEl'.
    """
    # tracks the flow tables of all elements throughout the trace
    fts = elsMetadata[targetEl].initialFTs.copy()
    metad = elsMetadata[targetEl]
    for node in trace[:end]:
        # anything that is not a reconfiguration to a switch is skipped
        if not isinstance(node.trans, RcfgTrans) or node.trans.dstPos != targetEl:
            continue
        ftToModify = metad.findSwitchIndex(node.trans.channel)
        if ftToModify == -1:
            raise ValueError("Could not match network switch based on rcfg channel")
        # apply the reconfiguration to the target element
        fts[ftToModify] = node.trans.policy
    return fts


def elementIsActiveInBetween(
    trace: List[TraceNode], t1Pos: int, t2Pos: int, elPos: int
) -> bool:
    n = len(trace)
    if not indexInBounds(t1Pos, n) or not indexInBounds(t2Pos, n):
        raise IndexError("Transition indices are out of bounds!")
    if t1Pos > t2Pos:
        t1Pos, t2Pos = t2Pos, t1Pos
    for i in range(t1Pos + 1, t2Pos):
        trans = trace[i].trans
        # an element is active if it is the source that triggers an action (packet
        # processing or communication with another element) or if it is the
        # target of a reconfiguration
        if trans.getSource() == elPos or trans.targetsElement(elPos):
            return True
    return False


def elementIsRcfgTargetInBetween(
    trace: List[TraceNode], t1Pos: int, t2Pos: int, elPos: int
) -> bool:
    n = len(trace)
    if not indexInBounds(t1Pos, n) or not indexInBounds(t2Pos, n):
        raise IndexError("Transition indices are out of bounds!")
    if t1Pos > t2Pos:
        t1Pos, t2Pos = t2Pos, t1Pos
    for i in range(t1Pos + 1, t2Pos):
        trans = trace[i].trans
        if trans.targetsElement(elPos):
            return True
    return False


class _TransitionCheckers(Protocol):
    def __getitem__(self, item: tuple[type[_T1], type[_T2]]) -> List[
        Callable[
            [List[TraceNode], Tuple[_T1, int], Tuple[_T2, int]],
            Tuple[TransCheckResult | None, bool],
        ]
    ]: ...

    def __setitem__(
        self,
        key: tuple[type[_T1], type[_T2]],
        value: List[
            Callable[
                [List[TraceNode], Tuple[_T1, int], Tuple[_T2, int]],
                Tuple[TransCheckResult | None, bool],
            ]
        ],
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

        self._checks: _TransitionCheckers = cast(_TransitionCheckers, {})
        self._checks[(PktProcTrans, PktProcTrans)] = [self._checkSWSW]
        self._checks[(PktProcTrans, RcfgTrans)] = [self._checkSWCT]
        self._checks[(RcfgTrans, PktProcTrans)] = [self._checkCTSW]
        self._checks[(RcfgTrans, RcfgTrans)] = [self._checkCTSWCT, self._checkCTCTSW]

    def check(
        self, trace: List[TraceNode], t1Pos: int, t2Pos: int
    ) -> TransCheckResult | None:
        t1 = trace[t1Pos].trans
        t2 = trace[t2Pos].trans
        key = (type(t1), type(t2))
        if key not in self._checks:
            return None
        checks = self._checks[key]
        for check in checks:
            res, satisfiesReqs = check(trace, (t1, t1Pos), (t2, t2Pos))
            if satisfiesReqs:
                return res
        return None

    def _checkSWSW(
        self,
        trace: List[TraceNode],
        t1: Tuple[PktProcTrans, int],
        t2: Tuple[PktProcTrans, int],
    ) -> Tuple[TransCheckResult | None, bool]:
        self._addSkippedRace(RaceType.SW_SW)
        return None, True

    def _checkCTSWCT(
        self,
        trace: List[TraceNode],
        t1: Tuple[RcfgTrans, int],
        t2: Tuple[RcfgTrans, int],
    ) -> Tuple[TransCheckResult | None, bool]:
        if RaceType.CT_SW_CT not in self.safetyProps:
            return None, False
        src1Type = self.elsMetadata[t1[0].srcPos].pType
        src2Type = self.elsMetadata[t2[0].srcPos].pType
        targetSw1Id = self.elsMetadata[t1[0].dstPos].pID
        targetSw2Id = self.elsMetadata[t2[0].dstPos].pID
        if not (
            targetSw1Id == targetSw2Id
            and src1Type == ElementType.CT
            and src2Type == ElementType.CT
            and not elementIsActiveInBetween(trace, t1[1], t2[1], t1[0].srcPos)
            and not elementIsRcfgTargetInBetween(trace, t1[1], t2[1], t1[0].dstPos)
        ):
            return None, False

        if RaceType.CT_SW_CT in self._skippedRaces:
            self._addSkippedRace(RaceType.CT_SW_CT)
            return None, True

        # Reconstruction is done up to the rcfg (possibly including the other rcfg
        # as well!). This is because not all pairs of racing rcfgs may be harmful,
        # e.g. when the rcfgs target different flow tables of the same element.
        swFts = _reconstructElementFTs(trace, self.elsMetadata, t1[1], t1[0].dstPos)
        pol1 = self._reconstructRcfg(swFts, t1[0].policy, t1[0].dstPos, t1[0].channel)
        swFts = _reconstructElementFTs(trace, self.elsMetadata, t2[1], t2[0].dstPos)
        pol2 = self._reconstructRcfg(swFts, t2[0].policy, t2[0].dstPos, t2[0].channel)

        # harmful if the new policy of CT1 is not equivalent to the new policy from CT2
        res1 = self.katchComm.checkProperty(self.safetyProps[RaceType.CT_SW_CT], pol1)
        res2 = self.katchComm.checkProperty(self.safetyProps[RaceType.CT_SW_CT], pol2)
        if not (res1 ^ res2):
            return None, True
        return TransCheckResult(RaceType.CT_SW_CT, pol1, pol2), True

    def _checkCTCTSW(
        self,
        trace: List[TraceNode],
        t1: Tuple[RcfgTrans, int],
        t2: Tuple[RcfgTrans, int],
    ) -> Tuple[TransCheckResult | None, bool]:
        if RaceType.CT_CT_SW not in self.safetyProps:
            return None, False
        swapped = False
        if t1[1] > t2[1]:
            t1, t2 = t2, t1
            swapped = True

        src1 = self.elsMetadata[t1[0].srcPos]
        src2 = self.elsMetadata[t2[0].srcPos]
        dst1 = self.elsMetadata[t1[0].dstPos]
        dst2 = self.elsMetadata[t2[0].dstPos]

        if not (
            src1.pType == ElementType.CT
            and dst1.pType == ElementType.SW
            and src2.pType == ElementType.CT
            and dst2.pType == ElementType.CT
            and src1.pID == dst2.pID
            and not elementIsActiveInBetween(trace, t1[1], t2[1], t1[0].srcPos)
            and not elementIsRcfgTargetInBetween(trace, t1[1], t2[1], t1[0].dstPos)
        ):
            return None, False

        if RaceType.CT_CT_SW in self._skippedRaces:
            self._addSkippedRace(RaceType.CT_CT_SW)
            return None, True

        ct1Rcfg, ct2Rcfg, sw = t1[0], t2[0], t1[0].dstPos
        swFts = _reconstructElementFTs(trace, self.elsMetadata, min(t1[1], t2[1]), sw)
        pol1 = self._reconstructRcfg(swFts, ct1Rcfg.policy, sw, ct1Rcfg.channel)
        pol2 = self._reconstructRcfg(swFts, ct2Rcfg.policy, sw, ct1Rcfg.channel)

        # harmful if the new policy of the updating controller (t2) does not cover
        # the same packets as the new policy installed on the switch by the
        # updated controller (t1)
        res1 = self.katchComm.checkProperty(self.safetyProps[RaceType.CT_CT_SW], pol1)
        res2 = self.katchComm.checkProperty(self.safetyProps[RaceType.CT_CT_SW], pol2)
        if not (res1 and (not res2)):
            return None, True
        if swapped:
            return TransCheckResult(RaceType.CT_CT_SW, pol2, pol1), True
        return TransCheckResult(RaceType.CT_CT_SW, pol1, pol2), True

    def _checkSWCT(
        self,
        trace: List[TraceNode],
        t1: Tuple[PktProcTrans, int],
        t2: Tuple[RcfgTrans, int],
    ) -> Tuple[TransCheckResult | None, bool]:
        res, satisfiesReqs = self._checkCTSW(trace, t2, t1)
        if res is not None:
            # reverse network policies to match input parameters
            res = TransCheckResult(res.raceType, res.netPolicy2, res.netPolicy1)
        return res, satisfiesReqs

    def _checkCTSW(
        self,
        trace: List[TraceNode],
        t1: Tuple[RcfgTrans, int],
        t2: Tuple[PktProcTrans, int],
    ) -> Tuple[TransCheckResult | None, bool]:
        if RaceType.CT_SW not in self.safetyProps:
            return None, False
        targetSwId = self.elsMetadata[t1[0].dstPos].pID
        srcSwId = self.elsMetadata[t2[0].swPos].pID
        rcfgSrcType = self.elsMetadata[t1[0].srcPos].pType
        if not (
            targetSwId == srcSwId
            and rcfgSrcType == ElementType.CT
            and not elementIsActiveInBetween(trace, t1[1], t2[1], t2[0].swPos)
        ):
            return None, False

        if RaceType.CT_SW in self._skippedRaces:
            self._addSkippedRace(RaceType.CT_SW)
            return None, True

        swFts = _reconstructElementFTs(trace, self.elsMetadata, t1[1], t1[0].dstPos)
        pol1 = self._reconstructRcfg(swFts, t1[0].policy, t1[0].dstPos, t1[0].channel)
        # harmful if the new policy does not cover the same packets
        # covered by the current policy of the switch
        res1 = self.katchComm.checkProperty(self.safetyProps[RaceType.CT_SW], pol1)
        res2 = self.katchComm.checkProperty(
            self.safetyProps[RaceType.CT_SW], t2[0].policy
        )
        if not ((not res1) and res2):
            return None, True
        return TransCheckResult(RaceType.CT_SW, pol1, t2[0].policy), True

    def _reconstructRcfg(
        self, fts: List[str], policy: str, targetEl: int, targetFTChannel: str
    ) -> str:
        """
        If the given node position does not contain a rcfg transition, it
        returns the policy of the node's transition.
        """
        targetFt = self.elsMetadata[targetEl].findSwitchIndex(targetFTChannel)
        if targetFt == -1:
            raise ValueError("Could not match network switch based on rcfg channel")
        fts[targetFt] = policy
        return _buildNetworkPolicy(fts, self.elsMetadata[targetEl].link)

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
