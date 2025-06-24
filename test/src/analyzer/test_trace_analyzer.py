import pytest

from src.analyzer.trace_analyzer import (RaceType, TraceAnalyzer,
                                         TraceAnalyzerError, _validateTrace)
from src.analyzer.transition_checker import TransitionsChecker
from src.trace.node import TraceNode
from src.trace.transition import PktProcTrans, RcfgTrans, TraceTransition
from src.util import DyNetKATSymbols as sym

pytest_plugins = [
    "test.src.test_utils.fixtures",
    "test.src.analyzer.test_utils.fixtures",
]


def test_validateTrace_valid_trace_and_metadata_no_exception(metadataFactory):
    trace = [
        TraceNode(TraceTransition(), [[0, 0], [0, 0]]),
        TraceNode(PktProcTrans("", 0), [[1, 0], [0, 0]]),
    ]
    elsMetadata = metadataFactory(2, 0)

    try:
        _validateTrace(trace, elsMetadata)
    except TraceAnalyzerError:
        pytest.fail("TraceAnalyzerError should not have been raised.")


def test_validateTrace_empty_transition_not_first_node_raises_error(metadataFactory):
    trace = [
        TraceNode(TraceTransition(), [[0, 0], [0, 0]]),
        TraceNode(TraceTransition(), [[0, 0], [0, 0]]),
    ]
    elsMetadata = metadataFactory(2, 0)

    with pytest.raises(TraceAnalyzerError):
        _validateTrace(trace, elsMetadata)


def test_validateTrace_transition_source_out_of_bounds_raises_error(metadataFactory):
    trace = [
        TraceNode(TraceTransition(), [[0, 0], [0, 0]]),
        TraceNode(RcfgTrans("", 2, 0, "ch"), [[0, 0], [0, 0]]),
    ]
    elsMetadata = metadataFactory(2, 0)

    with pytest.raises(TraceAnalyzerError):
        _validateTrace(trace, elsMetadata)


def test_validateTrace_transition_source_out_of_bounds_raises_error2(metadataFactory):
    trace = [
        TraceNode(TraceTransition(), [[0, 0], [0, 0]]),
        TraceNode(PktProcTrans("", 2), [[0, 0], [0, 0]]),
    ]
    elsMetadata = metadataFactory(2, 0)

    with pytest.raises(TraceAnalyzerError):
        _validateTrace(trace, elsMetadata)


def test_validateTrace_transition_destination_out_of_bounds_raises_error(metadataFactory):
    trace = [
        TraceNode(TraceTransition(), [[0, 0], [0, 0]]),
        TraceNode(RcfgTrans("", 1, 2, "ch"), [[0, 0], [0, 0]]),
    ]
    elsMetadata = metadataFactory(2, 0)

    with pytest.raises(TraceAnalyzerError):
        _validateTrace(trace, elsMetadata)


def test_validateTrace_mismatched_vector_clock_size_raises_error(metadataFactory):
    trace = [TraceNode(PktProcTrans("", 0), [[0, 0], [0]])]
    elsMetadata = metadataFactory(2, 0)

    with pytest.raises(TraceAnalyzerError):
        _validateTrace(trace, elsMetadata)


def test_validateTrace_empty_metadata_raises_error():
    trace = [TraceNode(RcfgTrans("", 0, 1, "ch"), [[0, 0], [0, 0]])]
    elsMetadata = []
    with pytest.raises(TraceAnalyzerError):
        _validateTrace(trace, elsMetadata)


def test_analyze_invalid_trace_raises_error(katch, metadataFactory):
    # out of bounds source and vector clocks not matching
    # the number of elements in the model
    trace = [
        TraceNode(TraceTransition(), [[0, 0], [0, 0]]),
        TraceNode(PktProcTrans("", 5), [[0, 0], [0, 0]]),
    ]
    elsMetadata = metadataFactory(2, 2)
    transChecker = TransitionsChecker(katch, {}, elsMetadata)
    ta = TraceAnalyzer(transChecker, elsMetadata)
    with pytest.raises(TraceAnalyzerError):
        ta.analyze(trace)


