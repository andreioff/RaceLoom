from test.src.test_utils.util import KATCH_PATH

import pytest

from src.KATch_comm import KATchComm


@pytest.fixture
def katch(tmp_path) -> KATchComm:
    outputDir = tmp_path / "katch_test_output"
    outputDir.mkdir()
    return KATchComm(KATCH_PATH, str(outputDir))
