from typing import List

import pytest

from src.analyzer.trace_analyzer import RaceType
from src.analyzer.transition_checker import (elementIsActiveInBetween,
                                             elementIsRcfgTargetInBetween)
from src.trace.node import TraceNode
from src.trace.transition import (ITransition, PktProcTrans, RcfgTrans,
                                  TraceTransition)
from src.util import DyNetKATSymbols as sym

pytest_plugins = [
    "test.src.test_utils.fixtures",
    "test.src.analyzer.test_utils.fixtures",
]

# position of elements in metadata list
_SW1 = 0
_SW2 = 1
_CT1 = 2
_CT2 = 3
_CT3 = 4


def _makeTrace(*transitions: ITransition) -> TraceNode:
    trace: List[TraceNode] = []
    for t in transitions:
        trace.append(TraceNode(t, []))
    return trace


def test_elementIsActiveInBetween_out_of_bounds_left_end_raises_error(
    transChecker2SW2CT, flowRule1, flowRule3
):
    t1 = PktProcTrans(flowRule1, _SW1)
    t2 = PktProcTrans(flowRule1, _SW2)
    t3 = PktProcTrans(flowRule1, _SW2)
    trace = _makeTrace(t1, t2, t3)
    with pytest.raises(IndexError):
        elementIsActiveInBetween(trace, -1, 2, _SW1)


def test_elementIsActiveInBetween_out_of_bounds_right_end_raises_error(
    transChecker2SW2CT, flowRule1, flowRule3
):
    t1 = PktProcTrans(flowRule1, _SW1)
    t2 = PktProcTrans(flowRule1, _SW2)
    t3 = PktProcTrans(flowRule1, _SW2)
    trace = _makeTrace(t1, t2, t3)
    with pytest.raises(IndexError):
        elementIsActiveInBetween(trace, 0, 3, _SW1)


def test_elementIsActiveInBetween_inactive_switch_returns_False(
    transChecker2SW2CT, flowRule1, flowRule3
):
    t1 = PktProcTrans(flowRule1, _SW1)
    t2 = PktProcTrans("policy", _SW2)
    t3 = RcfgTrans(flowRule1, _CT1, _SW2, "ch")
    t4 = RcfgTrans(flowRule3, _CT1, _SW1, "ch")
    trace = _makeTrace(t1, t2, t3, t4)
    res = elementIsActiveInBetween(trace, 0, 3, _SW1)
    assert res is False


def test_elementIsActiveInBetween_switch_processes_packet_returns_True(
    transChecker2SW2CT, flowRule1, flowRule3
):
    t1 = PktProcTrans(flowRule1, _SW1)
    T = PktProcTrans("policy", _SW1)
    t2 = RcfgTrans(flowRule3, _CT1, _SW1, "ch")
    trace = _makeTrace(t1, T, t2)
    res = elementIsActiveInBetween(trace, 0, 2, _SW1)
    assert res is True


def test_elementIsActiveInBetween_switch_sends_rcfg_returns_True(
    transChecker2SW2CT, flowRule1, flowRule3
):
    t1 = PktProcTrans(flowRule1, _SW1)
    t2 = PktProcTrans(flowRule1, _SW2)
    T = RcfgTrans("policy", _SW1, _CT2, "ch")
    t3 = PktProcTrans(flowRule1, _SW2)
    t4 = RcfgTrans(flowRule3, _CT1, _SW1, "ch")
    trace = _makeTrace(t1, t2, T, t3, t4)
    res = elementIsActiveInBetween(trace, 0, 4, _SW1)
    assert res is True


def test_elementIsActiveInBetween_switch_receives_rcfg_returns_True(
    transChecker2SW2CT, flowRule1, flowRule3
):
    t1 = PktProcTrans(flowRule1, _SW1)
    t2 = PktProcTrans(flowRule1, _SW2)
    T = RcfgTrans("policy", _CT1, _SW1, "ch")
    t3 = PktProcTrans(flowRule1, _SW2)
    t4 = RcfgTrans(flowRule3, _CT1, _SW1, "ch")
    trace = _makeTrace(t1, t2, T, t3, t4)
    res = elementIsActiveInBetween(trace, 0, 4, _SW1)
    assert res is True


