import pytest

from src.analyzer.trace_analyzer import (RaceType, TraceAnalyzer,
                                         TraceAnalyzerError, _validateTrace)
from src.model.dnk_maude_model import ElementMetadata, ElementType
from src.trace.node import TraceNode
from src.trace.transition import PktProcTrans, RcfgTrans, TraceTransition
from src.util import DyNetKATSymbols as sym

pytest_plugins = [
    "test.src.test_utils.fixtures",
    "test.src.analyzer.test_utils.fixtures",
]


def test_validateTrace_valid_trace_and_metadata_no_exception():
    trace = [
        TraceNode(TraceTransition(), [[0, 0], [0, 0]]),
        TraceNode(PktProcTrans("", 0), [[1, 0], [0, 0]]),
    ]
    elsMetadata = [
        ElementMetadata(1, ElementType.SW),
        ElementMetadata(2, ElementType.SW),
    ]
    try:
        _validateTrace(trace, elsMetadata)
    except TraceAnalyzerError:
        pytest.fail("TraceAnalyzerError should not have been raised.")


def test_validateTrace_empty_transition_not_first_node_raises_error():
    trace = [
        TraceNode(TraceTransition(), [[0, 0], [0, 0]]),
        TraceNode(TraceTransition(), [[0, 0], [0, 0]]),
    ]
    elsMetadata = [
        ElementMetadata(1, ElementType.SW),
        ElementMetadata(2, ElementType.SW),
    ]
    with pytest.raises(TraceAnalyzerError):
        _validateTrace(trace, elsMetadata)


def test_validateTrace_transition_source_out_of_bounds_raises_error():
    trace = [
        TraceNode(TraceTransition(), [[0, 0], [0, 0]]),
        TraceNode(RcfgTrans("", 2, 0, "ch"), [[0, 0], [0, 0]]),
    ]
    elsMetadata = [
        ElementMetadata(1, ElementType.SW),
        ElementMetadata(2, ElementType.SW),
    ]
    with pytest.raises(TraceAnalyzerError):
        _validateTrace(trace, elsMetadata)


def test_validateTrace_transition_source_out_of_bounds_raises_error2():
    trace = [
        TraceNode(TraceTransition(), [[0, 0], [0, 0]]),
        TraceNode(PktProcTrans("", 2), [[0, 0], [0, 0]]),
    ]
    elsMetadata = [
        ElementMetadata(1, ElementType.SW),
        ElementMetadata(2, ElementType.SW),
    ]
    with pytest.raises(TraceAnalyzerError):
        _validateTrace(trace, elsMetadata)


def test_validateTrace_transition_destination_out_of_bounds_raises_error():
    trace = [
        TraceNode(TraceTransition(), [[0, 0], [0, 0]]),
        TraceNode(RcfgTrans("", 1, 2, "ch"), [[0, 0], [0, 0]]),
    ]
    elsMetadata = [
        ElementMetadata(1, ElementType.SW),
        ElementMetadata(2, ElementType.SW),
    ]
    with pytest.raises(TraceAnalyzerError):
        _validateTrace(trace, elsMetadata)


def test_validateTrace_mismatched_vector_clock_size_raises_error():
    trace = [TraceNode(PktProcTrans("", 0), [[0, 0], [0]])]
    elsMetadata = [
        ElementMetadata(1, ElementType.SW),
        ElementMetadata(2, ElementType.SW),
    ]
    with pytest.raises(TraceAnalyzerError):
        _validateTrace(trace, elsMetadata)


def test_validateTrace_empty_metadata_raises_error():
    trace = [TraceNode(RcfgTrans("", 0, 1, "ch"), [[0, 0], [0, 0]])]
    elsMetadata = []
    with pytest.raises(TraceAnalyzerError):
        _validateTrace(trace, elsMetadata)


