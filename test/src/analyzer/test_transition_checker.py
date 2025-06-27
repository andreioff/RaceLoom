from test.src.analyzer.test_utils.util import raceSafetyDict
from typing import List

import pytest

from src.analyzer.trace_analyzer import RaceType
from src.analyzer.transition_checker import (TransCheckResult,
                                             TransitionsChecker,
                                             elementIsActiveInBetween,
                                             elementIsRcfgTargetInBetween)
from src.trace.node import TraceNode
from src.trace.transition import (ITransition, PktProcTrans, RcfgTrans,
                                  TraceTransition)

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

_inSW1 = 0
_inSW2 = 1


def _makeTrace(*transitions: ITransition) -> TraceNode:
    trace: List[TraceNode] = []
    for t in transitions:
        trace.append(TraceNode(t, []))
    return trace


def test_elementIsActiveInBetween_out_of_bounds_left_end_raises_error(safetyProp1):
    frs = safetyProp1.passingFlowRules
    t1 = PktProcTrans(frs[0], _SW1)
    t2 = PktProcTrans(frs[1], _SW2)
    t3 = PktProcTrans(frs[0], _SW2)
    trace = _makeTrace(t1, t2, t3)
    with pytest.raises(IndexError):
        elementIsActiveInBetween(trace, -1, 2, _SW1)


def test_elementIsActiveInBetween_out_of_bounds_right_end_raises_error(safetyProp1):
    frs = safetyProp1.passingFlowRules
    t1 = PktProcTrans(frs[0], _SW1)
    t2 = PktProcTrans(frs[0], _SW2)
    t3 = PktProcTrans(frs[0], _SW2)
    trace = _makeTrace(t1, t2, t3)
    with pytest.raises(IndexError):
        elementIsActiveInBetween(trace, 0, 3, _SW1)


def test_elementIsActiveInBetween_inactive_switch_returns_False(safetyProp1):
    frs = safetyProp1.passingFlowRules
    t1 = PktProcTrans(frs[0], _SW1)
    t2 = PktProcTrans("policy", _SW2)
    t3 = RcfgTrans(frs[0], _CT1, _SW2, "ch")
    t4 = RcfgTrans(frs[2], _CT1, _SW1, "ch")
    trace = _makeTrace(t1, t2, t3, t4)
    res = elementIsActiveInBetween(trace, 0, 3, _SW1)
    assert res is False


def test_elementIsActiveInBetween_switch_processes_packet_returns_True(safetyProp1):
    frs = safetyProp1.passingFlowRules
    t1 = PktProcTrans(frs[0], _SW1)
    T = PktProcTrans("policy", _SW1)
    t2 = RcfgTrans(frs[2], _CT1, _SW1, "ch")
    trace = _makeTrace(t1, T, t2)
    res = elementIsActiveInBetween(trace, 0, 2, _SW1)
    assert res is True


def test_elementIsActiveInBetween_switch_sends_rcfg_returns_True(safetyProp1):
    frs = safetyProp1.passingFlowRules
    t1 = PktProcTrans(frs[0], _SW1)
    t2 = PktProcTrans(frs[0], _SW2)
    T = RcfgTrans("policy", _SW1, _CT2, "ch")
    t3 = PktProcTrans(frs[0], _SW2)
    t4 = RcfgTrans(frs[2], _CT1, _SW1, "ch")
    trace = _makeTrace(t1, t2, T, t3, t4)
    res = elementIsActiveInBetween(trace, 0, 4, _SW1)
    assert res is True


def test_elementIsActiveInBetween_switch_receives_rcfg_returns_True(safetyProp1):
    frs = safetyProp1.passingFlowRules
    t1 = PktProcTrans(frs[0], _SW1)
    t2 = PktProcTrans(frs[0], _SW2)
    T = RcfgTrans("policy", _CT1, _SW1, "ch")
    t3 = PktProcTrans(frs[0], _SW2)
    t4 = RcfgTrans(frs[2], _CT1, _SW1, "ch")
    trace = _makeTrace(t1, t2, T, t3, t4)
    res = elementIsActiveInBetween(trace, 0, 4, _SW1)
    assert res is True