def test_elementIsActiveInBetween_controller_sends_rcfg_returns_True(
    transChecker2SW2CT, flowRule1, flowRule3
):
    t1 = PktProcTrans(flowRule1, _SW1)
    t2 = PktProcTrans(flowRule1, _SW2)
    T = RcfgTrans("policy", _CT1, _SW1, "ch")
    t3 = PktProcTrans(flowRule1, _SW2)
    t4 = RcfgTrans(flowRule3, _CT1, _SW1, "ch")
    trace = _makeTrace(t1, t2, T, t3, t4)
    res = elementIsActiveInBetween(trace, 0, 4, _CT1)
    assert res is True


def test_elementIsRcfgTargetInBetween_out_of_bounds_left_end_raises_error(
    transChecker2SW2CT, flowRule1, flowRule3
):
    t1 = PktProcTrans(flowRule1, _SW1)
    t2 = PktProcTrans(flowRule1, _SW2)
    t3 = PktProcTrans(flowRule1, _SW2)
    trace = _makeTrace(t1, t2, t3)
    with pytest.raises(IndexError):
        elementIsRcfgTargetInBetween(trace, -1, 2, _SW1)


def test_elementIsRcfgTargetInBetween_out_of_bounds_right_end_raises_error(
    transChecker2SW2CT, flowRule1, flowRule3
):
    t1 = PktProcTrans(flowRule1, _SW1)
    t2 = PktProcTrans(flowRule1, _SW2)
    t3 = PktProcTrans(flowRule1, _SW2)
    trace = _makeTrace(t1, t2, t3)
    with pytest.raises(IndexError):
        elementIsRcfgTargetInBetween(trace, 0, 3, _SW1)


def test_elementIsRcfgTargetInBetween_switch_processes_packet_returns_False(
    transChecker2SW2CT, flowRule1, flowRule3
):
    t1 = PktProcTrans(flowRule1, _SW1)
    t2 = PktProcTrans(flowRule1, _SW2)
    T = PktProcTrans(flowRule1, _SW1)
    t3 = PktProcTrans(flowRule1, _SW2)
    t4 = RcfgTrans(flowRule3, _CT1, _SW1, "ch")
    trace = _makeTrace(t1, t2, T, t3, t4)
    res = elementIsRcfgTargetInBetween(trace, 0, 4, _SW1)
    assert res is False


def test_elementIsRcfgTargetInBetween_switch_sends_rcfg_returns_False(
    transChecker2SW2CT, flowRule1, flowRule3
):
    t1 = PktProcTrans(flowRule1, _SW1)
    t2 = PktProcTrans(flowRule1, _SW2)
    T = RcfgTrans("", _SW1, _CT1, "ch")
    t3 = PktProcTrans(flowRule1, _SW2)
    t4 = RcfgTrans(flowRule3, _CT1, _SW1, "ch")
    trace = _makeTrace(t1, t2, T, t3, t4)
    res = elementIsRcfgTargetInBetween(trace, 0, 4, _SW1)
    assert res is False


def test_elementIsRcfgTargetInBetween_switch_receives_rcfg_returns_True(
    transChecker2SW2CT, flowRule1, flowRule3
):
    t1 = PktProcTrans(flowRule1, _SW1)
    t2 = PktProcTrans(flowRule1, _SW2)
    T = RcfgTrans("", _CT1, _SW1, "ch")
    t3 = PktProcTrans(flowRule1, _SW2)
    t4 = RcfgTrans(flowRule3, _CT1, _SW1, "ch")
    trace = _makeTrace(t1, t2, T, t3, t4)
    res = elementIsRcfgTargetInBetween(trace, 0, 4, _SW1)
    assert res is True


def test_checkCTSWCT_different_target_switches_returns_none(
    transChecker2SW2CT, flowRule1, flowRule2
):
    t1 = RcfgTrans(flowRule1, _CT1, _SW1, "ch")
    t2 = RcfgTrans(flowRule2, _CT2, _SW2, "ch")
    trace = _makeTrace(t1, t2)
    result = transChecker2SW2CT._checkCTSWCT(trace, (t1, 0), (t2, 1))
    assert result == (None, False)


