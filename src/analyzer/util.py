from typing import List

from src.model.dnk_maude_model import ElementMetadata
from src.trace.node import TraceNode
from src.trace.transition import RcfgTrans
from src.util import DyNetKATSymbols as sym
from src.util import indexInBounds


def buildNetworkPolicy(fts: List[str], link: str) -> str:
    if not fts:
        return sym.ZERO
    ftsStr = f" {sym.OR} ".join(fts)
    oneStepStr = f"({ftsStr}) {sym.AND} ({link})"
    return f"({oneStepStr}) {sym.AND} ({oneStepStr}){sym.STAR}"


def reconstructElementFTs(
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
        # TODO THIS DOES NOT ACCOUNT FOR UPDATES THAT SHOULD BE APPENDED
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