def test_elementIsActiveInBetween_controller_sends_rcfg_returns_True(safetyProp1):
    frs = safetyProp1.passingFlowRules
    t1 = PktProcTrans(frs[0], _SW1)
    t2 = PktProcTrans(frs[0], _SW2)
    T = RcfgTrans("policy", _CT1, _SW1, "ch")
    t3 = PktProcTrans(frs[0], _SW2)
    t4 = RcfgTrans(frs[2], _CT1, _SW1, "ch")
    trace = _makeTrace(t1, t2, T, t3, t4)
    res = elementIsActiveInBetween(trace, 0, 4, _CT1)
    assert res is True


def test_elementIsRcfgTargetInBetween_out_of_bounds_left_end_raises_error(safetyProp1):
    frs = safetyProp1.passingFlowRules
    t1 = PktProcTrans(frs[0], _SW1)
    t2 = PktProcTrans(frs[0], _SW2)
    t3 = PktProcTrans(frs[0], _SW2)
    trace = _makeTrace(t1, t2, t3)
    with pytest.raises(IndexError):
        elementIsRcfgTargetInBetween(trace, -1, 2, _SW1)


def test_elementIsRcfgTargetInBetween_out_of_bounds_right_end_raises_error(safetyProp1):
    frs = safetyProp1.passingFlowRules
    t1 = PktProcTrans(frs[0], _SW1)
    t2 = PktProcTrans(frs[0], _SW2)
    t3 = PktProcTrans(frs[0], _SW2)
    trace = _makeTrace(t1, t2, t3)
    with pytest.raises(IndexError):
        elementIsRcfgTargetInBetween(trace, 0, 3, _SW1)


def test_elementIsRcfgTargetInBetween_switch_processes_packet_returns_False(
    safetyProp1,
):
    frs = safetyProp1.passingFlowRules
    t1 = PktProcTrans(frs[0], _SW1)
    t2 = PktProcTrans(frs[0], _SW2)
    T = PktProcTrans(frs[0], _SW1)
    t3 = PktProcTrans(frs[0], _SW2)
    t4 = RcfgTrans(frs[2], _CT1, _SW1, "ch")
    trace = _makeTrace(t1, t2, T, t3, t4)
    res = elementIsRcfgTargetInBetween(trace, 0, 4, _SW1)
    assert res is False


def test_elementIsRcfgTargetInBetween_switch_sends_rcfg_returns_False(safetyProp1):
    frs = safetyProp1.passingFlowRules
    t1 = PktProcTrans(frs[0], _SW1)
    t2 = PktProcTrans(frs[0], _SW2)
    T = RcfgTrans("", _SW1, _CT1, "ch")
    t3 = PktProcTrans(frs[0], _SW2)
    t4 = RcfgTrans(frs[2], _CT1, _SW1, "ch")
    trace = _makeTrace(t1, t2, T, t3, t4)
    res = elementIsRcfgTargetInBetween(trace, 0, 4, _SW1)
    assert res is False


def test_elementIsRcfgTargetInBetween_switch_receives_rcfg_returns_True(safetyProp1):
    frs = safetyProp1.passingFlowRules
    t1 = PktProcTrans(frs[0], _SW1)
    t2 = PktProcTrans(frs[0], _SW2)
    T = RcfgTrans("", _CT1, _SW1, "ch")
    t3 = PktProcTrans(frs[0], _SW2)
    t4 = RcfgTrans(frs[2], _CT1, _SW1, "ch")
    trace = _makeTrace(t1, t2, T, t3, t4)
    res = elementIsRcfgTargetInBetween(trace, 0, 4, _SW1)
    assert res is True


def test_check_CT_SW_CT_race_different_target_switches_returns_none(
    katch, metadata2SW2CT, safetyProp1
):
    frs = safetyProp1.passingFlowRules
    t1 = RcfgTrans(frs[0], _CT1, _SW1, "ch")
    t2 = RcfgTrans(frs[1], _CT2, _SW2, "ch")
    trace = _makeTrace(t1, t2)

    props = raceSafetyDict(safetyProp1.prop)
    tc = TransitionsChecker(katch, props, metadata2SW2CT.elements)
    result = tc.check(trace, 0, 1)

    assert result is None


def test_check_CT_SW_CT_race_switch_rcfg_source_returns_none(
    katch, metadata2SW2CT, safetyProp1
):
    frs = safetyProp1.passingFlowRules
    t1 = RcfgTrans(frs[0], _SW2, _SW1, "ch")
    t2 = RcfgTrans(frs[1], _CT2, _SW2, "ch")
    trace = _makeTrace(t1, t2)

    props = raceSafetyDict(safetyProp1.prop)
    tc = TransitionsChecker(katch, props, metadata2SW2CT.elements)
    result = tc.check(trace, 0, 1)

    assert result is None