def test_analyze_invalid_trace_raises_error(transChecker2SW2CT, metadata2SW2CT):
    # out of bounds source and vector clocks not matching
    # the number of elements in the model
    trace = [
        TraceNode(TraceTransition(), [[0, 0], [0, 0]]),
        TraceNode(PktProcTrans("", 5), [[0, 0], [0, 0]]),
    ]
    ta = TraceAnalyzer(transChecker2SW2CT, metadata2SW2CT)
    with pytest.raises(TraceAnalyzerError):
        ta.analyze(trace)


def test_analyze_invalid_trace_transition_without_source_raises_error(
    transChecker1SW1CT, metadata1SW1CT
):
    trace = [
        TraceNode(TraceTransition(), [[0, 0], [0, 0]]),
        TraceNode(PktProcTrans("", 0), [[0, 0], [0, 0]]),
        TraceNode(TraceTransition(), [[0, 0], [0, 0]]),
    ]
    ta = TraceAnalyzer(transChecker1SW1CT, metadata1SW1CT)
    with pytest.raises(TraceAnalyzerError):
        ta.analyze(trace)


def test_analyze_valid_trace_no_race_returns_none(transChecker1SW2CT, metadata1SW2CT):
    SW1, CT1, CT2 = 0, 1, 2
    # all transition policies are not valid KATch input to ensure KATch is not
    # run at all when analyzing the trace
    trace = [
        TraceNode(TraceTransition(), [[0, 0, 0], [0, 0, 0], [0, 0, 0]]),
        TraceNode(
            RcfgTrans("policy1", CT1, SW1, "up1"), [[1, 1, 0], [0, 1, 0], [0, 0, 0]]
        ),
        TraceNode(PktProcTrans("policy1", SW1), [[2, 1, 0], [0, 1, 0], [0, 0, 0]]),
        TraceNode(
            RcfgTrans("help", SW1, CT1, "help1"), [[3, 1, 0], [3, 2, 0], [0, 0, 0]]
        ),
        TraceNode(
            RcfgTrans("help", CT1, CT2, "help2"), [[3, 1, 0], [3, 3, 0], [3, 3, 1]]
        ),
        TraceNode(
            RcfgTrans("policy2", CT2, SW1, "up2"), [[4, 3, 2], [3, 3, 0], [3, 3, 2]]
        ),
        TraceNode(PktProcTrans("policy2", SW1), [[5, 3, 2], [3, 3, 0], [3, 3, 2]]),
    ]
    ta = TraceAnalyzer(transChecker1SW2CT, metadata1SW2CT)
    res = ta.analyze(trace)
    skippedTrans = transChecker1SW2CT.getSkippedRacesStr()
    assert res is None
    assert skippedTrans == ""


def test_analyze_valid_trace_2_elements_unharmful_CT_SW_race_returns_none(
    transChecker1SW1CT, metadata1SW1CT, flowRule1, flowRule2
):
    SW1, CT1 = 0, 1
    trace = [
        TraceNode(TraceTransition(), [[0, 0], [0, 0]]),
        TraceNode(RcfgTrans(flowRule1, CT1, SW1, "up1"), [[1, 1], [0, 1]]),
        TraceNode(PktProcTrans(flowRule1, SW1), [[2, 1], [0, 1]]),
        TraceNode(
            RcfgTrans(flowRule1 + sym.OR + flowRule2, CT1, SW1, "up1"), [[3, 2], [0, 2]]
        ),
        TraceNode(PktProcTrans(flowRule1 + sym.OR + flowRule2, SW1), [[4, 2], [0, 2]]),
    ]
    ta = TraceAnalyzer(transChecker1SW1CT, metadata1SW1CT)
    res = ta.analyze(trace)
    skippedTrans = transChecker1SW1CT.getSkippedRacesStr()
    assert res is None
    assert skippedTrans == ""


