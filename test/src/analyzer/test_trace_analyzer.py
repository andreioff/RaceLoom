from test.src.analyzer.test_utils.util import raceSafetyDict

import pytest

from src.analyzer.trace_analyzer import (RaceType, TraceAnalyzer,
                                         TraceAnalyzerError, _validateTrace)
from src.analyzer.transition_checker import TransitionsChecker
from src.trace.node import TraceNode
from src.trace.transition import PktProcTrans, RcfgTrans, TraceTransition

pytest_plugins = [
    "test.src.test_utils.fixtures",
    "test.src.analyzer.test_utils.fixtures",
]


def test_validateTrace_valid_trace_and_metadata_no_exception(metadata1SW1CT):
    trace = [
        TraceNode(TraceTransition(), [[0, 0], [0, 0]]),
        TraceNode(PktProcTrans("", 0), [[1, 0], [0, 0]]),
    ]

    try:
        _validateTrace(trace, metadata1SW1CT.elements)
    except TraceAnalyzerError:
        pytest.fail("TraceAnalyzerError should not have been raised.")


def test_validateTrace_empty_transition_not_first_node_raises_error(metadata1SW1CT):
    trace = [
        TraceNode(TraceTransition(), [[0, 0], [0, 0]]),
        TraceNode(TraceTransition(), [[0, 0], [0, 0]]),
    ]

    with pytest.raises(TraceAnalyzerError):
        _validateTrace(trace, metadata1SW1CT.elements)


def test_validateTrace_transition_source_out_of_bounds_raises_error(metadata1SW1CT):
    trace = [
        TraceNode(TraceTransition(), [[0, 0], [0, 0]]),
        TraceNode(RcfgTrans("", 2, 0, "ch"), [[0, 0], [0, 0]]),
    ]

    with pytest.raises(TraceAnalyzerError):
        _validateTrace(trace, metadata1SW1CT.elements)


def test_validateTrace_transition_source_out_of_bounds_raises_error2(metadata1SW1CT):
    trace = [
        TraceNode(TraceTransition(), [[0, 0], [0, 0]]),
        TraceNode(PktProcTrans("", 2), [[0, 0], [0, 0]]),
    ]

    with pytest.raises(TraceAnalyzerError):
        _validateTrace(trace, metadata1SW1CT.elements)


def test_validateTrace_transition_destination_out_of_bounds_raises_error(
    metadata1SW1CT,
):
    trace = [
        TraceNode(TraceTransition(), [[0, 0], [0, 0]]),
        TraceNode(RcfgTrans("", 1, 2, "ch"), [[0, 0], [0, 0]]),
    ]

    with pytest.raises(TraceAnalyzerError):
        _validateTrace(trace, metadata1SW1CT.elements)


def test_validateTrace_mismatched_vector_clock_size_raises_error(metadata1SW1CT):
    trace = [TraceNode(PktProcTrans("", 0), [[0, 0], [0]])]

    with pytest.raises(TraceAnalyzerError):
        _validateTrace(trace, metadata1SW1CT.elements)


def test_validateTrace_empty_metadata_raises_error():
    trace = [TraceNode(RcfgTrans("", 0, 1, "ch"), [[0, 0], [0, 0]])]
    with pytest.raises(TraceAnalyzerError):
        _validateTrace(trace, [])


def test_analyze_invalid_trace_raises_error(katch, metadata2SW2CT):
    # out of bounds source and vector clocks not matching
    # the number of elements in the model
    trace = [
        TraceNode(TraceTransition(), [[0, 0], [0, 0]]),
        TraceNode(PktProcTrans("", 5), [[0, 0], [0, 0]]),
    ]
    elsMetadata = metadata2SW2CT.elements
    transChecker = TransitionsChecker(katch, {}, elsMetadata)
    ta = TraceAnalyzer(transChecker, elsMetadata)
    with pytest.raises(TraceAnalyzerError):
        ta.analyze(trace)