def test_checkCTSWCT_switch_rcfg_source_returns_none(
    transChecker2SW2CT, flowRule1, flowRule2
):
    t1 = RcfgTrans(flowRule1, _SW2, _SW1, "ch")
    t2 = RcfgTrans(flowRule2, _CT2, _SW2, "ch")
    trace = _makeTrace(t1, t2)
    result = transChecker2SW2CT._checkCTSWCT(trace, (t1, 0), (t2, 1))
    assert result == (None, False)


def test_checkCTSWCT_switch_rcfg_source_returns_none2(
    transChecker2SW2CT, flowRule1, flowRule2
):
    t1 = RcfgTrans(flowRule1, _CT2, _SW1, "ch")
    t2 = RcfgTrans(flowRule2, _SW1, _SW2, "ch")
    trace = _makeTrace(t1, t2)
    result = transChecker2SW2CT._checkCTSWCT(trace, (t1, 0), (t2, 1))
    assert result == (None, False)


def test_checkCTSWCT_active_first_controller_in_between_returns_none(
    transChecker2SW2CT, flowRule1, flowRule2
):
    t1 = RcfgTrans(flowRule1, _CT2, _SW1, "ch")
    dummyT = RcfgTrans(flowRule1, _CT2, _SW2, "ch")
    t2 = RcfgTrans(flowRule2, _CT1, _SW1, "ch")
    trace = _makeTrace(t1, dummyT, t2)
    result = transChecker2SW2CT._checkCTSWCT(trace, (t1, 0), (t2, 2))
    assert result == (None, False)


def test_checkCTSWCT_active_first_controller_in_between_returns_none2(
    transChecker2SW2CT, flowRule1, flowRule2
):
    t1 = RcfgTrans(flowRule1, _CT2, _SW1, "ch")
    dummyT = RcfgTrans(flowRule1, _SW2, _CT2, "ch")
    t2 = RcfgTrans(flowRule2, _CT1, _SW1, "ch")
    trace = _makeTrace(t1, dummyT, t2)
    result = transChecker2SW2CT._checkCTSWCT(trace, (t1, 0), (t2, 2))
    assert result == (None, False)


def test_checkCTSWCT_switch_is_rcfg_target_in_between_returns_none(
    transChecker2SW2CT, flowRule1, flowRule2
):
    t1 = RcfgTrans(flowRule1, _CT2, _SW1, "ch")
    dummyT = RcfgTrans(flowRule1, _CT2, _SW1, "ch")
    t2 = RcfgTrans(flowRule2, _CT1, _SW1, "ch")
    trace = _makeTrace(t1, dummyT, t2)
    result = transChecker2SW2CT._checkCTSWCT(trace, (t1, 0), (t2, 2))
    assert result == (None, False)


def test_checkCTSWCT_valid_rcfgs_not_equivalent_policies_returns_race(
    transChecker2SW2CT, flowRule1, flowRule2
):
    t1 = RcfgTrans(flowRule1, _CT1, _SW1, "ch")
    dummyT = PktProcTrans("", _SW1)
    t2 = RcfgTrans(flowRule2, _CT2, _SW1, "ch")
    trace = _makeTrace(t1, dummyT, t2)
    result = transChecker2SW2CT._checkCTSWCT(trace, (t1, 0), (t2, 2))
    assert result == (RaceType.CT_SW_CT, True)


def test_checkCTSWCT_valid_rcfgs_equivalent_policies_returns_none(
    transChecker2SW2CT, flowRule1, flowRule3
):
    t1 = RcfgTrans(flowRule1 + sym.OR + flowRule3, _CT1, _SW2, "ch")
    dummyT = RcfgTrans("", _SW1, _CT2, "ch")
    dummyT2 = RcfgTrans("", _CT2, _SW1, "ch")
    t2 = RcfgTrans(flowRule3 + sym.OR + flowRule1, _CT2, _SW2, "ch")
    trace = _makeTrace(t1, dummyT, dummyT2, t2)
    result = transChecker2SW2CT._checkCTSWCT(trace, (t1, 0), (t2, 3))
    assert result == (None, True)