def test_analyze_valid_trace_2_elements_harmful_CT_SW_race_beginning_returns_harmful_trace(
    transChecker1SW1CT, metadata1SW1CT, flowRule1, flowRule2
):
    SW1, CT1 = 0, 1
    trace = [
        TraceNode(PktProcTrans(flowRule1, SW1), [[1, 0], [0, 0]]),  # racing
        TraceNode(RcfgTrans(flowRule2, CT1, SW1, "up1"), [[2, 1], [0, 1]]),  # racing
        TraceNode(PktProcTrans(flowRule2, SW1), [[3, 1], [0, 1]]),
        TraceNode(
            RcfgTrans(flowRule1 + sym.OR + flowRule2, CT1, SW1, "up1"), [[4, 2], [0, 2]]
        ),
        TraceNode(PktProcTrans(flowRule2 + sym.OR + flowRule2, SW1), [[5, 2], [0, 2]]),
    ]
    ta = TraceAnalyzer(transChecker1SW1CT, metadata1SW1CT)
    res = ta.analyze(trace)
    skippedTrans = transChecker1SW1CT.getSkippedRacesStr()
    assert res is not None
    assert res.raceType == RaceType.CT_SW
    assert res.elsMetadata == metadata1SW1CT
    assert res.racingTransToEls == {0: 0, 1: 1}
    assert skippedTrans == ""


def test_analyze_valid_trace_2_elements_harmful_CT_SW_race_middle_returns_harmful_trace(
    transChecker1SW1CT, metadata1SW1CT, flowRule1, flowRule2
):
    SW1, CT1 = 0, 1
    trace = [
        TraceNode(TraceTransition(), [[0, 0], [0, 0]]),
        TraceNode(RcfgTrans(flowRule1, CT1, SW1, "up1"), [[1, 1], [0, 1]]),
        TraceNode(PktProcTrans(flowRule1, SW1), [[2, 1], [0, 1]]),  # racing
        TraceNode(RcfgTrans(flowRule2, CT1, SW1, "up1"), [[3, 2], [0, 2]]),  # racing
        TraceNode(PktProcTrans(flowRule2, SW1), [[4, 2], [0, 2]]),
        TraceNode(
            RcfgTrans(flowRule1 + sym.OR + flowRule2, CT1, SW1, "up1"), [[5, 3], [0, 3]]
        ),
    ]
    ta = TraceAnalyzer(transChecker1SW1CT, metadata1SW1CT)
    res = ta.analyze(trace)
    skippedTrans = transChecker1SW1CT.getSkippedRacesStr()
    assert res is not None
    assert res.raceType == RaceType.CT_SW
    assert res.elsMetadata == metadata1SW1CT
    assert res.racingTransToEls == {2: 0, 3: 1}
    assert skippedTrans == ""


def test_analyze_valid_trace_2_elements_harmful_CT_SW_race_end_returns_harmful_trace(
    transChecker1SW1CT, metadata1SW1CT, flowRule1, flowRule2, flowRule3
):
    SW1, CT1 = 0, 1
    trace = [
        TraceNode(TraceTransition(), [[0, 0], [0, 0]]),
        TraceNode(RcfgTrans(flowRule1, CT1, SW1, "up1"), [[1, 1], [0, 1]]),
        TraceNode(RcfgTrans(flowRule2, CT1, SW1, "up1"), [[2, 2], [0, 2]]),
        TraceNode(PktProcTrans(flowRule2, SW1), [[3, 2], [0, 2]]),  # racing
        TraceNode(RcfgTrans(flowRule3, CT1, SW1, "up1"), [[4, 3], [0, 3]]),  # racing
    ]
    ta = TraceAnalyzer(transChecker1SW1CT, metadata1SW1CT)
    res = ta.analyze(trace)
    skippedTrans = transChecker1SW1CT.getSkippedRacesStr()
    assert res is not None
    assert res.raceType == RaceType.CT_SW
    assert res.elsMetadata == metadata1SW1CT
    assert res.racingTransToEls == {3: 0, 4: 1}
    assert skippedTrans == ""


