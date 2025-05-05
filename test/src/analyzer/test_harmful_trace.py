from typing import List

import pytest

from src.analyzer.harmful_trace import ColorScheme as cs
from src.analyzer.harmful_trace import HarmfulTrace, RaceType
from src.model.dnk_maude_model import ElementMetadata
from src.model.dnk_maude_model import ElementType as et
from src.trace.node import TraceNode
from src.trace.transition import PktProcTrans, RcfgTrans, TraceTransition


def _wrap_in_digraph(*args: str) -> str:
    """
    Helper function to wrap the given arguments in a DOT graph format.
    """
    return "digraph g {\n" + "".join(args) + "}"


def _dotNode(id: int, label: str) -> str:
    return f'n{id} [label=<{label}>, shape=rectangle, style=filled, fillcolor="{cs.NODE_BG}"];\n'


def _dotNodeLabel(
    vcs: List[List[int]], args: List[str], racingEl: int | None = None
) -> str:
    vcsStr: List[str] = []
    for i, vcsEl in enumerate(vcs):
        if i == racingEl:
            vcsStr.append(f'<font color="{cs.ERR_PRIMARY}">{vcsEl}</font>')
            continue
        vcsStr.append(str(vcsEl))
    return ", ".join(args) + "<br/>" + f"[{", ".join(vcsStr)}]"


def _dotEdge(fromId: int, toId: int, label: str, isRacing: bool) -> str:
    penwidth = 2.0 if isRacing else 1.0
    color = cs.ERR_PRIMARY if isRacing else cs.EDGE
    return (
        f'n{fromId} -> n{toId} [label="{label}", '
        + f'color="{color}", penwidth={penwidth}];\n'
    )


def test_constructor_out_of_bound_racing_transition_data_raises_value_error():
    nodes = [
        TraceNode(TraceTransition(), [[0, 0], [0, 0]]),
        TraceNode(TraceTransition(), [[1, 1], [1, 1]]),
    ]
    metadata = [
        ElementMetadata(0, et.CT),
        ElementMetadata(1, et.SW, "smth"),
    ]
    racingTransToEls = {1: 1, 2: 0}  # second key is OUT OF BOUNDS

    with pytest.raises(ValueError):
        HarmfulTrace(nodes, metadata, racingTransToEls, RaceType.SWSW)


def test_constructor_out_of_bound_racing_transition_data_raises_value_error2():
    nodes = [
        TraceNode(TraceTransition(), [[0, 0], [0, 0]]),
        TraceNode(TraceTransition(), [[1, 1], [1, 1]]),
    ]
    metadata = [
        ElementMetadata(0, et.CT),
        ElementMetadata(1, et.SW, "smth"),
    ]
    racingTransToEls = {1: 1, 0: 3}  # second value is OUT OF BOUNDS

    with pytest.raises(ValueError):
        HarmfulTrace(nodes, metadata, racingTransToEls, RaceType.SWSW)


def test_toDOT_no_nodes_returns_empty_DOT_graph():
    harmful_trace = HarmfulTrace([], [], {}, RaceType.SWSW)
    dot_graph = harmful_trace.toDOT()
    expected = _wrap_in_digraph()
    assert dot_graph == expected


def test_toDOT_one_node_returns_single_node_DOT_graph():
    nodes = [TraceNode(PktProcTrans("", 0), [[0]])]
    harmful_trace = HarmfulTrace(
        nodes, [ElementMetadata(0, et.SW, "test")], {}, RaceType.SWSW
    )
    dot_graph = harmful_trace.toDOT()
    expected = _wrap_in_digraph(_dotNode(0, "test<br/>[[0]]"))
    assert dot_graph == expected


def test_toDOT_one_node_no_metadata_name_returns_single_node_DOT_graph_with_element_type_label():
    vcs1 = [[0]]
    nodes = [TraceNode(PktProcTrans("", 0), vcs1)]
    metadata = [ElementMetadata(0, et.SW)]  # NO name provided, should use type
    harmful_trace = HarmfulTrace(nodes, metadata, {}, RaceType.SWSW)

    dot_graph = harmful_trace.toDOT()
    expected = _wrap_in_digraph(_dotNode(0, _dotNodeLabel(vcs1, [et.SW])))
    assert dot_graph == expected


