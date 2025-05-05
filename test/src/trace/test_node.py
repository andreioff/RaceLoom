import pytest

from src.errors import ParseError
from src.trace.node import TraceNode
from src.trace.transition import TraceTransition, PktProcTrans, RcfgTrans


def test_new_trace_nodes_must_have_different_ids():
    t1 = TraceNode(TraceTransition(), [])
    t2 = TraceNode(TraceTransition(), [])
    assert t1.id != t2.id, f"Expected different ids, got {t1.id} and {t2.id}"


def test_addRacingNode_valid_nodes_are_marked_correctly():
    t1 = TraceNode(TraceTransition(), [])
    otherTs = [
        TraceNode(TraceTransition(), []),
        TraceNode(TraceTransition(), []),
        TraceNode(TraceTransition(), []),
    ]
    for otherT in otherTs:
        t1.addRacingNode(otherT)

    assert t1.isPartOfRace(), f"Expected {t1.id} to be part of a race"
    for otherT in otherTs:
        assert otherT.isPartOfRace(), f"Expected {otherT.id} to be part of a race"
        assert t1.isRacingWith(
            otherT
        ), f"Expected {t1.id} to be racing with {otherT.id}"
        assert otherT.isRacingWith(
            t1
        ), f"Expected {otherT.id} to be racing with {t1.id}"


def test_addRacingNode_marking_self_raises_value_error():
    t1 = TraceNode(TraceTransition(), [])
    with pytest.raises(ValueError):
        t1.addRacingNode(t1)


def test_fromTuple_valid_tuple_creates_trace_node():
    ts = [
        TraceNode.fromTuple(("", [])),
        TraceNode.fromTuple(("proc('',0)", [[1], [2]])),
        TraceNode.fromTuple(("rcfg(CH, 'test', 3, 1)", [[1, 2], [3, 4]])),
    ]
    for t in ts:
        assert isinstance(t, TraceNode), "Expected all elements to be TraceNode objects"


def test_fromTuple_invalid_tuple_raises_parse_error():
    cases = [
        ("proc('',0)", "invalid_vector_clock"),
        ("", [[1, 2, 3], [1, "str", 2]]),
    ]
    for case in cases:
        with pytest.raises(ParseError):
            TraceNode.fromTuple(case)


def test_toStr_node_is_formatted_as_expected():
    cases = [
        TraceNode(TraceTransition(), [[1, 2], [3, 4]]),
        TraceNode(PktProcTrans("policy", 10), []),
        TraceNode(RcfgTrans("policy2", 1, 4, "CH"), [[1]]),
    ]
    expected = [
        '("", [[1, 2], [3, 4]])',
        "(\"proc('policy', 10)\", [])",
        "(\"rcfg(CH, 'policy2', 1, 4)\", [[1]])",
    ]
    for t, e in zip(cases, expected):
        assert str(t) == e, f"Expected formatted string, got {str(t)}. Expected: {e}"