def test_analyze_valid_trace_3_elements_unharmful_CT_SW_CT_race_returns_none(
    transChecker1SW2CT, metadata1SW2CT, flowRule1
):
    SW1, CT1, CT2 = 0, 1, 2
    trace = [
        TraceNode(TraceTransition(), [[0, 0, 0], [0, 0, 0], [0, 0, 0]]),
        TraceNode(
            RcfgTrans("policy1", CT1, SW1, "up1"), [[1, 1, 0], [0, 1, 0], [0, 0, 0]]
        ),
        TraceNode(
            RcfgTrans("policy2", CT1, SW1, "up1"), [[2, 2, 0], [0, 2, 0], [0, 0, 0]]
        ),
        TraceNode(
            RcfgTrans(flowRule1, CT1, SW1, "up1"), [[3, 3, 0], [0, 3, 0], [0, 0, 0]]
        ),
        TraceNode(
            RcfgTrans(flowRule1, CT2, SW1, "up2"), [[4, 3, 1], [0, 3, 0], [0, 0, 1]]
        ),  # not racing with previous RCFG because they install the same policy
        TraceNode(PktProcTrans(flowRule1, SW1), [[5, 3, 1], [0, 3, 0], [0, 0, 1]]),
    ]
    ta = TraceAnalyzer(transChecker1SW2CT, metadata1SW2CT)
    res = ta.analyze(trace)
    skippedTrans = transChecker1SW2CT.getSkippedRacesStr()
    assert res is None
    assert skippedTrans == ""


def test_analyze_valid_trace_3_elements_harmful_CT_SW_CT_race_beginning_returns_harmful_trace(
    transChecker1SW2CT, metadata1SW2CT, flowRule1, flowRule2
):
    SW1, CT1, CT2 = 0, 1, 2
    trace = [
        TraceNode(
            RcfgTrans(flowRule1, CT1, SW1, "up1"), [[1, 1, 0], [0, 1, 0], [0, 0, 0]]
        ),  # racing
        TraceNode(
            RcfgTrans(flowRule2, CT2, SW1, "up2"), [[2, 1, 1], [0, 1, 0], [0, 0, 1]]
        ),  # racing
        TraceNode(PktProcTrans(flowRule2, SW1), [[3, 1, 1], [0, 1, 0], [0, 0, 1]]),
        TraceNode(PktProcTrans(flowRule2, SW1), [[4, 1, 1], [0, 1, 0], [0, 0, 1]]),
    ]
    ta = TraceAnalyzer(transChecker1SW2CT, metadata1SW2CT)
    res = ta.analyze(trace)
    skippedTrans = transChecker1SW2CT.getSkippedRacesStr()
    assert res is not None
    assert res.raceType == RaceType.CT_SW_CT
    assert res.elsMetadata == metadata1SW2CT
    assert res.racingTransToEls == {0: 1, 1: 2}
    assert skippedTrans == ""


def test_analyze_valid_trace_3_elements_harmful_CT_SW_CT_race_middle_returns_harmful_trace(
    transChecker1SW2CT, metadata1SW2CT, flowRule1, flowRule2
):
    SW1, CT1, CT2 = 0, 1, 2
    trace = [
        TraceNode(TraceTransition(), [[0, 0, 0], [0, 0, 0], [0, 0, 0]]),
        TraceNode(
            RcfgTrans("policy1", CT2, SW1, "up2"), [[1, 0, 1], [0, 0, 0], [0, 0, 1]]
        ),
        TraceNode(
            RcfgTrans(flowRule2, CT2, SW1, "up2"), [[2, 0, 2], [0, 0, 0], [0, 0, 2]]
        ),  # racing
        TraceNode(
            RcfgTrans(flowRule1, CT1, SW1, "up1"), [[3, 1, 2], [0, 1, 0], [0, 0, 2]]
        ),  # racing
        TraceNode(PktProcTrans(flowRule2, SW1), [[4, 1, 2], [0, 1, 0], [0, 0, 2]]),
    ]
    ta = TraceAnalyzer(transChecker1SW2CT, metadata1SW2CT)
    res = ta.analyze(trace)
    skippedTrans = transChecker1SW2CT.getSkippedRacesStr()
    assert res is not None
    assert res.raceType == RaceType.CT_SW_CT
    assert res.elsMetadata == metadata1SW2CT
    assert res.racingTransToEls == {2: 2, 3: 1}
    assert skippedTrans == ""


