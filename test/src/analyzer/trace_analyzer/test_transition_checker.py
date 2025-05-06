import pytest

from src.analyzer.trace_analyzer import TransitionsChecker, RaceType
from src.model.dnk_maude_model import ElementMetadata, ElementType
from src.trace.transition import RcfgTrans
from src.util import DyNetKATSymbols as sym
from test.src.testfiles.fixtures import katch, flowRule1, flowRule2

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


def test_checkRcfgRcfg_valid_rcfgs_equivalent_policies_returns_race(
    transChecker, flowRule1, flowRule3
):
    t1 = RcfgTrans(flowRule1 + sym.OR + flowRule3, _CT1, _SW2, "ch")
    t2 = RcfgTrans(flowRule3 + sym.OR + flowRule1, _CT2, _SW2, "ch")
    result = transChecker._checkRcfgRcfg(t1, t2)
    assert result is RaceType.CTCT
