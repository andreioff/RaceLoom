from src.analyzer.trace_analyzer import RaceType
from src.trace.transition import PktProcTrans, RcfgTrans
from src.util import DyNetKATSymbols as sym

pytest_plugins = [
    "test.src.test_utils.fixtures",
    "test.src.analyzer.trace_analyzer.test_utils.fixtures",
]

# position of elements in metadata list
_SW1 = 0
_SW2 = 1
_CT1 = 2
_CT2 = 3


def test_checkRcfgRcfg_different_target_switches_returns_none(
    transChecker2SW2CT, flowRule1, flowRule2
):
    t1 = RcfgTrans(flowRule1, _CT1, _SW1, "ch")
    t2 = RcfgTrans(flowRule2, _CT2, _SW2, "ch")
    result = transChecker2SW2CT._checkRcfgRcfg(t1, t2)
    assert result is None


def test_checkRcfgRcfg_switch_rcfg_source_returns_none(
    transChecker2SW2CT, flowRule1, flowRule2
):
    t1 = RcfgTrans(flowRule1, _SW2, _SW1, "ch")
    t2 = RcfgTrans(flowRule2, _CT2, _SW2, "ch")
    result = transChecker2SW2CT._checkRcfgRcfg(t1, t2)
    assert result is None


def test_checkRcfgRcfg_switch_rcfg_source_returns_none2(
    transChecker2SW2CT, flowRule1, flowRule2
):
    t1 = RcfgTrans(flowRule1, _CT2, _SW1, "ch")
    t2 = RcfgTrans(flowRule2, _SW1, _SW2, "ch")
    result = transChecker2SW2CT._checkRcfgRcfg(t1, t2)
    assert result is None


def test_checkRcfgRcfg_valid_rcfgs_not_equivalent_policies_returns_race(
    transChecker2SW2CT, flowRule1, flowRule2
):
    t1 = RcfgTrans(flowRule1, _CT1, _SW1, "ch")
    t2 = RcfgTrans(flowRule2, _CT2, _SW1, "ch")
    result = transChecker2SW2CT._checkRcfgRcfg(t1, t2)
    assert result is RaceType.CT_SW_CT


def test_checkRcfgRcfg_valid_rcfgs_equivalent_policies_returns_none(
    transChecker2SW2CT, flowRule1, flowRule3
):
    t1 = RcfgTrans(flowRule1 + sym.OR + flowRule3, _CT1, _SW2, "ch")
    t2 = RcfgTrans(flowRule3 + sym.OR + flowRule1, _CT2, _SW2, "ch")
    result = transChecker2SW2CT._checkRcfgRcfg(t1, t2)
    assert result is None


def test_checkProcRcfg_different_target_switch_returns_none(
    transChecker2SW2CT, flowRule1, flowRule3
):
    t1 = PktProcTrans(flowRule1 + sym.OR + flowRule3, _SW1)
    t2 = RcfgTrans(flowRule3 + sym.OR + flowRule1, _CT2, _SW2, "ch")
    res1 = transChecker2SW2CT._checkProcRcfg(t1, t2)
    res2 = transChecker2SW2CT._checkRcfgProc(t2, t1)
    assert res1 is None
    assert res2 is None


def test_checkProcRcfg_switch_rcfg_source_returns_none(
    transChecker2SW2CT, flowRule1, flowRule3
):
    t1 = PktProcTrans(flowRule1 + sym.OR + flowRule3, _SW1)
    t2 = RcfgTrans(flowRule3 + sym.OR + flowRule1, _SW1, _SW2, "ch")
    res1 = transChecker2SW2CT._checkProcRcfg(t1, t2)
    res2 = transChecker2SW2CT._checkRcfgProc(t2, t1)
    assert res1 is None
    assert res2 is None


def test_checkProcRcfg_valid_transitions_empty_policy_difference_returns_none(
    transChecker2SW2CT, flowRule1, flowRule2, flowRule3
):
    t1 = PktProcTrans(flowRule1 + sym.OR + flowRule3, _SW1)
    t2 = RcfgTrans(
        flowRule2 + sym.OR + flowRule3 + sym.OR + flowRule1, _CT1, _SW1, "ch"
    )
    res1 = transChecker2SW2CT._checkProcRcfg(t1, t2)
    res2 = transChecker2SW2CT._checkRcfgProc(t2, t1)
    assert res1 is None
    assert res2 is None


