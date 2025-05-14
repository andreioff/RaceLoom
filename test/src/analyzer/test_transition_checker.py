from src.analyzer.trace_analyzer import RaceType
from src.trace.transition import PktProcTrans, RcfgTrans
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


def test_checkCTSWCT_different_target_switches_returns_none(
    transChecker2SW2CT, flowRule1, flowRule2
):
    t1 = RcfgTrans(flowRule1, _CT1, _SW1, "ch")
    t2 = RcfgTrans(flowRule2, _CT2, _SW2, "ch")
    result = transChecker2SW2CT._checkCTSWCT(t1, t2)
    assert result == (None, False)


def test_checkCTSWCT_switch_rcfg_source_returns_none(
    transChecker2SW2CT, flowRule1, flowRule2
):
    t1 = RcfgTrans(flowRule1, _SW2, _SW1, "ch")
    t2 = RcfgTrans(flowRule2, _CT2, _SW2, "ch")
    result = transChecker2SW2CT._checkCTSWCT(t1, t2)
    assert result == (None, False)


def test_checkCTSWCT_switch_rcfg_source_returns_none2(
    transChecker2SW2CT, flowRule1, flowRule2
):
    t1 = RcfgTrans(flowRule1, _CT2, _SW1, "ch")
    t2 = RcfgTrans(flowRule2, _SW1, _SW2, "ch")
    result = transChecker2SW2CT._checkCTSWCT(t1, t2)
    assert result == (None, False)


def test_checkCTSWCT_valid_rcfgs_not_equivalent_policies_returns_race(
    transChecker2SW2CT, flowRule1, flowRule2
):
    t1 = RcfgTrans(flowRule1, _CT1, _SW1, "ch")
    t2 = RcfgTrans(flowRule2, _CT2, _SW1, "ch")
    result = transChecker2SW2CT._checkCTSWCT(t1, t2)
    assert result == (RaceType.CT_SW_CT, True)


def test_checkCTSWCT_valid_rcfgs_equivalent_policies_returns_none(
    transChecker2SW2CT, flowRule1, flowRule3
):
    t1 = RcfgTrans(flowRule1 + sym.OR + flowRule3, _CT1, _SW2, "ch")
    t2 = RcfgTrans(flowRule3 + sym.OR + flowRule1, _CT2, _SW2, "ch")
    result = transChecker2SW2CT._checkCTSWCT(t1, t2)
    assert result == (None, True)


def test_checkCTCTSW_switch_rcfg_source_returns_none(
    transChecker2SW2CT, flowRule1, flowRule2
):
    t1 = RcfgTrans(flowRule1, _SW2, _SW1, "ch")
    t2 = RcfgTrans(flowRule2, _CT2, _CT1, "ch")
    result = transChecker2SW2CT._checkCTCTSW(t1, t2)
    assert result == (None, False)


def test_checkCTCTSW_switch_rcfg_source_returns_none2(
    transChecker2SW2CT, flowRule1, flowRule2
):
    t1 = RcfgTrans(flowRule1, _CT1, _SW1, "ch")
    t2 = RcfgTrans(flowRule2, _SW2, _CT1, "ch")
    result = transChecker2SW2CT._checkCTCTSW(t1, t2)
    assert result == (None, False)


def test_checkCTCTSW_both_rcfg_destinations_are_switches_returns_none(
    transChecker2SW2CT, flowRule1, flowRule2
):
    t1 = RcfgTrans(flowRule1, _CT1, _SW1, "ch")
    t2 = RcfgTrans(flowRule2, _CT2, _SW2, "ch")
    result = transChecker2SW2CT._checkCTCTSW(t1, t2)
    assert result == (None, False)


def test_checkCTCTSW_different_source_and_destination_controller_returns_none(
    transChecker2SW3CT, flowRule1, flowRule2
):
    t1 = RcfgTrans(flowRule1, _CT1, _CT2, "ch")
    t2 = RcfgTrans(flowRule2, _CT3, _SW2, "ch")
    result = transChecker2SW3CT._checkCTCTSW(t1, t2)
    assert result == (None, False)


def test_checkCTCTSW_no_switch_destination_returns_none(
    transChecker2SW3CT, flowRule1, flowRule2
):
    t1 = RcfgTrans(flowRule1, _CT1, _CT2, "ch")
    t2 = RcfgTrans(flowRule2, _CT3, _CT1, "ch")
    result = transChecker2SW3CT._checkCTCTSW(t1, t2)
    assert result == (None, False)


def test_checkCTCTSW_valid_rcfgs_non_empty_policy_difference_returns_race(
    transChecker2SW2CT, flowRule1, flowRule2
):
    t1 = RcfgTrans(flowRule1, _CT1, _SW1, "ch")
    t2 = RcfgTrans(flowRule2, _CT2, _CT1, "ch")
    result = transChecker2SW2CT._checkCTCTSW(t1, t2)
    assert result == (RaceType.CT_CT_SW, True)


def test_checkCTCTSW_valid_rcfgs_empty_policy_difference_returns_none(
    transChecker2SW2CT, flowRule1, flowRule3
):
    t1 = RcfgTrans(flowRule1, _CT1, _SW2, "ch")
    t2 = RcfgTrans(flowRule3 + sym.OR + flowRule1, _CT2, _CT1, "ch")
    result = transChecker2SW2CT._checkCTCTSW(t1, t2)
    assert result == (None, True)


def test_checkCTSW_different_target_switch_returns_none(
    transChecker2SW2CT, flowRule1, flowRule3
):
    t1 = PktProcTrans(flowRule1 + sym.OR + flowRule3, _SW1)
    t2 = RcfgTrans(flowRule3 + sym.OR + flowRule1, _CT2, _SW2, "ch")
    res2 = transChecker2SW2CT._checkCTSW(t2, t1)
    res1 = transChecker2SW2CT._checkSWCT(t1, t2)
    assert res1 == (None, False)
    assert res2 == (None, False)


