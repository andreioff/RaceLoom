from test.src.analyzer.test_utils.util import (Metadata, SafetyPropertyData,
                                               TraceBuilder, TraceData)
from typing import List

import pytest

from src.analyzer.harmful_trace import RacingNode
from src.json_safety_property import SafetyProperty
from src.KATch_comm import _SAFETY_PROPERTY_PLACEHOLDER_NAME as SP_PLACEHOLDER
from src.KATch_comm import NKPL_EQUIV, NKPL_FALSE
from src.model.dnk_maude_model import ElementMetadata
from src.util import DyNetKATSymbols as sym


@pytest.fixture
def metadata2SW3CT() -> List[ElementMetadata]:
    return (
        Metadata()
        .addBigSw([["ch1", "ch2"], ["ch3", "ch4"]])
        .addBigSw([["ch1", "ch2"], ["ch3", "ch4"]])
        .addCt()
        .addCt()
        .addCt()
    )


@pytest.fixture
def metadata2SW2CT() -> List[ElementMetadata]:
    return (
        Metadata()
        .addBigSw([["ch1", "ch2"], ["ch3", "ch4"]])
        .addBigSw([["ch1", "ch2"], ["ch3", "ch4"]])
        .addCt()
        .addCt()
    )


@pytest.fixture
def metadata1SW2CT() -> List[ElementMetadata]:
    return Metadata().addBigSw([["ch1", "ch2"], ["ch3", "ch4"]]).addCt().addCt()


@pytest.fixture
def metadata1SW1CT() -> List[ElementMetadata]:
    return Metadata().addBigSw([["ch1", "ch2"], ["ch3", "ch4"]]).addCt()


@pytest.fixture
def safetyProp1() -> SafetyPropertyData:
    return SafetyPropertyData(
        f"(port {sym.EQUAL} 1 {sym.OR} port {sym.EQUAL} 2) "
        + f"{sym.AND} {SP_PLACEHOLDER} {sym.AND} "
        + f"(port {sym.EQUAL} 5 {sym.OR} port {sym.EQUAL} 6) "
        + f"{NKPL_EQUIV} {NKPL_FALSE}",
        passingFlowRules=[
            f"port {sym.EQUAL} 1 {sym.AND} port {sym.ASSIGN} 7",
            f"port {sym.EQUAL} 4 {sym.AND} port {sym.ASSIGN} 5",
            f"port {sym.EQUAL} 2 {sym.AND} port {sym.ASSIGN} 3",
            f"port {sym.EQUAL} 0 {sym.AND} port {sym.ASSIGN} 9",
        ],
        failingFlowRules=[
            f"port {sym.EQUAL} 1 {sym.AND} port {sym.ASSIGN} 5",
            f"port {sym.EQUAL} 2 {sym.AND} port {sym.ASSIGN} 6",
            f"port {sym.EQUAL} 1 {sym.AND} port {sym.ASSIGN} 6",
            f"port {sym.EQUAL} 2 {sym.AND} port {sym.ASSIGN} 5",
        ],
    )


@pytest.fixture
def trace_1SW_1CT_unharmful_CT_SW_race(metadata1SW1CT, safetyProp1) -> TraceData:
    SW1, CT1 = 0, 1
    frs = safetyProp1.passingFlowRules
    trace = (
        TraceBuilder(metadata1SW1CT)
        .addStartNode()
        .rcfgSw(frs[0], CT1, SW1, (0, 0))
        .forward(frs[0], SW1)  # racing
        .rcfgSw(frs[1], CT1, SW1, (0, 1))  # racing
        .forward(frs[1], SW1)
        .build()
    )
    return TraceData(metadata1SW1CT.elements, trace, safetyProp1.prop, [])