def test_check_CT_SW_CT_race_switch_rcfg_source_returns_none2(
    katch, metadata2SW2CT, safetyProp1
):
    frs = safetyProp1.passingFlowRules
    t1 = RcfgTrans(frs[0], _CT2, _SW1, "ch")
    t2 = RcfgTrans(frs[1], _SW1, _SW2, "ch")
    trace = _makeTrace(t1, t2)

    props = raceSafetyDict(safetyProp1.prop)
    tc = TransitionsChecker(katch, props, metadata2SW2CT.elements)
    result = tc.check(trace, 0, 1)

    assert result is None


def test_check_CT_SW_CT_race_active_first_controller_in_between_returns_none(
    katch, metadata2SW2CT, safetyProp1
):
    frs = safetyProp1.passingFlowRules
    t1 = RcfgTrans(frs[0], _CT2, _SW1, "ch")
    dummyT = RcfgTrans(frs[0], _CT2, _SW2, "ch")
    t2 = RcfgTrans(frs[1], _CT1, _SW1, "ch")
    trace = _makeTrace(t1, dummyT, t2)

    props = raceSafetyDict(safetyProp1.prop)
    tc = TransitionsChecker(katch, props, metadata2SW2CT.elements)
    result = tc.check(trace, 0, 2)

    assert result is None


def test_check_CT_SW_CT_race_active_first_controller_in_between_returns_none2(
    katch, metadata2SW2CT, safetyProp1
):
    frs = safetyProp1.passingFlowRules
    t1 = RcfgTrans(frs[0], _CT2, _SW1, "ch")
    dummyT = RcfgTrans(frs[0], _SW2, _CT2, "ch")
    t2 = RcfgTrans(frs[1], _CT1, _SW1, "ch")
    trace = _makeTrace(t1, dummyT, t2)

    props = raceSafetyDict(safetyProp1.prop)
    tc = TransitionsChecker(katch, props, metadata2SW2CT.elements)
    result = tc.check(trace, 0, 2)

    assert result is None


def test_check_CT_SW_CT_race_switch_is_rcfg_target_in_between_returns_none(
    katch, metadata2SW2CT, safetyProp1
):
    frs = safetyProp1.passingFlowRules
    t1 = RcfgTrans(frs[0], _CT2, _SW1, "ch")
    dummyT = RcfgTrans(frs[0], _CT2, _SW1, "ch")
    t2 = RcfgTrans(frs[1], _CT1, _SW1, "ch")
    trace = _makeTrace(t1, dummyT, t2)

    props = raceSafetyDict(safetyProp1.prop)
    tc = TransitionsChecker(katch, props, metadata2SW2CT.elements)
    result = tc.check(trace, 0, 2)

    assert result is None


def test_check_harmful_CT_SW_CT_race_returns_race(
    katch, trace_1SW_2CT_harmful_CT_SW_CT_race2
):
    td = trace_1SW_2CT_harmful_CT_SW_CT_race2
    props = raceSafetyDict(td.safetyProp)
    tc = TransitionsChecker(katch, props, td.metadata)
    result = tc.check(td.trace, td.racingNodes[0].pos, td.racingNodes[1].pos)

    assert result == TransCheckResult(
        RaceType.CT_SW_CT, td.racingNodes[0].netPolicy, td.racingNodes[1].netPolicy
    )


def test_check_unharmful_CT_SW_CT_race_returns_none(
    katch, trace_1SW_2CT_unharmful_CT_SW_CT_race
):
    td = trace_1SW_2CT_unharmful_CT_SW_CT_race
    props = raceSafetyDict(td.safetyProp)
    tc = TransitionsChecker(katch, props, td.metadata)
    result = tc.check(td.trace, 3, 4)

    assert result is None


def test_check_CT_CT_SW_race_switch_rcfg_source_returns_none(
    katch, metadata2SW2CT, safetyProp1
):
    frs = safetyProp1.passingFlowRules
    t1 = RcfgTrans(frs[0], _SW2, _SW1, "ch")
    t2 = RcfgTrans(frs[1], _CT2, _CT1, "ch")
    trace = _makeTrace(t1, t2)

    props = raceSafetyDict(safetyProp1.prop)
    tc = TransitionsChecker(katch, props, metadata2SW2CT.elements)
    result = tc.check(trace, 0, 1)

    assert result is None


