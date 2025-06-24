from typing import Callable, List

import pytest

from src.model.dnk_maude_model import ElementMetadata, ElementType


@pytest.fixture
def metadataFactory() -> Callable[[int, int], List[ElementMetadata]]:
    def _metadata(numSw: int, numCt: int) -> List[ElementMetadata]:
        elId = 0
        m: List[ElementMetadata] = []
        for _i in range(numSw):
            elId += 1
            m.append(ElementMetadata(elId, ElementType.SW))
        for _i in range(numCt):
            elId += 1
            m.append(ElementMetadata(elId, ElementType.CT))
        return m

    return _metadata