def test_analyze_invalid_trace_transition_without_source_raises_error(
        katch,
        metadataFactory
):
    trace = [
        TraceNode(TraceTransition(), [[0, 0], [0, 0]]),
        TraceNode(PktProcTrans("", 0), [[0, 0], [0, 0]]),
        TraceNode(TraceTransition(), [[0, 0], [0, 0]]),
    ]
    elsMetadata = metadataFactory(1, 1)
    transChecker = TransitionsChecker(katch, {}, elsMetadata)
    ta = TraceAnalyzer(transChecker, elsMetadata)
    with pytest.raises(TraceAnalyzerError):
        ta.analyze(trace)


def test_analyze_valid_trace_no_race_returns_none(katch, metadataFactory):
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
    elsMetadata = metadataFactory(1, 2)
    transChecker = TransitionsChecker(katch, {}, elsMetadata)
    ta = TraceAnalyzer(transChecker, elsMetadata)
    res = ta.analyze(trace)
    skippedTrans = transChecker.getSkippedRacesStr()
    assert res is None
    assert skippedTrans == ""


def test_analyze_valid_trace_2_elements_unharmful_CT_SW_race_returns_none(
    katch, metadataFactory, flowRule1, flowRule2
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
    elsMetadata = metadataFactory(1, 1)
    transChecker = TransitionsChecker(katch, {}, elsMetadata)
    ta = TraceAnalyzer(transChecker, elsMetadata)
    res = ta.analyze(trace)
    skippedTrans = transChecker.getSkippedRacesStr()
    assert res is None
    assert skippedTrans == ""


def test_analyze_valid_trace_2_elements_harmful_CT_SW_race_beginning_returns_harmful_trace(
    katch, metadataFactory, flowRule1, flowRule2
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
    elsMetadata = metadataFactory(1, 1)
    transChecker = TransitionsChecker(katch, {}, elsMetadata)
    ta = TraceAnalyzer(transChecker, elsMetadata)
    res = ta.analyze(trace)
    skippedTrans = transChecker.getSkippedRacesStr()
    assert res is not None
    assert res.raceType == RaceType.CT_SW
    assert res.elsMetadata == elsMetadata
    assert res.racingTransToEls == {0: 0, 1: 1}
    assert skippedTrans == ""


def test_analyze_valid_trace_2_elements_harmful_CT_SW_race_middle_returns_harmful_trace(
    katch, metadataFactory, flowRule1, flowRule2
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
    elsMetadata = metadataFactory(1, 1)
    transChecker = TransitionsChecker(katch, {}, elsMetadata)
    ta = TraceAnalyzer(transChecker, elsMetadata)
    res = ta.analyze(trace)
    skippedTrans = transChecker.getSkippedRacesStr()
    assert res is not None
    assert res.raceType == RaceType.CT_SW
    assert res.elsMetadata == elsMetadata 
    assert res.racingTransToEls == {2: 0, 3: 1}
    assert skippedTrans == ""


def test_analyze_valid_trace_2_elements_harmful_CT_SW_race_end_returns_harmful_trace(
    katch, metadataFactory, flowRule1, flowRule2, flowRule3
):
    SW1, CT1 = 0, 1
    trace = [
        TraceNode(TraceTransition(), [[0, 0], [0, 0]]),
        TraceNode(RcfgTrans(flowRule1, CT1, SW1, "up1"), [[1, 1], [0, 1]]),
        TraceNode(RcfgTrans(flowRule2, CT1, SW1, "up1"), [[2, 2], [0, 2]]),
        TraceNode(PktProcTrans(flowRule2, SW1), [[3, 2], [0, 2]]),  # racing
        TraceNode(RcfgTrans(flowRule3, CT1, SW1, "up1"), [[4, 3], [0, 3]]),  # racing
    ]
    elsMetadata = metadataFactory(1, 1)
    transChecker = TransitionsChecker(katch, {}, elsMetadata)
    ta = TraceAnalyzer(transChecker, elsMetadata)
    res = ta.analyze(trace)
    skippedTrans = transChecker.getSkippedRacesStr()
    assert res is not None
    assert res.raceType == RaceType.CT_SW
    assert res.elsMetadata == elsMetadata 
    assert res.racingTransToEls == {3: 0, 4: 1}
    assert skippedTrans == ""


def test_analyze_valid_trace_3_elements_unharmful_CT_SW_CT_race_returns_none(
    katch, metadataFactory, flowRule1
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
    elsMetadata = metadataFactory(1, 2)
    transChecker = TransitionsChecker(katch, {}, elsMetadata)
    ta = TraceAnalyzer(transChecker, elsMetadata)
    res = ta.analyze(trace)
    skippedTrans = transChecker.getSkippedRacesStr()
    assert res is None
    assert skippedTrans == ""


def test_analyze_valid_trace_3_elements_harmful_CT_SW_CT_race_beginning_returns_harmful_trace(
    katch, metadataFactory, flowRule1, flowRule2
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
    elsMetadata = metadataFactory(1, 2)
    transChecker = TransitionsChecker(katch, {}, elsMetadata)
    ta = TraceAnalyzer(transChecker, elsMetadata)
    res = ta.analyze(trace)
    skippedTrans = transChecker.getSkippedRacesStr()
    assert res is not None
    assert res.raceType == RaceType.CT_SW_CT
    assert res.elsMetadata == metadata1SW2CT
    assert res.racingTransToEls == {0: 1, 1: 2}
    assert skippedTrans == ""


def test_analyze_valid_trace_3_elements_harmful_CT_SW_CT_race_middle_returns_harmful_trace(
    katch, metadataFactory, flowRule1, flowRule2
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
    elsMetadata = metadataFactory(1, 2)
    transChecker = TransitionsChecker(katch, {}, elsMetadata)
    ta = TraceAnalyzer(transChecker, elsMetadata)
    res = ta.analyze(trace)
    skippedTrans = transChecker.getSkippedRacesStr()
    assert res is not None
    assert res.raceType == RaceType.CT_SW_CT
    assert res.elsMetadata == elsMetadata
    assert res.racingTransToEls == {2: 2, 3: 1}
    assert skippedTrans == ""


def test_analyze_valid_trace_3_elements_harmful_CT_SW_CT_race_end_returns_harmful_trace(
    katch, metadataFactory, flowRule1, flowRule2
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
    elsMetadata = metadataFactory(1, 2)
    transChecker = TransitionsChecker(katch, {}, elsMetadata)
    ta = TraceAnalyzer(transChecker, elsMetadata)
    res = ta.analyze(trace)
    skippedTrans = transChecker.getSkippedRacesStr()
    assert res is not None
    assert res.raceType == RaceType.CT_SW_CT
    assert res.elsMetadata == elsMetadata 
    assert res.racingTransToEls == {3: 1, 4: 2}
    assert skippedTrans == ""


def test_analyze_valid_trace_3_elements_unharmful_CT_CT_SW_race_returns_none(
    katch, metadataFactory, flowRule1, flowRule2
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
            [[3, 3, 0], [0, 4, 1], [0, 0, 1]],
        ),  # not racing with previous RCFG because they install the same policy
        TraceNode(
            RcfgTrans(flowRule1 + sym.OR + flowRule2, CT1, SW1, "up2"),
            [[4, 5, 1], [0, 5, 1], [0, 0, 1]],
        ),
    ]
    elsMetadata = metadataFactory(1, 2)
    transChecker = TransitionsChecker(katch, {}, elsMetadata)
    ta = TraceAnalyzer(transChecker, elsMetadata)
    res = ta.analyze(trace)
    skippedTrans = transChecker.getSkippedRacesStr()
    assert res is None
    assert skippedTrans == ""


def test_analyze_valid_trace_3_elements_harmful_CT_CT_SW_race_beginning_returns_harmful_trace(
    katch, metadataFactory, flowRule1, flowRule2
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
    elsMetadata = metadataFactory(1, 2)
    transChecker = TransitionsChecker(katch, {}, elsMetadata)
    ta = TraceAnalyzer(transChecker, elsMetadata)
    res = ta.analyze(trace)
    skippedTrans = transChecker.getSkippedRacesStr()
    assert res is not None
    assert res.raceType == RaceType.CT_CT_SW
    assert res.elsMetadata == elsMetadata
    assert res.racingTransToEls == {0: 2, 1: 1}
    assert skippedTrans == ""


def test_analyze_valid_trace_3_elements_harmful_CT_CT_SW_race_middle_returns_harmful_trace(
    katch, metadataFactory, flowRule1, flowRule2
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
    elsMetadata = metadataFactory(1, 1)
    transChecker = TransitionsChecker(katch, {}, elsMetadata)
    ta = TraceAnalyzer(transChecker, elsMetadata)
    res = ta.analyze(trace)
    skippedTrans = transChecker.getSkippedRacesStr()
    assert res is not None
    assert res.raceType == RaceType.CT_CT_SW
    assert res.elsMetadata == elsMetadata
    assert res.racingTransToEls == {2: 2, 3: 1}
    assert skippedTrans == ""


def test_analyze_valid_trace_3_elements_harmful_CT_CT_SW_race_end_returns_harmful_trace(
    katch, metadataFactory, flowRule1, flowRule2
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
    elsMetadata = metadataFactory(1, 2)
    transChecker = TransitionsChecker(katch, {}, elsMetadata)
    ta = TraceAnalyzer(transChecker, elsMetadata)
    res = ta.analyze(trace)
    skippedTrans = transChecker.getSkippedRacesStr()
    assert res is not None
    assert res.raceType == RaceType.CT_CT_SW
    assert res.elsMetadata == elsMetadata
    assert res.racingTransToEls == {3: 1, 4: 2}
    assert skippedTrans == ""


def test_analyze_valid_trace_4_elements_SW_SW_race_is_skipped_once_returns_none(
    katch, metadataFactory, flowRule1, flowRule2
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
    elsMetadata = metadataFactory(2, 2)
    transChecker = TransitionsChecker(katch, {}, elsMetadata)
    ta = TraceAnalyzer(transChecker, elsMetadata)
    res = ta.analyze(trace)
    skippedTrans = transChecker.getSkippedRacesStr("\t")
    assert res is None
    assert skippedTrans == "\tSW-SW: 1 times"


def test_analyze_valid_trace_4_elements_SW_SW_race_is_skipped_twice_returns_none(
    katch, metadataFactory, flowRule1, flowRule2
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
    elsMetadata = metadataFactory(2, 2)
    transChecker = TransitionsChecker(katch, {}, elsMetadata)
    ta = TraceAnalyzer(transChecker, elsMetadata)
    res = ta.analyze(trace)
    skippedTrans = transChecker.getSkippedRacesStr()
    assert res is None
    assert skippedTrans == "SW-SW: 2 times"


def test_analyze_valid_trace_3_elements_CT_SW_race_is_skipped_returns_CT_SW_CT_race(
    katch, metadataFactory, flowRule1, flowRule2
):
    SW1, CT1, CT2 = 0, 1, 2
    trace = [
        TraceNode(TraceTransition(), [[0, 0, 0], [0, 0, 0], [0, 0, 0]]),
        TraceNode(
            PktProcTrans(flowRule1, SW1),
            [[1, 0, 0], [0, 0, 0], [0, 0, 0]],
        ),  # racing with the next rcfg
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
    elsMetadata = metadataFactory(1, 2)
    transChecker = TransitionsChecker(katch, {}, elsMetadata)
    ta = TraceAnalyzer(transChecker, elsMetadata)
    res = ta.analyze(trace)
    skippedTrans = transChecker.getSkippedRacesStr()
    assert res is not None
    assert res.raceType == RaceType.CT_SW_CT
    assert res.elsMetadata == elsMetadata 
    assert res.racingTransToEls == {3: 1, 4: 2}
    assert skippedTrans == f"{RaceType.CT_SW}: 1 times"


def test_analyze_valid_trace_4_elements_unharmful_CT_SW_race_different_rcfg_target_returns_none(
    katch, metadataFactory, flowRule1, flowRule2
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
    elsMetadata = metadataFactory(2, 2)
    transChecker = TransitionsChecker(katch, {}, elsMetadata)
    ta = TraceAnalyzer(transChecker, elsMetadata)
    res = ta.analyze(trace)
    skippedTrans = transChecker.getSkippedRacesStr()
    assert res is None
    assert skippedTrans == ""


def test_analyze_valid_trace_4_elements_unharmful_CT_SW_race_different_rcfg_target_returns_none2(
    katch, metadataFactory, flowRule1, flowRule2
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
    elsMetadata = metadataFactory(2, 2)
    transChecker = TransitionsChecker(katch, {}, elsMetadata)
    ta = TraceAnalyzer(transChecker, elsMetadata)
    res = ta.analyze(trace)
    skippedTrans = transChecker.getSkippedRacesStr()
    assert res is None
    assert skippedTrans == ""