def test_checkProcRcfg_valid_transitions_non_empty_policy_difference_returns_race(
    transChecker2SW2CT, flowRule1, flowRule2, flowRule3
):
    t1 = PktProcTrans(flowRule2 + sym.OR + flowRule3, _SW1)
    t2 = RcfgTrans(flowRule3 + sym.OR + flowRule1, _CT1, _SW1, "ch")
    res1 = transChecker2SW2CT._checkProcRcfg(t1, t2)
    res2 = transChecker2SW2CT._checkRcfgProc(t2, t1)
    assert res1 is RaceType.CT_SW
    assert res2 is RaceType.CT_SW


def test_unexpected_transition_pairs_are_counted(
    transChecker2SW2CT, flowRule1, flowRule2
):
    t1 = PktProcTrans(flowRule1, _SW1)
    t2 = RcfgTrans(flowRule2, _CT1, _SW1, "ch")
    for _i in range(2):
        transChecker2SW2CT._addUnexpectedTransPair(t1, t1)
        transChecker2SW2CT._addUnexpectedTransPair(t1, t2)
        transChecker2SW2CT._addUnexpectedTransPair(t2, t1)
        transChecker2SW2CT._addUnexpectedTransPair(t2, t2)
    res = transChecker2SW2CT.getUnexpectedTransPairsStr("\t")
    assert res == (
        "\t(PktProcTrans, PktProcTrans): 2 occurrences\n"
        "\t(PktProcTrans, RcfgTrans): 2 occurrences\n"
        "\t(RcfgTrans, PktProcTrans): 2 occurrences\n"
        "\t(RcfgTrans, RcfgTrans): 2 occurrences"
    )


def test_check_processing_and_rcfg_transitions_returns_race(
    transChecker2SW2CT, flowRule1, flowRule2
):
    t1 = PktProcTrans(flowRule1, _SW1)
    t2 = RcfgTrans(flowRule2, _CT1, _SW1, "ch")
    res1 = transChecker2SW2CT.check(t1, t2)
    res2 = transChecker2SW2CT.check(t2, t1)
    assert res1 is RaceType.CT_SW
    assert res2 is RaceType.CT_SW
    assert transChecker2SW2CT.getUnexpectedTransPairsStr() == ""


def test_check_processing_and_rcfg_transitions_returns_none(
    transChecker2SW2CT, flowRule1
):
    t1 = PktProcTrans(flowRule1, _SW1)
    t2 = RcfgTrans(flowRule1, _CT1, _SW1, "ch")
    res1 = transChecker2SW2CT.check(t1, t2)
    res2 = transChecker2SW2CT.check(t2, t1)
    assert res1 is None
    assert res2 is None
    assert transChecker2SW2CT.getUnexpectedTransPairsStr() == ""


def test_check_rcfg_transitions_returns_race(transChecker2SW2CT, flowRule1, flowRule2):
    t1 = RcfgTrans(flowRule1, _CT1, _SW1, "ch")
    t2 = RcfgTrans(flowRule2, _CT2, _SW1, "ch")
    res = transChecker2SW2CT.check(t1, t2)
    assert res is RaceType.CT_SW_CT
    assert transChecker2SW2CT.getUnexpectedTransPairsStr() == ""


def test_check_rcfg_transitions_returns_none(transChecker2SW2CT, flowRule1):
    t1 = RcfgTrans(flowRule1, _CT1, _SW1, "ch")
    t2 = RcfgTrans(flowRule1, _CT2, _SW1, "ch")
    res = transChecker2SW2CT.check(t1, t2)
    assert res is None
    assert transChecker2SW2CT.getUnexpectedTransPairsStr() == ""


def test_check_unexpected_transitions_returns_none(transChecker2SW2CT, flowRule1):
    t1 = PktProcTrans(flowRule1, _SW1)
    res = transChecker2SW2CT.check(t1, t1)
    assert res is None
    assert (
        transChecker2SW2CT.getUnexpectedTransPairsStr()
        == "(PktProcTrans, PktProcTrans): 1 occurrences"
    )