def test_analyze_valid_trace_3_elements_harmful_CT_SW_CT_race_end_returns_harmful_trace(
    transChecker1SW2CT, metadata1SW2CT, flowRule1, flowRule2
):
    SW1, CT1, CT2 = 0, 1, 2
    trace = [
        TraceNode(TraceTransition(), [[0, 0, 0], [0, 0, 0], [0, 0, 0]]),
        TraceNode(
            RcfgTrans("policy1", CT1, SW1, "up1"), [[1, 1, 0], [0, 1, 0], [0, 0, 0]]
        ),
        TraceNode(
            RcfgTrans("policy2", CT1, SW1, "up1"), [[2, 2, 0], [0, 2, 0], [0, 0, 0]]
        ),
        TraceNode(
            RcfgTrans(flowRule1, CT1, SW1, "up1"), [[3, 3, 0], [0, 3, 0], [0, 0, 0]]
        ),  # racing
        TraceNode(
            RcfgTrans(flowRule2, CT2, SW1, "up2"), [[4, 3, 1], [0, 3, 0], [0, 0, 1]]
        ),  # racing
    ]
    ta = TraceAnalyzer(transChecker1SW2CT, metadata1SW2CT)
    res = ta.analyze(trace)
    skippedTrans = transChecker1SW2CT.getSkippedRacesStr()
    assert res is not None
    assert res.raceType == RaceType.CT_SW_CT
    assert res.elsMetadata == metadata1SW2CT
    assert res.racingTransToEls == {3: 1, 4: 2}
    assert skippedTrans == ""


def test_analyze_valid_trace_3_elements_unharmful_CT_CT_SW_race_returns_none(
    transChecker1SW2CT, metadata1SW2CT, flowRule1, flowRule2
):
    SW1, CT1, CT2 = 0, 1, 2
    trace = [
        TraceNode(TraceTransition(), [[0, 0, 0], [0, 0, 0], [0, 0, 0]]),
        TraceNode(
            RcfgTrans("policy1", CT1, SW1, "up1"), [[1, 1, 0], [0, 1, 0], [0, 0, 0]]
        ),
        TraceNode(
            RcfgTrans("policy2", CT1, SW1, "up1"), [[2, 2, 0], [0, 2, 0], [0, 0, 0]]
        ),
        TraceNode(
            RcfgTrans(flowRule1, CT1, SW1, "up1"), [[3, 3, 0], [0, 3, 0], [0, 0, 0]]
        ),
        TraceNode(
            RcfgTrans(flowRule1 + sym.OR + flowRule2, CT2, CT1, "up2"),
            [[3, 3, 0], [0, 4, 1], [0, 0, 1]]
        ),  # not racing with previous RCFG because they install the same policy
        TraceNode(
            RcfgTrans(flowRule1 + sym.OR + flowRule2, CT1, SW1, "up2"),
            [[4, 5, 1], [0, 5, 1], [0, 0, 1]]
        ),
    ]
    ta = TraceAnalyzer(transChecker1SW2CT, metadata1SW2CT)
    res = ta.analyze(trace)
    skippedTrans = transChecker1SW2CT.getSkippedRacesStr()
    assert res is None
    assert skippedTrans == ""


