from typing import List

import pytest

from src.analyzer.trace_analyzer import TransitionsChecker
from src.model.dnk_maude_model import ElementMetadata, ElementType

_SW1_ID = 991
_SW2_ID = 992
_CT1_ID = 993
_CT2_ID = 994


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
def transChecker1SW2CT(katch, metadata1SW2CT) -> TransitionsChecker:
    return TransitionsChecker(katch, metadata1SW2CT)


@pytest.fixture
def transChecker1SW1CT(katch, metadata1SW1CT) -> TransitionsChecker:
    return TransitionsChecker(katch, metadata1SW1CT)