@pytest.fixture
def trace_1SW_1CT_harmful_CT_SW_race(metadata1SW1CT, safetyProp1) -> TraceData:
    SW1, CT1 = 0, 1
    inSW1 = 0
    frs = safetyProp1.passingFlowRules
    okFr, notOkFr = frs[0], safetyProp1.failingFlowRules[0]
    trace = (
        TraceBuilder(metadata1SW1CT)
        # no start node on purpose
        .forward(okFr, SW1)  # racing
        .rcfgSw(notOkFr, CT1, SW1, (inSW1, 1))  # racing
        .forward(frs[1], SW1)
        .rcfgSw(frs[2], CT1, SW1, (inSW1, 0))
        .forward(frs[1], SW1)
        .build()
    )
    expPolicy2 = metadata1SW1CT.buildBigSwPolicy(SW1, (inSW1, notOkFr))
    return TraceData(
        metadata1SW1CT.elements,
        trace,
        safetyProp1.prop,
        [RacingNode(0, SW1, okFr), RacingNode(1, CT1, expPolicy2)],
    )


@pytest.fixture
def trace_1SW_1CT_harmful_CT_SW_race2(metadata1SW1CT, safetyProp1) -> TraceData:
    SW1, CT1 = 0, 1
    inSW1, inSW2 = 0, 1
    frs = safetyProp1.passingFlowRules
    okFr, notOkFr = frs[3], safetyProp1.failingFlowRules[2]
    trace = (
        TraceBuilder(metadata1SW1CT)
        .addStartNode()
        .rcfgSw(frs[0], CT1, SW1, (inSW2, 0))
        .forward(notOkFr, SW1)  # racing
        .rcfgSw(okFr, CT1, SW1, (inSW2, 1))  # racing
        .forward(frs[1], SW1)
        .rcfgSw(frs[2], CT1, SW1, (inSW1, 0))
        .build()
    )
    expPolicy2 = metadata1SW1CT.buildBigSwPolicy(SW1, (inSW2, okFr))
    return TraceData(
        metadata1SW1CT.elements,
        trace,
        safetyProp1.prop,
        [RacingNode(2, SW1, notOkFr), RacingNode(3, CT1, expPolicy2)],
    )


@pytest.fixture
def trace_1SW_2CT_no_race(metadata1SW2CT, safetyProp1) -> TraceData:
    SW1, CT1, CT2 = 0, 1, 2
    # all transition policies are not valid KATch input to ensure KATch is not
    # run at all when analyzing the trace
    trace = (
        TraceBuilder(metadata1SW2CT)
        .addStartNode()
        .rcfgSw("policy1", CT1, SW1, (0, 0))
        .forward("policy1", SW1)
        .rcfgCt("help", SW1, CT1, "help1")
        .rcfgCt("help", CT1, CT2, "help2")
        .rcfgSw("policy2", CT2, SW1, (1, 0))
        .forward("policy2", SW1)
        .build()
    )
    return TraceData(metadata1SW2CT.elements, trace, safetyProp1.prop, [])


@pytest.fixture
def trace_1SW_2CT_unharmful_CT_SW_CT_race(metadata1SW2CT, safetyProp1) -> TraceData:
    SW1, CT1, CT2 = 0, 1, 2
    inSW2 = 1
    frs = safetyProp1.passingFlowRules
    trace = (
        TraceBuilder(metadata1SW2CT)
        .addStartNode()
        .rcfgSw(frs[1], CT1, SW1, (inSW2, 0))
        .rcfgSw(frs[0], CT1, SW1, (inSW2, 1))
        .rcfgSw(frs[2], CT1, SW1, (inSW2, 1))  # racing
        .rcfgSw(frs[3], CT2, SW1, (inSW2, 0))  # racing
        .build()
    )
    return TraceData(metadata1SW2CT.elements, trace, safetyProp1.prop, [])