def test_checkCTCTSW_switch_rcfg_source_returns_none(
    transChecker2SW2CT, flowRule1, flowRule2
):
    t1 = RcfgTrans(flowRule1, _SW2, _SW1, "ch")
    t2 = RcfgTrans(flowRule2, _CT2, _CT1, "ch")
    trace = _makeTrace(t1, t2)
    result = transChecker2SW2CT._checkCTCTSW(trace, (t1, 0), (t2, 1))
    assert result == (None, False)


def test_checkCTCTSW_switch_rcfg_source_returns_none2(
    transChecker2SW2CT, flowRule1, flowRule2
):
    t1 = RcfgTrans(flowRule1, _CT1, _SW1, "ch")
    t2 = RcfgTrans(flowRule2, _SW2, _CT1, "ch")
    trace = _makeTrace(t1, t2)
    result = transChecker2SW2CT._checkCTCTSW(trace, (t1, 0), (t2, 1))
    assert result == (None, False)


def test_checkCTCTSW_both_rcfg_destinations_are_switches_returns_none(
    transChecker2SW2CT, flowRule1, flowRule2
):
    t1 = RcfgTrans(flowRule1, _CT1, _SW1, "ch")
    t2 = RcfgTrans(flowRule2, _CT2, _SW2, "ch")
    trace = _makeTrace(t1, t2)
    result = transChecker2SW2CT._checkCTCTSW(trace, (t1, 0), (t2, 1))
    assert result == (None, False)


def test_checkCTCTSW_different_source_and_destination_controller_returns_none(
    transChecker2SW3CT, flowRule1, flowRule2
):
    t1 = RcfgTrans(flowRule1, _CT1, _CT2, "ch")
    t2 = RcfgTrans(flowRule2, _CT3, _SW2, "ch")
    trace = _makeTrace(t1, t2)
    result = transChecker2SW3CT._checkCTCTSW(trace, (t1, 0), (t2, 1))
    assert result == (None, False)


def test_checkCTCTSW_no_switch_destination_returns_none(
    transChecker2SW3CT, flowRule1, flowRule2
):
    t1 = RcfgTrans(flowRule1, _CT1, _CT2, "ch")
    t2 = RcfgTrans(flowRule2, _CT3, _CT1, "ch")
    trace = _makeTrace(t1, t2)
    result = transChecker2SW3CT._checkCTCTSW(trace, (t1, 0), (t2, 1))
    assert result == (None, False)


def test_checkCTCTSW_active_first_controller_in_between_returns_none(
    transChecker2SW3CT, flowRule1, flowRule2
):
    t1 = RcfgTrans(flowRule1, _CT1, _SW1, "ch")
    dummyT = RcfgTrans(flowRule1, _CT1, _SW2, "ch")
    t2 = RcfgTrans(flowRule2, _CT2, _CT1, "ch")
    trace = _makeTrace(t1, dummyT, t2)
    result = transChecker2SW3CT._checkCTCTSW(trace, (t1, 0), (t2, 2))
    assert result == (None, False)


def test_checkCTCTSW_active_first_controller_in_between_returns_none2(
    transChecker2SW3CT, flowRule1, flowRule2
):
    t1 = RcfgTrans(flowRule1, _CT1, _SW1, "ch")
    dummyT = RcfgTrans(flowRule1, _SW2, _CT1, "ch")
    t2 = RcfgTrans(flowRule2, _CT2, _CT1, "ch")
    trace = _makeTrace(t1, dummyT, t2)
    result = transChecker2SW3CT._checkCTCTSW(trace, (t1, 0), (t2, 2))
    assert result == (None, False)


def test_checkCTCTSW_switch_is_rcfg_target_in_between_returns_none(
    transChecker2SW3CT, flowRule1, flowRule2
):
    t1 = RcfgTrans(flowRule1, _CT1, _SW1, "ch")
    dummyT = RcfgTrans(flowRule1, _CT3, _SW1, "ch")
    t2 = RcfgTrans(flowRule2, _CT2, _CT1, "ch")
    trace = _makeTrace(t1, dummyT, t2)
    result = transChecker2SW3CT._checkCTCTSW(trace, (t1, 0), (t2, 2))
    assert result == (None, False)