def test_analyze_invalid_trace_transition_without_source_raises_error(
    katch, metadata1SW1CT
):
    trace = [
        TraceNode(TraceTransition(), [[0, 0], [0, 0]]),
        TraceNode(PktProcTrans("", 0), [[0, 0], [0, 0]]),
        TraceNode(TraceTransition(), [[0, 0], [0, 0]]),
    ]
    elsMetadata = metadata1SW1CT.elements
    transChecker = TransitionsChecker(katch, {}, elsMetadata)
    ta = TraceAnalyzer(transChecker, elsMetadata)
    with pytest.raises(TraceAnalyzerError):
        ta.analyze(trace)


def test_analysis_of_no_race_detects_nothing(katch, trace_1SW_2CT_no_race):
    td = trace_1SW_2CT_no_race
    props = raceSafetyDict(td.safetyProp)
    transChecker = TransitionsChecker(katch, props, td.metadata)
    ta = TraceAnalyzer(transChecker, td.metadata)

    res = ta.analyze(td.trace)
    skippedTrans = transChecker.getSkippedRacesStr()

    assert res is None
    assert skippedTrans == ""


def test_analysis_of_unharmful_CT_SW_race_detects_nothing(
    katch, trace_1SW_1CT_unharmful_CT_SW_race
):
    td = trace_1SW_1CT_unharmful_CT_SW_race
    props = raceSafetyDict(td.safetyProp)
    transChecker = TransitionsChecker(katch, props, td.metadata)
    ta = TraceAnalyzer(transChecker, td.metadata)

    res = ta.analyze(td.trace)
    skippedTrans = transChecker.getSkippedRacesStr()

    assert res is None
    assert skippedTrans == ""


def test_anlaysis_of_harmful_CT_SW_race_detects_race_correctly(
    katch, trace_1SW_1CT_harmful_CT_SW_race
):
    td = trace_1SW_1CT_harmful_CT_SW_race
    props = raceSafetyDict(td.safetyProp)
    transChecker = TransitionsChecker(katch, props, td.metadata)
    ta = TraceAnalyzer(transChecker, td.metadata)

    res = ta.analyze(td.trace)
    skippedTrans = transChecker.getSkippedRacesStr()

    assert res is not None
    assert res.raceType == RaceType.CT_SW
    assert res.elsMetadata == td.metadata
    assert skippedTrans == ""
    assert res.racingNodes == td.racingNodes


def test_analysis_of_harmful_CT_SW_race_detects_race_correctly2(
    katch, trace_1SW_1CT_harmful_CT_SW_race2
):
    td = trace_1SW_1CT_harmful_CT_SW_race2
    props = raceSafetyDict(td.safetyProp)
    transChecker = TransitionsChecker(katch, props, td.metadata)
    ta = TraceAnalyzer(transChecker, td.metadata)

    res = ta.analyze(td.trace)
    skippedTrans = transChecker.getSkippedRacesStr()

    assert res is not None
    assert res.raceType == RaceType.CT_SW
    assert res.elsMetadata == td.metadata
    assert res.racingNodes == td.racingNodes
    assert skippedTrans == ""


def test_analysis_of_unharmful_CT_SW_CT_race_detects_nothing(
    katch, trace_1SW_2CT_unharmful_CT_SW_CT_race
):
    td = trace_1SW_2CT_unharmful_CT_SW_CT_race
    props = raceSafetyDict(td.safetyProp)
    transChecker = TransitionsChecker(katch, props, td.metadata)
    ta = TraceAnalyzer(transChecker, td.metadata)

    res = ta.analyze(td.trace)
    skippedTrans = transChecker.getSkippedRacesStr()

    assert res is None
    assert skippedTrans == ""


def test_analysis_of_harmful_CT_SW_CT_race_detects_race_correctly(
    katch, trace_1SW_2CT_harmful_CT_SW_CT_race
):
    td = trace_1SW_2CT_harmful_CT_SW_CT_race
    props = raceSafetyDict(td.safetyProp)
    transChecker = TransitionsChecker(katch, props, td.metadata)
    ta = TraceAnalyzer(transChecker, td.metadata)

    res = ta.analyze(td.trace)
    skippedTrans = transChecker.getSkippedRacesStr()

    assert res is not None
    assert res.raceType == RaceType.CT_SW_CT
    assert res.elsMetadata == td.metadata
    assert res.racingNodes == td.racingNodes
    assert skippedTrans == ""


