from typing import List

import pytest

from src.analyzer.harmful_trace import RaceType
from src.analyzer.transition_checker import TransitionsChecker
from src.model.dnk_maude_model import ElementMetadata, ElementType

_SW1_ID = 991
_SW2_ID = 992
_CT1_ID = 993
_CT2_ID = 994
_CT3_ID = 995


@pytest.fixture
def metadata2SW3CT() -> List[ElementMetadata]:
    return [
        ElementMetadata(_SW1_ID, ElementType.SW),
        ElementMetadata(_SW2_ID, ElementType.SW),
        ElementMetadata(_CT1_ID, ElementType.CT),
        ElementMetadata(_CT2_ID, ElementType.CT),
        ElementMetadata(_CT3_ID, ElementType.CT),
    ]


@pytest.fixture
def metadata2SW2CT() -> List[ElementMetadata]:
    return [
        ElementMetadata(_SW1_ID, ElementType.SW),
        ElementMetadata(_SW2_ID, ElementType.SW),
        ElementMetadata(_CT1_ID, ElementType.CT),
        ElementMetadata(_CT2_ID, ElementType.CT),
    ]


@pytest.fixture
def metadata1SW2CT() -> List[ElementMetadata]:
    return [
        ElementMetadata(_SW1_ID, ElementType.SW),
        ElementMetadata(_CT1_ID, ElementType.CT),
        ElementMetadata(_CT2_ID, ElementType.CT),
    ]


@pytest.fixture
def metadata1SW1CT() -> List[ElementMetadata]:
    return [
        ElementMetadata(_SW1_ID, ElementType.SW),
        ElementMetadata(_CT1_ID, ElementType.CT),
    ]


@pytest.fixture
def transChecker2SW2CT(katch, metadata2SW2CT) -> TransitionsChecker:
    return TransitionsChecker(katch, metadata2SW2CT)


@pytest.fixture
def transChecker2SW3CT(katch, metadata2SW3CT) -> TransitionsChecker:
    return TransitionsChecker(katch, metadata2SW3CT)


@pytest.fixture
def transChecker1SW2CT(katch, metadata1SW2CT) -> TransitionsChecker:
    return TransitionsChecker(katch, metadata1SW2CT)


@pytest.fixture
def transChecker1SW1CT(katch, metadata1SW1CT) -> TransitionsChecker:
    return TransitionsChecker(katch, metadata1SW1CT)


@pytest.fixture
def transCheckerAllSkipped(katch, metadata2SW2CT) -> TransitionsChecker:
    return TransitionsChecker(katch, metadata2SW2CT, [rt for rt in RaceType])


@pytest.fixture
def transChecker1SW2CTSkipCTSW(katch, metadata1SW2CT) -> TransitionsChecker:
    return TransitionsChecker(katch, metadata1SW2CT, [RaceType.CT_SW])