def test_checkCTCTSW_valid_rcfgs_non_empty_policy_difference_returns_race(
    transChecker2SW2CT, flowRule1, flowRule2
):
    t1 = RcfgTrans(flowRule1, _CT1, _SW1, "ch")
    dummyT = PktProcTrans("", _SW1)
    t2 = RcfgTrans(flowRule2, _CT2, _CT1, "ch")
    trace = _makeTrace(t1, dummyT, t2)
    result = transChecker2SW2CT._checkCTCTSW(trace, (t1, 0), (t2, 2))
    assert result == (RaceType.CT_CT_SW, True)


def test_checkCTCTSW_valid_rcfgs_empty_policy_difference_returns_none(
    transChecker2SW2CT, flowRule1, flowRule3
):
    t1 = RcfgTrans(flowRule1, _CT1, _SW2, "ch")
    dummyT = RcfgTrans("", _SW1, _CT2, "ch")
    # second controller should be allowed to perform actions in between
    # as long as they do not target the switch or controller involved
    dummyT2 = RcfgTrans("", _CT2, _SW1, "ch")
    t2 = RcfgTrans(flowRule3 + sym.OR + flowRule1, _CT2, _CT1, "ch")
    trace = _makeTrace(t1, dummyT, dummyT2, t2)
    result = transChecker2SW2CT._checkCTCTSW(trace, (t1, 0), (t2, 3))
    assert result == (None, True)


def test_checkCTSW_different_target_switch_returns_none(
    transChecker2SW2CT, flowRule1, flowRule3
):
    t1 = PktProcTrans(flowRule1 + sym.OR + flowRule3, _SW1)
    t2 = RcfgTrans(flowRule3 + sym.OR + flowRule1, _CT2, _SW2, "ch")
    trace = _makeTrace(t1, t2)
    res2 = transChecker2SW2CT._checkCTSW(trace, (t2, 1), (t1, 0))
    res1 = transChecker2SW2CT._checkSWCT(trace, (t1, 0), (t2, 1))
    assert res1 == (None, False)
    assert res2 == (None, False)


def test_checkCTSW_switch_rcfg_source_returns_none(
    transChecker2SW2CT, flowRule1, flowRule3
):
    t1 = PktProcTrans(flowRule1 + sym.OR + flowRule3, _SW1)
    t2 = RcfgTrans(flowRule3 + sym.OR + flowRule1, _SW1, _SW2, "ch")
    trace = _makeTrace(t1, t2)
    res2 = transChecker2SW2CT._checkCTSW(trace, (t2, 1), (t1, 0))
    res1 = transChecker2SW2CT._checkSWCT(trace, (t1, 0), (t2, 1))
    assert res1 == (None, False)
    assert res2 == (None, False)


def test_checkCTSW_active_src_switch_in_between_transitions_returns_none(
    transChecker2SW2CT, flowRule1, flowRule3
):
    t1 = PktProcTrans(flowRule1 + sym.OR + flowRule3, _SW1)
    dummyT = PktProcTrans("policy", _SW1)
    t2 = RcfgTrans(flowRule3 + sym.OR + flowRule1, _CT1, _SW1, "ch")
    trace = _makeTrace(t1, dummyT, t2)
    res2 = transChecker2SW2CT._checkCTSW(trace, (t2, 2), (t1, 0))
    res1 = transChecker2SW2CT._checkSWCT(trace, (t1, 0), (t2, 2))
    assert res1 == (None, False)
    assert res2 == (None, False)