def test_analysis_of_harmful_CT_SW_CT_race_detects_race_correctly2(
    katch, trace_1SW_2CT_harmful_CT_SW_CT_race2
):
    td = trace_1SW_2CT_harmful_CT_SW_CT_race2
    props = raceSafetyDict(td.safetyProp)
    transChecker = TransitionsChecker(katch, props, td.metadata)
    ta = TraceAnalyzer(transChecker, td.metadata)

    res = ta.analyze(td.trace)
    skippedTrans = transChecker.getSkippedRacesStr()

    assert res is not None
    assert res.raceType == RaceType.CT_SW_CT
    assert res.elsMetadata == td.metadata
    assert res.racingNodes == td.racingNodes
    assert skippedTrans == ""


def test_analysis_skips_CT_SW_races_and_detects_harmful_CT_SW_CT_race_correctly(
    katch, trace_1SW_2CT_harmful_CT_SW_and_CT_SW_CT_race
):
    td = trace_1SW_2CT_harmful_CT_SW_and_CT_SW_CT_race
    props = raceSafetyDict(td.safetyProp)
    transChecker = TransitionsChecker(katch, props, td.metadata, [RaceType.CT_SW])
    ta = TraceAnalyzer(transChecker, td.metadata)

    res = ta.analyze(td.trace)
    skippedTrans = transChecker.getSkippedRacesStr()

    assert res is not None
    assert res.raceType == RaceType.CT_SW_CT
    assert res.elsMetadata == td.metadata
    assert res.racingNodes == td.racingNodes[2:]
    assert skippedTrans == f"{RaceType.CT_SW}: 1 times"


def test_analysis_skips_SW_SW_race_correctly(katch, trace_2SW_2CT_SW_SW_race):
    td = trace_2SW_2CT_SW_SW_race
    props = raceSafetyDict(td.safetyProp)
    transChecker = TransitionsChecker(katch, props, td.metadata)
    ta = TraceAnalyzer(transChecker, td.metadata)

    res = ta.analyze(td.trace)
    skippedTrans = transChecker.getSkippedRacesStr("\t")

    assert res is None
    assert skippedTrans == "\tSW-SW: 1 times"


def test_analysis_of_unharmful_CT_CT_SW_race_detects_nothing(
    katch, trace_2SW_2CT_unharmful_CT_CT_SW_race
):
    td = trace_2SW_2CT_unharmful_CT_CT_SW_race
    props = raceSafetyDict(td.safetyProp)
    transChecker = TransitionsChecker(katch, props, td.metadata)
    ta = TraceAnalyzer(transChecker, td.metadata)

    res = ta.analyze(td.trace)
    skippedTrans = transChecker.getSkippedRacesStr()

    assert res is None
    assert skippedTrans == ""


def test_analysis_of_harmful_CT_CT_SW_race_detects_race_correctly(
    katch, trace_2SW_2CT_harmful_CT_CT_SW_race
):
    td = trace_2SW_2CT_harmful_CT_CT_SW_race
    props = raceSafetyDict(td.safetyProp)
    transChecker = TransitionsChecker(katch, props, td.metadata)
    ta = TraceAnalyzer(transChecker, td.metadata)

    res = ta.analyze(td.trace)
    skippedTrans = transChecker.getSkippedRacesStr()

    assert res is not None
    assert res.raceType == RaceType.CT_CT_SW
    assert res.elsMetadata == td.metadata
    assert res.racingNodes == td.racingNodes
    assert skippedTrans == ""


def test_analysis_of_harmful_CT_CT_SW_race_detects_race_correctly2(
    katch, trace_2SW_2CT_harmful_CT_CT_SW_race2
):
    td = trace_2SW_2CT_harmful_CT_CT_SW_race2
    props = raceSafetyDict(td.safetyProp)
    transChecker = TransitionsChecker(katch, props, td.metadata)
    ta = TraceAnalyzer(transChecker, td.metadata)

    res = ta.analyze(td.trace)
    skippedTrans = transChecker.getSkippedRacesStr()

    assert res is not None
    assert res.raceType == RaceType.CT_CT_SW
    assert res.elsMetadata == td.metadata
    assert res.racingNodes == td.racingNodes
    assert skippedTrans == ""