def test_analyze_valid_trace_3_elements_harmful_CT_CT_SW_race_beginning_returns_harmful_trace(
    transChecker1SW2CT, metadata1SW2CT, flowRule1, flowRule2
):
    SW1, CT1, CT2 = 0, 1, 2
    trace = [
        TraceNode(
            RcfgTrans(flowRule1, CT2, SW1, "up1"), [[1, 0, 1], [0, 0, 0], [0, 0, 1]]
        ),  # racing
        TraceNode(
            RcfgTrans(flowRule2, CT1, CT2, "up2"), [[1, 0, 1], [0, 1, 0], [0, 1, 2]]
        ),  # racing
        TraceNode(
            RcfgTrans(flowRule2, CT2, SW1, "up1"), [[2, 1, 3], [0, 1, 0], [0, 1, 3]]
        ),
        TraceNode(PktProcTrans(flowRule1, SW1), [[3, 1, 3], [0, 1, 0], [0, 1, 3]]),
        TraceNode(PktProcTrans(flowRule1, SW1), [[4, 1, 3], [0, 1, 0], [0, 1, 3]]),
    ]
    ta = TraceAnalyzer(transChecker1SW2CT, metadata1SW2CT)
    res = ta.analyze(trace)
    skippedTrans = transChecker1SW2CT.getSkippedRacesStr()
    assert res is not None
    assert res.raceType == RaceType.CT_CT_SW
    assert res.elsMetadata == metadata1SW2CT
    assert res.racingTransToEls == {0: 2, 1: 1}
    assert skippedTrans == ""


def test_analyze_valid_trace_3_elements_harmful_CT_CT_SW_race_middle_returns_harmful_trace(
    transChecker1SW2CTSkipCTSW, metadata1SW2CT, flowRule1, flowRule2
):
    SW1, CT1, CT2 = 0, 1, 2
    trace = [
        TraceNode(TraceTransition(), [[0, 0, 0], [0, 0, 0], [0, 0, 0]]),
        TraceNode(
            RcfgTrans("policy1", CT2, SW1, "up2"), [[1, 0, 1], [0, 0, 0], [0, 0, 1]]
        ),
        TraceNode(
            RcfgTrans(flowRule2, CT2, SW1, "up2"), [[2, 0, 2], [0, 0, 0], [0, 0, 2]]
        ),  # racing
        TraceNode(
            RcfgTrans(flowRule1, CT1, CT2, "up1"), [[2, 0, 2], [0, 1, 0], [0, 1, 3]]
        ),  # racing
        TraceNode(PktProcTrans(flowRule2, SW1), [[3, 0, 2], [0, 1, 0], [0, 1, 3]]),
        # also racing, but the CT_CT_SW race should be found first
    ]
    ta = TraceAnalyzer(transChecker1SW2CTSkipCTSW, metadata1SW2CT)
    res = ta.analyze(trace)
    skippedTrans = transChecker1SW2CTSkipCTSW.getSkippedRacesStr()
    assert res is not None
    assert res.raceType == RaceType.CT_CT_SW
    assert res.elsMetadata == metadata1SW2CT
    assert res.racingTransToEls == {2: 2, 3: 1}
    assert skippedTrans == ""


def test_analyze_valid_trace_3_elements_harmful_CT_CT_SW_race_end_returns_harmful_trace(
    transChecker1SW2CT, metadata1SW2CT, flowRule1, flowRule2
):
    SW1, CT1, CT2 = 0, 1, 2
    trace = [
        TraceNode(TraceTransition(), [[0, 0, 0], [0, 0, 0], [0, 0, 0]]),
        TraceNode(
            RcfgTrans("policy1", CT1, SW1, "up1"), [[1, 1, 0], [0, 1, 0], [0, 0, 0]]
        ),
        TraceNode(
            RcfgTrans("policy2", CT1, SW1, "up1"), [[2, 2, 0], [0, 2, 0], [0, 0, 0]]
        ),
        TraceNode(
            RcfgTrans(flowRule1, CT1, SW1, "up1"), [[3, 3, 0], [0, 3, 0], [0, 0, 0]]
        ),  # racing
        TraceNode(
            RcfgTrans(flowRule2, CT2, CT1, "up2"), [[3, 3, 0], [0, 4, 1], [0, 0, 1]]
        ),  # racing
    ]
    ta = TraceAnalyzer(transChecker1SW2CT, metadata1SW2CT)
    res = ta.analyze(trace)
    skippedTrans = transChecker1SW2CT.getSkippedRacesStr()
    assert res is not None
    assert res.raceType == RaceType.CT_CT_SW
    assert res.elsMetadata == metadata1SW2CT
    assert res.racingTransToEls == {3: 1, 4: 2}
    assert skippedTrans == ""