def test_checkCTSW_switch_rcfg_source_returns_none(
    transChecker2SW2CT, flowRule1, flowRule3
):
    t1 = PktProcTrans(flowRule1 + sym.OR + flowRule3, _SW1)
    t2 = RcfgTrans(flowRule3 + sym.OR + flowRule1, _SW1, _SW2, "ch")
    res2 = transChecker2SW2CT._checkCTSW(t2, t1)
    res1 = transChecker2SW2CT._checkSWCT(t1, t2)
    assert res1 == (None, False)
    assert res2 == (None, False)


def test_checkCTSW_valid_transitions_empty_policy_difference_returns_none(
    transChecker2SW2CT, flowRule1, flowRule2, flowRule3
):
    t1 = PktProcTrans(flowRule1 + sym.OR + flowRule3, _SW1)
    t2 = RcfgTrans(
        flowRule2 + sym.OR + flowRule3 + sym.OR + flowRule1, _CT1, _SW1, "ch"
    )
    res2 = transChecker2SW2CT._checkCTSW(t2, t1)
    res1 = transChecker2SW2CT._checkSWCT(t1, t2)
    assert res1 == (None, True)
    assert res2 == (None, True)


def test_checkCTSW_valid_transitions_non_empty_policy_difference_returns_race(
    transChecker2SW2CT, flowRule1, flowRule2, flowRule3
):
    t1 = PktProcTrans(flowRule2 + sym.OR + flowRule3, _SW1)
    t2 = RcfgTrans(flowRule3 + sym.OR + flowRule1, _CT1, _SW1, "ch")
    res2 = transChecker2SW2CT._checkCTSW(t2, t1)
    res1 = transChecker2SW2CT._checkSWCT(t1, t2)
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


def test_check_processing_and_rcfg_transitions_returns_CT_SW_race(
    transChecker2SW2CT, flowRule1, flowRule2
):
    t1 = PktProcTrans(flowRule1, _SW1)
    t2 = RcfgTrans(flowRule2, _CT1, _SW1, "ch")
    res1 = transChecker2SW2CT.check(t1, t2)
    res2 = transChecker2SW2CT.check(t2, t1)
    assert res1 is RaceType.CT_SW
    assert res2 is RaceType.CT_SW
    assert transChecker2SW2CT.getSkippedRacesStr() == ""


def test_check_processing_and_rcfg_transitions_returns_none(
    transChecker2SW2CT, flowRule1
):
    t1 = PktProcTrans(flowRule1, _SW1)
    t2 = RcfgTrans(flowRule1, _CT1, _SW1, "ch")
    res1 = transChecker2SW2CT.check(t1, t2)
    res2 = transChecker2SW2CT.check(t2, t1)
    assert res1 is None
    assert res2 is None
    assert transChecker2SW2CT.getSkippedRacesStr() == ""


def test_check_CT_SW_CT_rcfg_transitions_returns_race(
    transChecker2SW2CT, flowRule1, flowRule2
):
    t1 = RcfgTrans(flowRule1, _CT1, _SW1, "ch")
    t2 = RcfgTrans(flowRule2, _CT2, _SW1, "ch")
    res = transChecker2SW2CT.check(t1, t2)
    assert res is RaceType.CT_SW_CT
    assert transChecker2SW2CT.getSkippedRacesStr() == ""


def test_check_CT_SW_CT_rcfg_transitions_returns_none(transChecker2SW2CT, flowRule1):
    t1 = RcfgTrans(flowRule1, _CT1, _SW1, "ch")
    t2 = RcfgTrans(flowRule1, _CT2, _SW1, "ch")
    res = transChecker2SW2CT.check(t1, t2)
    assert res is None
    assert transChecker2SW2CT.getSkippedRacesStr() == ""


def test_check_CT_CT_SW_rcfg_transitions_returns_race(
    transChecker2SW2CT, flowRule1, flowRule2
):
    t1 = RcfgTrans(flowRule1, _CT1, _SW1, "ch")
    t2 = RcfgTrans(flowRule2, _CT2, _CT1, "ch")
    res = transChecker2SW2CT.check(t1, t2)
    assert res is RaceType.CT_CT_SW
    assert transChecker2SW2CT.getSkippedRacesStr() == ""


def test_check_CT_CT_SW_rcfg_transitions_returns_none(transChecker2SW2CT, flowRule1):
    t1 = RcfgTrans(flowRule1, _CT1, _SW1, "ch")
    t2 = RcfgTrans(flowRule1, _CT2, _CT1, "ch")
    res = transChecker2SW2CT.check(t2, t1)
    assert res is None
    assert transChecker2SW2CT.getSkippedRacesStr() == ""


def test_check_SWSW_race_is_skipped_returns_none(transChecker2SW2CT, flowRule1):
    t1 = PktProcTrans(flowRule1, _SW1)
    res = transChecker2SW2CT.check(t1, t1)
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
    for tt1, tt2 in [(t1, t1), (t2, t3), (t2, t1), (t4, t2)]:
        res = transCheckerAllSkipped.check(tt1, tt2)
        assert res is None
    assert transCheckerAllSkipped.getSkippedRacesStr() == (
        f"{RaceType.SW_SW}: 1 times\n"
        f"{RaceType.CT_SW_CT}: 1 times\n"
        f"{RaceType.CT_SW}: 1 times\n"
        f"{RaceType.CT_CT_SW}: 1 times"
    )