def test_check_CT_CT_SW_race_switch_rcfg_source_returns_none2(
    katch, metadata2SW2CT, safetyProp1
):
    frs = safetyProp1.passingFlowRules
    t1 = RcfgTrans(frs[0], _CT1, _SW1, "ch")
    t2 = RcfgTrans(frs[1], _SW2, _CT1, "ch")
    trace = _makeTrace(t1, t2)

    props = raceSafetyDict(safetyProp1.prop)
    tc = TransitionsChecker(katch, props, metadata2SW2CT.elements)
    result = tc.check(trace, 0, 1)

    assert result is None


def test_check_CT_CT_SW_race_both_rcfg_destinations_are_switches_returns_none(
    katch, metadata2SW2CT, safetyProp1
):
    frs = safetyProp1.passingFlowRules
    t1 = RcfgTrans(frs[0], _CT1, _SW1, "ch")
    t2 = RcfgTrans(frs[1], _CT2, _SW2, "ch")
    trace = _makeTrace(t1, t2)

    props = raceSafetyDict(safetyProp1.prop)
    tc = TransitionsChecker(katch, props, metadata2SW2CT.elements)
    result = tc.check(trace, 0, 1)

    assert result is None


def test_check_CT_CT_SW_race_different_source_and_destination_controller_returns_none(
    katch, metadata2SW3CT, safetyProp1
):
    frs = safetyProp1.passingFlowRules
    t1 = RcfgTrans(frs[0], _CT1, _CT2, "ch")
    t2 = RcfgTrans(frs[1], _CT3, _SW2, "ch")
    trace = _makeTrace(t1, t2)

    props = raceSafetyDict(safetyProp1.prop)
    tc = TransitionsChecker(katch, props, metadata2SW3CT.elements)
    result = tc.check(trace, 0, 1)

    assert result is None


def test_check_CT_CT_SW_race_no_switch_destination_returns_none(
    katch, metadata2SW3CT, safetyProp1
):
    frs = safetyProp1.passingFlowRules
    t1 = RcfgTrans(frs[0], _CT1, _CT2, "ch")
    t2 = RcfgTrans(frs[1], _CT3, _CT1, "ch")
    trace = _makeTrace(t1, t2)

    props = raceSafetyDict(safetyProp1.prop)
    tc = TransitionsChecker(katch, props, metadata2SW3CT.elements)
    result = tc.check(trace, 0, 1)

    assert result is None


def test_check_CT_CT_SW_race_active_first_controller_in_between_returns_none(
    katch, metadata2SW3CT, safetyProp1
):
    frs = safetyProp1.passingFlowRules
    t1 = RcfgTrans(frs[0], _CT1, _SW1, "ch")
    dummyT = RcfgTrans(frs[0], _CT1, _SW2, "ch")
    t2 = RcfgTrans(frs[1], _CT2, _CT1, "ch")
    trace = _makeTrace(t1, dummyT, t2)

    props = raceSafetyDict(safetyProp1.prop)
    tc = TransitionsChecker(katch, props, metadata2SW3CT.elements)
    result = tc.check(trace, 0, 2)

    assert result is None


def test_check_CT_CT_SW_race_active_first_controller_in_between_returns_none2(
    katch, metadata2SW3CT, safetyProp1
):
    frs = safetyProp1.passingFlowRules
    t1 = RcfgTrans(frs[0], _CT1, _SW1, "ch")
    dummyT = RcfgTrans(frs[0], _SW2, _CT1, "ch")
    t2 = RcfgTrans(frs[1], _CT2, _CT1, "ch")
    trace = _makeTrace(t1, dummyT, t2)

    props = raceSafetyDict(safetyProp1.prop)
    tc = TransitionsChecker(katch, props, metadata2SW3CT.elements)
    result = tc.check(trace, 0, 2)

    assert result is None


def test_check_CT_CT_SW_race_switch_is_rcfg_target_in_between_returns_none(
    katch, metadata2SW3CT, safetyProp1
):
    frs = safetyProp1.passingFlowRules
    t1 = RcfgTrans(frs[0], _CT1, _SW1, "ch")
    dummyT = RcfgTrans(frs[0], _CT3, _SW1, "ch")
    t2 = RcfgTrans(frs[1], _CT2, _CT1, "ch")
    trace = _makeTrace(t1, dummyT, t2)

    props = raceSafetyDict(safetyProp1.prop)
    tc = TransitionsChecker(katch, props, metadata2SW3CT.elements)
    result = tc.check(trace, 0, 2)

    assert result is None


