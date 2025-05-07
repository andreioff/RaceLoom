import pytest

from src.analyzer.trace_analyzer import TransitionsChecker, RaceType
from src.model.dnk_maude_model import ElementMetadata, ElementType
from src.trace.transition import RcfgTrans, PktProcTrans
from src.util import DyNetKATSymbols as sym
from test.src.testfiles.fixtures import katch, flowRule1, flowRule2, flowRule3

_SW1 = 0
_SW2 = 1
_CT1 = 2
_CT2 = 3


@pytest.fixture
def transChecker(katch) -> TransitionsChecker:
    elsMetadata = [
        ElementMetadata(_SW1, ElementType.SW),
        ElementMetadata(_SW2, ElementType.SW),
        ElementMetadata(_CT1, ElementType.CT),
        ElementMetadata(_CT2, ElementType.CT),
    ]
    return TransitionsChecker(katch, elsMetadata)


def test_checkRcfgRcfg_different_target_switches_returns_none(
    transChecker, flowRule1, flowRule2
):
    t1 = RcfgTrans(flowRule1, _CT1, _SW1, "ch")
    t2 = RcfgTrans(flowRule2, _CT2, _SW2, "ch")
    result = transChecker._checkRcfgRcfg(t1, t2)
    assert result is None


def test_checkRcfgRcfg_switch_rcfg_source_returns_none(
    transChecker, flowRule1, flowRule2
):
    t1 = RcfgTrans(flowRule1, _SW2, _SW1, "ch")
    t2 = RcfgTrans(flowRule2, _CT2, _SW2, "ch")
    result = transChecker._checkRcfgRcfg(t1, t2)
    assert result is None


def test_checkRcfgRcfg_switch_rcfg_source_returns_none2(
    transChecker, flowRule1, flowRule2
):
    t1 = RcfgTrans(flowRule1, _CT2, _SW1, "ch")
    t2 = RcfgTrans(flowRule2, _SW1, _SW2, "ch")
    result = transChecker._checkRcfgRcfg(t1, t2)
    assert result is None


def test_checkRcfgRcfg_valid_rcfgs_not_equivalent_policies_returns_race(
    transChecker, flowRule1, flowRule2
):
    t1 = RcfgTrans(flowRule1, _CT1, _SW1, "ch")
    t2 = RcfgTrans(flowRule2, _CT2, _SW1, "ch")
    result = transChecker._checkRcfgRcfg(t1, t2)
    assert result is RaceType.CTCT


def test_checkRcfgRcfg_valid_rcfgs_equivalent_policies_returns_none(
    transChecker, flowRule1, flowRule3
):
    t1 = RcfgTrans(flowRule1 + sym.OR + flowRule3, _CT1, _SW2, "ch")
    t2 = RcfgTrans(flowRule3 + sym.OR + flowRule1, _CT2, _SW2, "ch")
    result = transChecker._checkRcfgRcfg(t1, t2)
    assert result is None


def test_checkProcRcfg_different_target_switch_returns_none(
    transChecker, flowRule1, flowRule3
):
    t1 = PktProcTrans(flowRule1 + sym.OR + flowRule3, _SW1)
    t2 = RcfgTrans(flowRule3 + sym.OR + flowRule1, _CT2, _SW2, "ch")
    res1 = transChecker._checkProcRcfg(t1, t2)
    res2 = transChecker._checkRcfgProc(t2, t1)
    assert res1 is None
    assert res2 is None


def test_checkProcRcfg_switch_rcfg_source_returns_none(
    transChecker, flowRule1, flowRule3
):
    t1 = PktProcTrans(flowRule1 + sym.OR + flowRule3, _SW1)
    t2 = RcfgTrans(flowRule3 + sym.OR + flowRule1, _SW1, _SW2, "ch")
    res1 = transChecker._checkProcRcfg(t1, t2)
    res2 = transChecker._checkRcfgProc(t2, t1)
    assert res1 is None
    assert res2 is None


