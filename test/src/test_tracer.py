import os
import test.util as util
from dataclasses import dataclass
from typing import List

import networkx
import pygraphviz
import pytest

from src.tracer import Tracer, TracerConfig

TEST_OUTPUT_DIR_NAME = "tracer_test_output"
TEST_INPUT_DIR_PATH = os.path.join(util.TEST_DIR, "testfiles")
MAUDE_FILES_DIR_PATH = os.path.join(util.PROJECT_DIR, "maude")
EXPECTED_DOT_FILENAME = "expected.gv"
MAUDE_INPUT_FILENAME = "maude_input.maude"


def readInputFile(directory: str, fileName: str) -> str:
    with open(os.path.join(TEST_INPUT_DIR_PATH, directory, fileName), "r") as f:
        content = str(f.read())
    if not content:
        pytest.fail("Read empty test input file!")
    return content


@pytest.fixture
def tracer(tmp_path) -> Tracer:
    outputDir = tmp_path / TEST_OUTPUT_DIR_NAME
    outputDir.mkdir()

    config = TracerConfig(
        outputDirPath=str(outputDir),
        katchPath="",
        maudeFilesDirPath=MAUDE_FILES_DIR_PATH,
    )

    return Tracer(config)


@dataclass
class TracerTestData:
    id: str
    expectedFilesDirName: str
    switchesMaudeMap: str
    controllersMaudeMap: str
    depth: int
    allTraces: bool
    __test__ = False


class TestTracer:
    testDataList: List[TracerTestData] = [
        TracerTestData(
            id="[SUCCESS]: stateful firewall, multiple traces with incomparable VCs",
            expectedFilesDirName="tracer1",
            switchesMaudeMap="getRecPol(SW)",
            controllersMaudeMap="(0 |-> getRecPol(C), empty)",
            depth=10,
            allTraces=True,
        ),
        TracerTestData(
            id="[SUCCESS]: 1 switch - 2 controllers, multiple traces with incomparable VCs",
            expectedFilesDirName="tracer2",
            switchesMaudeMap="getRecPol(SW)",
            controllersMaudeMap="(0 |-> getRecPol(C1), 1 |-> getRecPol(C2))",
            depth=10,
            allTraces=True,
        ),
    ]

    @pytest.mark.parametrize(
        "testData",
        testDataList,
        ids=map(lambda x: x.id, testDataList),
    )
    def test(self, tracer, testData: TracerTestData):
        result = tracer.run(
            util.DNKTestModel(
                readInputFile(testData.expectedFilesDirName, MAUDE_INPUT_FILENAME),
                testData.switchesMaudeMap,
                testData.controllersMaudeMap,
            ),
            testData.depth,
            testData.allTraces,
        )

        t1 = networkx.nx_agraph.read_dot(
            os.path.join(
                TEST_INPUT_DIR_PATH,
                testData.expectedFilesDirName,
                EXPECTED_DOT_FILENAME,
            )
        )
        t2 = networkx.nx_agraph.from_agraph(pygraphviz.AGraph(result))
        util.assertEqualTrees(t1, t2)