def test_check_harmful_CT_CT_SW_race_returns_race(
    katch, trace_2SW_2CT_harmful_CT_CT_SW_race2
):
    td = trace_2SW_2CT_harmful_CT_CT_SW_race2
    props = raceSafetyDict(td.safetyProp)
    tc = TransitionsChecker(katch, props, td.metadata)
    result = tc.check(td.trace, td.racingNodes[0].pos, td.racingNodes[1].pos)

    assert result == TransCheckResult(
        RaceType.CT_CT_SW, td.racingNodes[0].netPolicy, td.racingNodes[1].netPolicy
    )


def test_check_unharmful_CT_CT_SW_race_returns_none(
    katch, trace_2SW_2CT_unharmful_CT_CT_SW_race
):
    td = trace_2SW_2CT_unharmful_CT_CT_SW_race
    props = raceSafetyDict(td.safetyProp)
    tc = TransitionsChecker(katch, props, td.metadata)
    result = tc.check(td.trace, 3, 4)

    assert result is None


def test_check_CT_SW_race_different_target_switch_returns_none(
    katch, metadata2SW2CT, safetyProp1
):
    frs = safetyProp1.passingFlowRules
    t1 = PktProcTrans(frs[0], _SW1)
    t2 = RcfgTrans(frs[2], _CT2, _SW2, "ch")
    trace = _makeTrace(t1, t2)

    props = raceSafetyDict(safetyProp1.prop)
    tc = TransitionsChecker(katch, props, metadata2SW2CT.elements)
    res1 = tc.check(trace, 1, 0)
    res2 = tc.check(trace, 0, 1)

    assert res1 is None
    assert res2 is None


def test_check_CT_SW_race_switch_rcfg_source_returns_none(
    katch, metadata2SW2CT, safetyProp1
):
    frs = safetyProp1.passingFlowRules
    t1 = PktProcTrans(frs[0], _SW1)
    t2 = RcfgTrans(frs[1], _SW1, _SW2, "ch")
    trace = _makeTrace(t1, t2)

    props = raceSafetyDict(safetyProp1.prop)
    tc = TransitionsChecker(katch, props, metadata2SW2CT.elements)
    res1 = tc.check(trace, 1, 0)
    res2 = tc.check(trace, 0, 1)

    assert res1 is None
    assert res2 is None


def test_check_CT_SW_race_active_src_switch_in_between_transitions_returns_none(
    katch, metadata2SW2CT, safetyProp1
):
    frs = safetyProp1.passingFlowRules
    t1 = PktProcTrans(frs[1], _SW1)
    dummyT = PktProcTrans("policy", _SW1)
    t2 = RcfgTrans(frs[2], _CT1, _SW1, "ch")
    trace = _makeTrace(t1, dummyT, t2)

    props = raceSafetyDict(safetyProp1.prop)
    tc = TransitionsChecker(katch, props, metadata2SW2CT.elements)
    res1 = tc.check(trace, 2, 0)
    res2 = tc.check(trace, 0, 2)

    assert res1 is None
    assert res2 is None


def test_check_CT_SW_race_active_src_switch_in_between_transitions_returns_none2(
    katch, metadata2SW2CT, safetyProp1
):
    frs = safetyProp1.passingFlowRules
    t1 = PktProcTrans(frs[0], _SW1)
    dummyT = RcfgTrans("policy", _SW1, _CT2, "ch")
    t2 = RcfgTrans(frs[2], _CT1, _SW1, "ch")
    trace = _makeTrace(t1, dummyT, t2)

    props = raceSafetyDict(safetyProp1.prop)
    tc = TransitionsChecker(katch, props, metadata2SW2CT.elements)
    res1 = tc.check(trace, 2, 0)
    res2 = tc.check(trace, 0, 2)

    assert res1 is None
    assert res2 is None


def test_check_unharmful_CT_SW_race_returns_none(
    katch, trace_1SW_1CT_unharmful_CT_SW_race
):
    td = trace_1SW_1CT_unharmful_CT_SW_race
    props = raceSafetyDict(td.safetyProp)
    tc = TransitionsChecker(katch, props, td.metadata)
    res1 = tc.check(td.trace, 3, 2)
    res2 = tc.check(td.trace, 2, 3)

    assert res1 is None
    assert res2 is None