@pytest.fixture
def trace_1SW_2CT_harmful_CT_SW_CT_race(metadata1SW2CT, safetyProp1) -> TraceData:
    SW1, CT1, CT2 = 0, 1, 2
    inSW1 = 0
    frs = safetyProp1.passingFlowRules
    okFr, notOkFr = frs[1], safetyProp1.failingFlowRules[3]
    trace = (
        TraceBuilder(metadata1SW2CT)
        # no start node on purpose
        .rcfgSw(notOkFr, CT1, SW1, (inSW1, 0))  # racing
        .rcfgSw(okFr, CT2, SW1, (inSW1, 1))  # racing
        .forward(frs[2], SW1)
        .forward(frs[2], SW1)
        .build()
    )
    expPolicy1 = metadata1SW2CT.buildBigSwPolicy(SW1, (inSW1, notOkFr))
    expPolicy2 = metadata1SW2CT.buildBigSwPolicy(SW1, (inSW1, okFr))
    return TraceData(
        metadata1SW2CT.elements,
        trace,
        safetyProp1.prop,
        [RacingNode(0, CT1, expPolicy1), RacingNode(1, CT2, expPolicy2)],
    )


@pytest.fixture
def trace_1SW_2CT_harmful_CT_SW_CT_race2(metadata1SW2CT, safetyProp1) -> TraceData:
    SW1, CT1, CT2 = 0, 1, 2
    inSW1, inSW2 = 0, 1
    frs = safetyProp1.passingFlowRules
    okFr, notOkFr = frs[1], safetyProp1.failingFlowRules[3]
    trace = (
        TraceBuilder(metadata1SW2CT)
        .addStartNode()
        .rcfgSw(frs[0], CT2, SW1, (inSW1, 0))
        .rcfgSw(okFr, CT2, SW1, (inSW1, 1))  # racing
        .rcfgSw(notOkFr, CT1, SW1, (inSW2, 0))  # racing
        .forward(frs[2], SW1)
        .build()
    )
    expPolicy1 = metadata1SW2CT.buildBigSwPolicy(SW1, (inSW1, okFr))
    expPolicy2 = metadata1SW2CT.buildBigSwPolicy(SW1, (inSW1, okFr), (inSW2, notOkFr))
    return TraceData(
        metadata1SW2CT.elements,
        trace,
        safetyProp1.prop,
        [RacingNode(2, CT2, expPolicy1), RacingNode(3, CT1, expPolicy2)],
    )


@pytest.fixture
def trace_1SW_2CT_harmful_CT_SW_and_CT_SW_CT_race(
    metadata1SW2CT, safetyProp1
) -> TraceData:
    SW1, CT1, CT2 = 0, 1, 2
    inSW1, inSW2 = 0, 1
    okFr1, okFr2 = safetyProp1.passingFlowRules[1], safetyProp1.passingFlowRules[3]
    notOkFr = safetyProp1.failingFlowRules[3]
    trace = (
        TraceBuilder(metadata1SW2CT)
        .addStartNode()
        .forward(notOkFr, SW1)  # racing with next rcfg
        .rcfgSw(okFr1, CT1, SW1, (inSW2, 0))
        .rcfgSw(okFr2, CT1, SW1, (inSW1, 1))  # racing
        .rcfgSw(notOkFr, CT2, SW1, (inSW1, 0))  # racing
        .forward(okFr1, SW1)
        .build()
    )

    expPolicy2 = metadata1SW2CT.buildBigSwPolicy(SW1, (inSW2, okFr1))
    expPolicy3 = metadata1SW2CT.buildBigSwPolicy(SW1, (inSW2, okFr1), (inSW1, okFr2))
    expPolicy4 = metadata1SW2CT.buildBigSwPolicy(SW1, (inSW2, okFr1), (inSW1, notOkFr))
    return TraceData(
        metadata1SW2CT.elements,
        trace,
        safetyProp1.prop,
        [
            RacingNode(1, SW1, notOkFr),
            RacingNode(2, CT1, expPolicy2),
            RacingNode(3, CT1, expPolicy3),
            RacingNode(4, CT2, expPolicy4),
        ],
    )


@pytest.fixture
def trace_2SW_2CT_SW_SW_race(metadata2SW2CT, safetyProp1) -> TraceData:
    SW1, SW2, CT1, CT2 = 0, 1, 2, 3
    inSW1, inSW2 = 0, 1
    frs = safetyProp1.passingFlowRules
    trace = (
        TraceBuilder(metadata2SW2CT)
        .addStartNode()
        .rcfgSw(frs[0], CT1, SW1, (inSW1, 0))
        .rcfgSw(frs[1], CT2, SW2, (inSW2, 1))
        .forward(frs[1], SW2)  # racing
        .forward(frs[0], SW1)  # racing
        .build()
    )
    return TraceData(metadata2SW2CT.elements, trace, safetyProp1.prop, [])