def test_analyze_valid_trace_4_elements_SW_SW_race_is_skipped_once_returns_none(
    transChecker2SW2CT, metadata2SW2CT, flowRule1, flowRule2
):
    SW1, SW2, CT1, CT2 = 0, 1, 2, 3
    trace = [
        TraceNode(
            TraceTransition(), [[0, 0, 0, 0], [0, 0, 0, 0], [0, 0, 0, 0], [0, 0, 0, 0]]
        ),
        TraceNode(
            RcfgTrans(flowRule1, CT1, SW1, "up1"),
            [[1, 0, 1, 0], [0, 0, 0, 0], [0, 0, 1, 0], [0, 0, 0, 0]],
        ),
        TraceNode(
            RcfgTrans(flowRule1, CT2, SW2, "up2"),
            [[1, 0, 1, 0], [0, 1, 0, 1], [0, 0, 1, 0], [0, 0, 0, 1]],
        ),
        TraceNode(
            PktProcTrans(flowRule1, SW2),
            [[1, 0, 1, 0], [0, 2, 0, 1], [0, 0, 1, 0], [0, 0, 0, 1]],
        ),
        TraceNode(
            PktProcTrans(flowRule1, SW1),
            [[2, 0, 1, 0], [0, 2, 0, 1], [0, 0, 1, 0], [0, 0, 0, 1]],
        ),
    ]
    ta = TraceAnalyzer(transChecker2SW2CT, metadata2SW2CT)
    res = ta.analyze(trace)
    skippedTrans = transChecker2SW2CT.getSkippedRacesStr("\t")
    assert res is None
    assert skippedTrans == "\tSW-SW: 1 times"


def test_analyze_valid_trace_4_elements_SW_SW_race_is_skipped_twice_returns_none(
    transChecker2SW2CT, metadata2SW2CT, flowRule1, flowRule2
):
    SW1, SW2, CT1, CT2 = 0, 1, 2, 3
    trace = [
        TraceNode(
            TraceTransition(), [[0, 0, 0, 0], [0, 0, 0, 0], [0, 0, 0, 0], [0, 0, 0, 0]]
        ),
        TraceNode(
            RcfgTrans(flowRule1, CT1, SW1, "up1"),
            [[1, 0, 1, 0], [0, 0, 0, 0], [0, 0, 1, 0], [0, 0, 0, 0]],
        ),
        TraceNode(
            RcfgTrans(flowRule1, CT2, SW2, "up2"),
            [[1, 0, 1, 0], [0, 1, 0, 1], [0, 0, 1, 0], [0, 0, 0, 1]],
        ),
        TraceNode(
            PktProcTrans(flowRule1, SW2),
            [[1, 0, 1, 0], [0, 2, 0, 1], [0, 0, 1, 0], [0, 0, 0, 1]],
        ),
        TraceNode(
            PktProcTrans(flowRule1, SW1),
            [[2, 0, 1, 0], [0, 2, 0, 1], [0, 0, 1, 0], [0, 0, 0, 1]],
        ),
        TraceNode(
            PktProcTrans(flowRule1, SW2),
            [[2, 0, 1, 0], [0, 3, 0, 1], [0, 0, 1, 0], [0, 0, 0, 1]],
        ),
    ]
    ta = TraceAnalyzer(transChecker2SW2CT, metadata2SW2CT)
    res = ta.analyze(trace)
    skippedTrans = transChecker2SW2CT.getSkippedRacesStr()
    assert res is None
    assert skippedTrans == "SW-SW: 2 times"