def test_check_harmful_CT_SW_race_returns_race(
    katch, trace_1SW_1CT_harmful_CT_SW_race2
):
    td = trace_1SW_1CT_harmful_CT_SW_race2
    props = raceSafetyDict(td.safetyProp)
    tc = TransitionsChecker(katch, props, td.metadata)
    res1 = tc.check(td.trace, td.racingNodes[0].pos, td.racingNodes[1].pos)
    res2 = tc.check(td.trace, td.racingNodes[1].pos, td.racingNodes[0].pos)

    assert res1 == TransCheckResult(
        RaceType.CT_SW, td.racingNodes[0].netPolicy, td.racingNodes[1].netPolicy
    )
    assert res2 == TransCheckResult(
        RaceType.CT_SW, td.racingNodes[1].netPolicy, td.racingNodes[0].netPolicy
    )


def test_skipped_races_are_counted(katch, metadata2SW2CT):
    tc = TransitionsChecker(katch, {}, metadata2SW2CT.elements)
    for _i in range(2):
        tc._addSkippedRace(RaceType.SW_SW)
        tc._addSkippedRace(RaceType.CT_CT_SW)
        tc._addSkippedRace(RaceType.CT_SW_CT)
        tc._addSkippedRace(RaceType.CT_SW)
    res = tc.getSkippedRacesStr("\t")
    assert res == (
        f"\t{RaceType.SW_SW}: 2 times\n"
        f"\t{RaceType.CT_CT_SW}: 2 times\n"
        f"\t{RaceType.CT_SW_CT}: 2 times\n"
        f"\t{RaceType.CT_SW}: 2 times"
    )


def test_check_transition_pair_without_check_returns_none(
    katch, metadata2SW2CT, safetyProp1
):
    t1 = PktProcTrans("", _SW1)
    t2 = TraceTransition()
    trace = _makeTrace(t1, t2)

    props = raceSafetyDict(safetyProp1.prop)
    tc = TransitionsChecker(katch, props, metadata2SW2CT.elements)
    res = tc.check(trace, 0, 1)
    assert res is None
    assert tc.getSkippedRacesStr() == ""


def test_check_harmful_races_without_safety_properties_returns_none(
    katch, trace_1SW_2CT_harmful_CT_SW_and_CT_SW_CT_race
):
    td = trace_1SW_2CT_harmful_CT_SW_and_CT_SW_CT_race
    # no safety properties
    tc = TransitionsChecker(katch, {}, td.metadata)
    res1 = tc.check(td.trace, 1, 2)
    res2 = tc.check(td.trace, 3, 4)
    assert res1 is None
    assert res2 is None
    assert tc.getSkippedRacesStr() == ""


def test_check_SWSW_race_is_skipped_returns_none(katch, trace_2SW_2CT_SW_SW_race):
    td = trace_2SW_2CT_SW_SW_race
    props = raceSafetyDict(td.safetyProp)
    tc = TransitionsChecker(katch, props, td.metadata)
    res = tc.check(td.trace, 3, 4)
    assert res is None
    assert tc.getSkippedRacesStr() == f"{RaceType.SW_SW}: 1 times"


def test_check_all_races_skipped_returns_none(katch, metadata2SW2CT, safetyProp1):
    frs = safetyProp1.passingFlowRules
    props = raceSafetyDict(safetyProp1.prop)
    tc = TransitionsChecker(
        katch, props, metadata2SW2CT.elements, [rt for rt in RaceType]
    )

    t1 = PktProcTrans(frs[0], _SW1)
    t2 = RcfgTrans(frs[1], _CT1, _SW1, "ch")
    t3 = RcfgTrans(frs[2], _CT2, _SW1, "ch")
    t4 = RcfgTrans(frs[2], _CT2, _CT1, "ch")
    #                SW SW  | CT SW CT |  CT SW  | CT CT SW
    for tt1, tt2 in [(t1, t1), (t2, t3), (t2, t1), (t2, t4)]:
        trace = _makeTrace(tt1, tt2)
        res = tc.check(trace, 0, 1)
        assert res is None
    assert tc.getSkippedRacesStr() == (
        f"{RaceType.SW_SW}: 1 times\n"
        f"{RaceType.CT_SW_CT}: 1 times\n"
        f"{RaceType.CT_SW}: 1 times\n"
        f"{RaceType.CT_CT_SW}: 1 times"
    )