def test_checkProcRcfg_valid_transitions_empty_policy_difference_returns_none(
    transChecker, flowRule1, flowRule2, flowRule3
):
    t1 = PktProcTrans(flowRule1 + sym.OR + flowRule3, _SW1)
    t2 = RcfgTrans(
        flowRule2 + sym.OR + flowRule3 + sym.OR + flowRule1, _CT1, _SW1, "ch"
    )
    res1 = transChecker._checkProcRcfg(t1, t2)
    res2 = transChecker._checkRcfgProc(t2, t1)
    assert res1 is None
    assert res2 is None


def test_checkProcRcfg_valid_transitions_non_empty_policy_difference_returns_race(
    transChecker, flowRule1, flowRule2, flowRule3
):
    t1 = PktProcTrans(flowRule2 + sym.OR + flowRule3, _SW1)
    t2 = RcfgTrans(flowRule3 + sym.OR + flowRule1, _CT1, _SW1, "ch")
    res1 = transChecker._checkProcRcfg(t1, t2)
    res2 = transChecker._checkRcfgProc(t2, t1)
    assert res1 is RaceType.SWCT
    assert res2 is RaceType.SWCT


def test_unexpected_transition_pairs_are_counted(transChecker, flowRule1, flowRule2):
    t1 = PktProcTrans(flowRule1, _SW1)
    t2 = RcfgTrans(flowRule2, _CT1, _SW1, "ch")
    for i in range(2):
        transChecker._addUnexpectedTransPair(t1, t1)
        transChecker._addUnexpectedTransPair(t1, t2)
        transChecker._addUnexpectedTransPair(t2, t1)
        transChecker._addUnexpectedTransPair(t2, t2)
    res = transChecker.getUnexpectedTransPairsStr("\t")
    assert res == (
        "\t(PktProcTrans, PktProcTrans): 2 occurrences\n"
        "\t(PktProcTrans, RcfgTrans): 2 occurrences\n"
        "\t(RcfgTrans, PktProcTrans): 2 occurrences\n"
        "\t(RcfgTrans, RcfgTrans): 2 occurrences"
    )


def test_check_processing_and_rcfg_transitions_returns_race(
    transChecker, flowRule1, flowRule2
):
    t1 = PktProcTrans(flowRule1, _SW1)
    t2 = RcfgTrans(flowRule2, _CT1, _SW1, "ch")
    res1 = transChecker.check(t1, t2)
    res2 = transChecker.check(t2, t1)
    assert res1 is RaceType.SWCT
    assert res2 is RaceType.SWCT
    assert transChecker.getUnexpectedTransPairsStr() == ""


def test_check_processing_and_rcfg_transitions_returns_none(transChecker, flowRule1):
    t1 = PktProcTrans(flowRule1, _SW1)
    t2 = RcfgTrans(flowRule1, _CT1, _SW1, "ch")
    res1 = transChecker.check(t1, t2)
    res2 = transChecker.check(t2, t1)
    assert res1 is None
    assert res2 is None
    assert transChecker.getUnexpectedTransPairsStr() == ""


def test_check_rcfg_transitions_returns_race(transChecker, flowRule1, flowRule2):
    t1 = RcfgTrans(flowRule1, _CT1, _SW1, "ch")
    t2 = RcfgTrans(flowRule2, _CT2, _SW1, "ch")
    res = transChecker.check(t1, t2)
    assert res is RaceType.CTCT
    assert transChecker.getUnexpectedTransPairsStr() == ""


def test_check_rcfg_transitions_returns_none(transChecker, flowRule1):
    t1 = RcfgTrans(flowRule1, _CT1, _SW1, "ch")
    t2 = RcfgTrans(flowRule1, _CT2, _SW1, "ch")
    res = transChecker.check(t1, t2)
    assert res is None
    assert transChecker.getUnexpectedTransPairsStr() == ""


def test_check_unexpected_transitions_returns_none(transChecker, flowRule1):
    t1 = PktProcTrans(flowRule1, _SW1)
    res = transChecker.check(t1, t1)
    assert res is None
    assert (
        transChecker.getUnexpectedTransPairsStr()
        == "(PktProcTrans, PktProcTrans): 1 occurrences"
    )