def test_checkCTSW_active_src_switch_in_between_transitions_returns_none2(
    transChecker2SW2CT, flowRule1, flowRule3
):
    t1 = PktProcTrans(flowRule1 + sym.OR + flowRule3, _SW1)
    dummyT = RcfgTrans("policy", _SW1, _CT2, "ch")
    t2 = RcfgTrans(flowRule3 + sym.OR + flowRule1, _CT1, _SW1, "ch")
    trace = _makeTrace(t1, dummyT, t2)
    res2 = transChecker2SW2CT._checkCTSW(trace, (t2, 2), (t1, 0))
    res1 = transChecker2SW2CT._checkSWCT(trace, (t1, 0), (t2, 2))
    assert res1 == (None, False)
    assert res2 == (None, False)


def test_checkCTSW_valid_transitions_empty_policy_difference_returns_none(
    transChecker2SW2CT, flowRule1, flowRule2, flowRule3
):
    t1 = PktProcTrans(flowRule1 + sym.OR + flowRule3, _SW1)
    dummyT = RcfgTrans("", _SW2, _CT1, "ch")
    dummyT2 = RcfgTrans("", _CT1, _SW2, "ch")
    t2 = RcfgTrans(
        flowRule2 + sym.OR + flowRule3 + sym.OR + flowRule1, _CT1, _SW1, "ch"
    )
    trace = _makeTrace(t1, dummyT, dummyT2, t2)
    res2 = transChecker2SW2CT._checkCTSW(trace, (t2, 3), (t1, 0))
    res1 = transChecker2SW2CT._checkSWCT(trace, (t1, 0), (t2, 3))
    assert res1 == (None, True)
    assert res2 == (None, True)


def test_checkCTSW_valid_transitions_non_empty_policy_difference_returns_race(
    transChecker2SW2CT, flowRule1, flowRule2, flowRule3
):
    t1 = PktProcTrans(flowRule2 + sym.OR + flowRule3, _SW1)
    dummyT = RcfgTrans("", _CT1, _SW2, "ch")
    t2 = RcfgTrans(flowRule3 + sym.OR + flowRule1, _CT1, _SW1, "ch")
    trace = _makeTrace(t1, dummyT, t2)
    res2 = transChecker2SW2CT._checkCTSW(trace, (t2, 2), (t1, 0))
    res1 = transChecker2SW2CT._checkSWCT(trace, (t1, 0), (t2, 2))
    assert res1 == (RaceType.CT_SW, True)
    assert res2 == (RaceType.CT_SW, True)


def test_skipped_races_are_counted(transChecker2SW2CT, flowRule1, flowRule2):
    for _i in range(2):
        transChecker2SW2CT._addSkippedRace(RaceType.SW_SW)
        transChecker2SW2CT._addSkippedRace(RaceType.CT_CT_SW)
        transChecker2SW2CT._addSkippedRace(RaceType.CT_SW_CT)
        transChecker2SW2CT._addSkippedRace(RaceType.CT_SW)
    res = transChecker2SW2CT.getSkippedRacesStr("\t")
    assert res == (
        f"\t{RaceType.SW_SW}: 2 times\n"
        f"\t{RaceType.CT_CT_SW}: 2 times\n"
        f"\t{RaceType.CT_SW_CT}: 2 times\n"
        f"\t{RaceType.CT_SW}: 2 times"
    )


def test_check_transition_pair_without_check_returns_none(transChecker2SW2CT):
    t1 = PktProcTrans("", _SW1)
    t2 = TraceTransition()
    trace = _makeTrace(t1, t2)
    res = transChecker2SW2CT.check(trace, 0, 1)
    assert res is None
    assert transChecker2SW2CT.getSkippedRacesStr() == ""


def test_check_processing_and_rcfg_transitions_returns_CT_SW_race(
    transChecker2SW2CT, flowRule1, flowRule2
):
    t1 = PktProcTrans(flowRule1, _SW1)
    t2 = RcfgTrans(flowRule2, _CT1, _SW1, "ch")
    trace = _makeTrace(t1, t2)
    res1 = transChecker2SW2CT.check(trace, 0, 1)
    res2 = transChecker2SW2CT.check(trace, 1, 0)
    assert res1 is RaceType.CT_SW
    assert res2 is RaceType.CT_SW
    assert transChecker2SW2CT.getSkippedRacesStr() == ""