def test_analyze_valid_trace_3_elements_CT_SW_race_is_skipped_returns_CT_SW_CT_race(
    transChecker1SW2CTSkipCTSW, metadata1SW2CT, flowRule1, flowRule2
):
    SW1, CT1, CT2 = 0, 1, 2
    trace = [
        TraceNode(TraceTransition(), [[0, 0, 0], [0, 0, 0], [0, 0, 0]]),
        TraceNode(
            PktProcTrans(flowRule1, SW1),
            [[1, 0, 0], [0, 0, 0], [0, 0, 0]],
        ),  # racing with all upcoming rcfgs (3 times in total)
        TraceNode(
            RcfgTrans("policy1", CT1, SW1, "up1"), [[2, 1, 0], [0, 1, 0], [0, 0, 0]]
        ),
        TraceNode(
            RcfgTrans(flowRule1, CT1, SW1, "up1"), [[3, 2, 0], [0, 2, 0], [0, 0, 0]]
        ),  # racing
        TraceNode(
            RcfgTrans(flowRule2, CT2, SW1, "up2"), [[4, 2, 1], [0, 2, 0], [0, 0, 1]]
        ),  # racing
    ]
    ta = TraceAnalyzer(transChecker1SW2CTSkipCTSW, metadata1SW2CT)
    res = ta.analyze(trace)
    skippedTrans = transChecker1SW2CTSkipCTSW.getSkippedRacesStr()
    assert res is not None
    assert res.raceType == RaceType.CT_SW_CT
    assert res.elsMetadata == metadata1SW2CT
    assert res.racingTransToEls == {3: 1, 4: 2}
    assert skippedTrans == f"{RaceType.CT_SW}: 3 times"


def test_analyze_valid_trace_4_elements_unharmful_CT_SW_race_different_rcfg_target_returns_none(
    transChecker2SW2CT, metadata2SW2CT, flowRule1, flowRule2
):
    SW1, SW2, CT1 = 0, 1, 2
    trace = [
        TraceNode(
            TraceTransition(), [[0, 0, 0, 0], [0, 0, 0, 0], [0, 0, 0, 0], [0, 0, 0, 0]]
        ),
        TraceNode(
            PktProcTrans(flowRule2, SW2),
            [[0, 0, 0, 0], [0, 1, 0, 0], [0, 0, 0, 0], [0, 0, 0, 0]],
        ),
        TraceNode(
            PktProcTrans(flowRule2, SW2),
            [[0, 0, 0, 0], [0, 2, 0, 0], [0, 0, 0, 0], [0, 0, 0, 0]],
        ),
        TraceNode(
            RcfgTrans(flowRule1, CT1, SW1, "up1"),
            [[1, 0, 1, 0], [0, 2, 0, 0], [0, 0, 1, 0], [0, 0, 0, 0]],
        ),
    ]
    ta = TraceAnalyzer(transChecker2SW2CT, metadata2SW2CT)
    res = ta.analyze(trace)
    skippedTrans = transChecker2SW2CT.getSkippedRacesStr()
    assert res is None
    assert skippedTrans == ""


def test_analyze_valid_trace_4_elements_unharmful_CT_SW_race_different_rcfg_target_returns_none2(
    transChecker2SW2CT, metadata2SW2CT, flowRule1, flowRule2
):
    SW1, SW2, CT1 = 0, 1, 2
    trace = [
        TraceNode(
            TraceTransition(), [[0, 0, 0, 0], [0, 0, 0, 0], [0, 0, 0, 0], [0, 0, 0, 0]]
        ),
        TraceNode(
            RcfgTrans(flowRule1, CT1, SW1, "up1"),
            [[1, 0, 1, 0], [0, 0, 0, 0], [0, 0, 1, 0], [0, 0, 0, 0]],
        ),
        TraceNode(
            PktProcTrans(flowRule2, SW2),
            [[1, 0, 1, 0], [0, 1, 0, 0], [0, 0, 1, 0], [0, 0, 0, 0]],
        ),
    ]
    ta = TraceAnalyzer(transChecker2SW2CT, metadata2SW2CT)
    res = ta.analyze(trace)
    skippedTrans = transChecker2SW2CT.getSkippedRacesStr()
    assert res is None
    assert skippedTrans == ""
