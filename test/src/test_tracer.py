import os
import test.util as util
from typing import Callable

import pytest

from src.tracer import Tracer, TracerConfig

TEST_OUTPUT_DIR_NAME = "tracer_test_output"
TEST_INPUT_DIR_PATH = os.path.join(util.TEST_DIR, "testfiles")
MAUDE_FILES_DIR_PATH = os.path.join(util.PROJECT_DIR, "maude")


def readInputFile(fileName: str) -> str:
    with open(os.path.join(TEST_INPUT_DIR_PATH, fileName), "r") as f:
        content = str(f.read())
    if not content:
        pytest.fail("Read empty test input file!")
    return content


@pytest.fixture
def tracer(tmp_path) -> Callable[[int, bool], Tracer]:
    outputDir = tmp_path / TEST_OUTPUT_DIR_NAME
    outputDir.mkdir()

    config = TracerConfig(
        outputDirPath=str(outputDir),
        katchPath="",
        maudeFilesDirPath=MAUDE_FILES_DIR_PATH,
    )

    return Tracer(config)


def test_run_stateful_firewall_multiple_traces_with_incomparable_VCs_success(tracer):
    result = tracer.run(
        util.DNKTestModel(
            readInputFile("maude_input_1.maude"),
            "getRecPol(SW)",
            "(0 |-> getRecPol(C), empty)",
        ),
        10,
        True,
    )

    expected = readInputFile("dot_output_1.gv")
    assert result == expected