def test_toDOT_two_nodes_returns_connected_graph_in_order():
    vcs = [[[0, 0], [0, 0]], [[1, 1], [1, 1]]]
    nodes = [
        TraceNode(PktProcTrans("", 0), vcs[0]),
        TraceNode(PktProcTrans("policy", 1), vcs[1]),
    ]
    metadata = [
        ElementMetadata(0, et.SW, "test"),
        ElementMetadata(1, et.SW, "smth"),
    ]
    harmful_trace = HarmfulTrace(nodes, metadata, {}, RaceType.SWSW)
    dot_graph = harmful_trace.toDOT()
    elNames = ["test", "smth"]
    expected = _wrap_in_digraph(
        _dotNode(0, _dotNodeLabel(vcs[0], elNames)),
        _dotNode(1, _dotNodeLabel(vcs[1], elNames)),
        _dotEdge(0, 1, "proc('policy', 1)", False),
    )
    assert dot_graph == expected


def test_toDOT_racing_transitions_returns_connected_graph_marked_correctly():
    """Race happens between the first 2 transitions of the trace"""
    vcs = [[[0, 0], [0, 0]], [[1, 1], [1, 1]], [[2, 2], [2, 2]]]
    nodes = [
        TraceNode(TraceTransition(), vcs[0]),
        TraceNode(PktProcTrans("policy", 1), vcs[1]),
        TraceNode(RcfgTrans("other policy", 0, 1, "ch"), vcs[2]),
    ]
    metadata = [
        ElementMetadata(0, et.CT),
        ElementMetadata(1, et.SW, "smth"),
    ]
    racingTransToEls = {1: 1, 2: 0}
    harmful_trace = HarmfulTrace(nodes, metadata, racingTransToEls, RaceType.SWSW)

    dot_graph = harmful_trace.toDOT()
    elNames = [et.CT, "smth"]
    expected = _wrap_in_digraph(
        _dotNode(0, _dotNodeLabel(vcs[0], elNames)),
        _dotNode(1, _dotNodeLabel(vcs[1], elNames, 1)),
        _dotEdge(0, 1, "proc('policy', 1)", True),
        _dotNode(2, _dotNodeLabel(vcs[2], elNames, 0)),
        _dotEdge(1, 2, "rcfg(ch, 'other policy', 0, 1)", True),
    )
    assert dot_graph == expected


def test_toDOT_racing_transitions_returns_connected_graph_marked_correctly2():
    """Race happens between the first 2nd and 3rd transitions of the trace"""
    vcs = [[[0, 0], [0, 0]], [[1, 1], [1, 1]], [[2, 2], [2, 2]]]
    nodes = [
        TraceNode(TraceTransition(), vcs[0]),
        TraceNode(PktProcTrans("policy", 1), vcs[1]),
        TraceNode(RcfgTrans("other policy", 0, 1, "ch"), vcs[2]),
        TraceNode(PktProcTrans("policy", 1), vcs[1]),
        TraceNode(RcfgTrans("other policy", 0, 1, "ch"), vcs[2]),
    ]
    metadata = [
        ElementMetadata(0, et.CT),
        ElementMetadata(1, et.SW, "smth"),
    ]
    racingTransToEls = {2: 0, 3: 1}  # race between the first 2 transitions
    harmful_trace = HarmfulTrace(nodes, metadata, racingTransToEls, RaceType.SWSW)

    dot_graph = harmful_trace.toDOT()
    elNames = [et.CT, "smth"]
    expected = _wrap_in_digraph(
        _dotNode(0, _dotNodeLabel(vcs[0], elNames)),
        _dotNode(1, _dotNodeLabel(vcs[1], elNames)),
        _dotEdge(0, 1, "proc('policy', 1)", False),
        _dotNode(2, _dotNodeLabel(vcs[2], elNames, 0)),
        _dotEdge(1, 2, "rcfg(ch, 'other policy', 0, 1)", True),
        _dotNode(3, _dotNodeLabel(vcs[1], elNames, 1)),
        _dotEdge(2, 3, "proc('policy', 1)", True),
        _dotNode(4, _dotNodeLabel(vcs[2], elNames)),
        _dotEdge(3, 4, "rcfg(ch, 'other policy', 0, 1)", False),
    )
    assert dot_graph == expected