@pytest.fixture
def trace_2SW_2CT_unharmful_CT_CT_SW_race(metadata2SW2CT, safetyProp1) -> TraceData:
    SW1, SW2, CT1, CT2 = 0, 1, 2, 3
    inSW1, inSW2 = 0, 1
    frs = safetyProp1.passingFlowRules
    trace = (
        TraceBuilder(metadata2SW2CT)
        .addStartNode()
        .rcfgSw(frs[0], CT1, SW1, (inSW1, 0))
        .rcfgSw(frs[1], CT2, SW2, (inSW2, 1))
        .rcfgSw(frs[2], CT1, SW1, (inSW2, 0))  # racing
        .rcfgCt(frs[3], CT2, CT1, "upCT")  # racing
        .forward(frs[1], SW2)
        .build()
    )
    return TraceData(metadata2SW2CT.elements, trace, safetyProp1.prop, [])


@pytest.fixture
def trace_2SW_2CT_harmful_CT_CT_SW_race(metadata2SW2CT, safetyProp1) -> TraceData:
    SW1, SW2, CT1, CT2 = 0, 1, 2, 3
    inSW1, inSW2 = 0, 1
    frs = safetyProp1.passingFlowRules
    okFr, notOkFr = frs[1], safetyProp1.failingFlowRules[3]
    trace = (
        TraceBuilder(metadata2SW2CT)
        # no start node on purpose
        .rcfgSw(notOkFr, CT2, SW1, (inSW1, 0))  # racing
        .rcfgCt(okFr, CT1, CT2, "upCt")  # racing
        .rcfgSw(frs[0], CT2, SW2, (inSW2, 0))
        .forward(frs[0], SW2)
        .forward(frs[3], SW1)
        .build()
    )
    expPolicy1 = metadata2SW2CT.buildBigSwPolicy(SW1, (inSW1, notOkFr))
    expPolicy2 = metadata2SW2CT.buildBigSwPolicy(SW1, (inSW1, okFr))
    return TraceData(
        metadata2SW2CT.elements,
        trace,
        safetyProp1.prop,
        [RacingNode(0, CT2, expPolicy1), RacingNode(1, CT1, expPolicy2)],
    )


@pytest.fixture
def trace_2SW_2CT_harmful_CT_CT_SW_race2(metadata2SW2CT, safetyProp1) -> TraceData:
    SW1, SW2, CT1, CT2 = 0, 1, 2, 3
    inSW1, inSW2 = 0, 1
    frs = safetyProp1.passingFlowRules
    okFr, notOkFr = frs[1], safetyProp1.failingFlowRules[3]
    trace = (
        TraceBuilder(metadata2SW2CT)
        .addStartNode()
        .rcfgSw(frs[0], CT1, SW1, (inSW1, 0))
        .rcfgSw(frs[1], CT2, SW2, (inSW2, 1))
        .rcfgSw(okFr, CT1, SW1, (inSW2, 0))  # racing
        .forward(frs[2], SW1)
        .rcfgCt(notOkFr, CT2, CT1, "upCT")  # racing
        .rcfgSw(notOkFr, CT1, SW2, (inSW1, 0))
        .build()
    )
    expPolicy1 = metadata2SW2CT.buildBigSwPolicy(SW1, (inSW1, frs[0]), (inSW2, okFr))
    expPolicy2 = metadata2SW2CT.buildBigSwPolicy(SW1, (inSW1, frs[0]), (inSW2, notOkFr))
    return TraceData(
        metadata2SW2CT.elements,
        trace,
        safetyProp1.prop,
        [RacingNode(3, CT1, expPolicy1), RacingNode(5, CT2, expPolicy2)],
    )
