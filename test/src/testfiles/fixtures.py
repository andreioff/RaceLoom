import pytest

from src.KATch_comm import KATchComm
from src.util import DyNetKATSymbols as sym
from test.src.testfiles.util import KATCH_PATH


@pytest.fixture
def katch(tmp_path) -> KATchComm:
    outputDir = tmp_path / "katch_test_output"
    outputDir.mkdir()
    return KATchComm(KATCH_PATH, str(outputDir))


@pytest.fixture
def flowRule1():
    return (
        f"port {sym.EQUAL} 1 {sym.AND} dst {sym.EQUAL} 2 {sym.AND} port {sym.ASSIGN} 3"
    )


@pytest.fixture
def flowRule2():
    return (
        f"port {sym.EQUAL} 3 {sym.AND} dst {sym.EQUAL} 1 {sym.AND} port {sym.ASSIGN} 5"
    )


@pytest.fixture
def flowRule3():
    return f"field1 {sym.EQUAL} 50 {sym.AND} field2 {sym.EQUAL} 32 {sym.AND} field3 {sym.ASSIGN} 60"