def test_check_processing_and_rcfg_transitions_returns_none(
    transChecker2SW2CT, flowRule1
):
    t1 = PktProcTrans(flowRule1, _SW1)
    t2 = RcfgTrans(flowRule1, _CT1, _SW1, "ch")
    trace = _makeTrace(t1, t2)
    res1 = transChecker2SW2CT.check(trace, 0, 1)
    res2 = transChecker2SW2CT.check(trace, 1, 0)
    assert res1 is None
    assert res2 is None
    assert transChecker2SW2CT.getSkippedRacesStr() == ""


def test_check_CT_SW_CT_rcfg_transitions_returns_race(
    transChecker2SW2CT, flowRule1, flowRule2
):
    t1 = RcfgTrans(flowRule1, _CT1, _SW1, "ch")
    t2 = RcfgTrans(flowRule2, _CT2, _SW1, "ch")
    trace = _makeTrace(t1, t2)
    res = transChecker2SW2CT.check(trace, 0, 1)
    assert res is RaceType.CT_SW_CT
    assert transChecker2SW2CT.getSkippedRacesStr() == ""


def test_check_CT_SW_CT_rcfg_transitions_returns_none(transChecker2SW2CT, flowRule1):
    t1 = RcfgTrans(flowRule1, _CT1, _SW1, "ch")
    t2 = RcfgTrans(flowRule1, _CT2, _SW1, "ch")
    trace = _makeTrace(t1, t2)
    res = transChecker2SW2CT.check(trace, 0, 1)
    assert res is None
    assert transChecker2SW2CT.getSkippedRacesStr() == ""


def test_check_CT_CT_SW_rcfg_transitions_returns_race(
    transChecker2SW2CT, flowRule1, flowRule2
):
    t1 = RcfgTrans(flowRule1, _CT1, _SW1, "ch")
    t2 = RcfgTrans(flowRule2, _CT2, _CT1, "ch")
    trace = _makeTrace(t1, t2)
    res = transChecker2SW2CT.check(trace, 0, 1)
    assert res is RaceType.CT_CT_SW
    assert transChecker2SW2CT.getSkippedRacesStr() == ""


def test_check_CT_CT_SW_rcfg_transitions_returns_none(transChecker2SW2CT, flowRule1):
    t1 = RcfgTrans(flowRule1, _CT2, _CT1, "ch")
    t2 = RcfgTrans(flowRule1, _CT1, _SW1, "ch")
    trace = _makeTrace(t1, t2)
    res = transChecker2SW2CT.check(trace, 1, 0)
    assert res is None
    assert transChecker2SW2CT.getSkippedRacesStr() == ""


def test_check_SWSW_race_is_skipped_returns_none(transChecker2SW2CT, flowRule1):
    t1 = PktProcTrans(flowRule1, _SW1)
    trace = _makeTrace(t1, t1)
    res = transChecker2SW2CT.check(trace, 0, 1)
    assert res is None
    assert transChecker2SW2CT.getSkippedRacesStr() == f"{RaceType.SW_SW}: 1 times"


def test_check_all_races_skipped_returns_none(
    transCheckerAllSkipped, flowRule1, flowRule2, flowRule3
):
    t1 = PktProcTrans(flowRule1, _SW1)
    t2 = RcfgTrans(flowRule2, _CT1, _SW1, "ch")
    t3 = RcfgTrans(flowRule3, _CT2, _SW1, "ch")
    t4 = RcfgTrans(flowRule3, _CT2, _CT1, "ch")
    #                SW SW  | CT SW CT |  CT SW  | CT CT SW
    for tt1, tt2 in [(t1, t1), (t2, t3), (t2, t1), (t2, t4)]:
        trace = _makeTrace(tt1, tt2)
        res = transCheckerAllSkipped.check(trace, 0, 1)
        assert res is None
    assert transCheckerAllSkipped.getSkippedRacesStr() == (
        f"{RaceType.SW_SW}: 1 times\n"
        f"{RaceType.CT_SW_CT}: 1 times\n"
        f"{RaceType.CT_SW}: 1 times\n"
        f"{RaceType.CT_CT_SW}: 1 times"
    )
