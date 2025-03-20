import optparse
import os
import sys
import time
from test.util import DNKTestModel
from typing import List, Tuple

from pydantic import ValidationError

from src.model.dnk_maude_model import DNKMaudeModel
from src.tracer import MaudeError, Tracer, TracerConfig, TracerStats
from src.util import createDir, getFileName, isExe, readFile

PROJECT_DIR_PATH = os.path.dirname(os.path.realpath(__file__))
OUTPUT_DIR_PATH = os.path.join(PROJECT_DIR_PATH, "output")
MAUDE_FILES_DIR_PATH = os.path.join(PROJECT_DIR_PATH, "src", "maude")
OUTPUT_FILE_NAME = "traces"
EXEC_STATS_FILE_NAME = "execution_stats"


def printAndExit(msg: str) -> None:
    print(msg)
    sys.exit()


def buildArgsParser() -> optparse.OptionParser:
    parser = optparse.OptionParser()
    parser.add_option(
        "-d",
        "--depth",
        type="int",
        dest="depth",
        default=5,
        help="Depth of search (default is 5)",
    )
    parser.add_option(
        "-g",
        "--debug",
        dest="debug",
        default=False,
        action="store_true",
        help="Passing this option enables the tool to accept specifically formated "
        + ".maude files containing DNK network models for testing or debugging",
    )
    return parser


def validateArgs(args: List[str], debugMode: bool) -> Tuple[str, str]:
    """Validates the command line arguments and returns the paths to the KATch
    executable and the input JSON file."""
    if len(args) < 2:
        printAndExit("Error: provide the arguments <path_to_katch> <input_file>.")

    if not os.path.exists(args[0]) or not isExe(args[0]):
        printAndExit("KATch tool could not be found in the given path!")

    fileExt = args[1].split(".")[-1]
    if (
        not os.path.isfile(args[1])
        or fileExt not in ["json", "maude"]
        or (fileExt == "maude" and not debugMode)
    ):
        printAndExit("Please provide a .json input file!")
    return args[0], args[1]


def getOutputFilePath(currTime: time.struct_time, inputFileName: str) -> str:
    currTimeStr = time.strftime("%Y_%m_%dT%H_%M_%S", currTime)
    return os.path.join(
        OUTPUT_DIR_PATH, f"{OUTPUT_FILE_NAME}_{currTimeStr}_{inputFileName}.txt"
    )


def logRunStats(
    currTime: time.struct_time,
    inputFileName: str,
    depth: int,
    stats: TracerStats,
    branchCountsStr: str,
) -> None:
    logFilePath = os.path.join(OUTPUT_DIR_PATH, f"{EXEC_STATS_FILE_NAME}.csv")

    statsVarNames: List[str] = [str(k) for k in vars(stats).keys()]  # type: ignore
    statsVarValues: List[str] = [str(v) for v in vars(stats).values()]  # type: ignore
    if not os.path.exists(logFilePath):
        with open(logFilePath, "w") as f:
            f.write(
                ",".join(
                    ["date", "input_file", "depth", "branchCounts"] + statsVarNames
                )
            )
            f.write(os.linesep)

    fmtTime = time.strftime("%Y-%m-%d;%H:%M:%S", currTime)
    with open(logFilePath, "a") as f:
        f.write(
            ",".join(
                [fmtTime, inputFileName, f"{depth}", branchCountsStr] + statsVarValues
            )
        )
        f.write(os.linesep)


def readDNKModelFromFile(filePath: str) -> DNKMaudeModel:
    fileExt = filePath.split(".")[-1]
    if fileExt == "maude":
        # Only for debugging purposes
        jsonStr = readFile(filePath)
        fileContent = readFile(filePath)
        fileContentLines = fileContent.split("\n")
        maudeStr = "\n".join(fileContentLines[:-3])
        switchCall = fileContentLines[-3]
        controllerMap = fileContentLines[-2]
        return DNKTestModel(
            maudeStr,
            switchCall,
            controllerMap,
        )

    if fileExt == "json":
        jsonStr = readFile(filePath)
        return DNKMaudeModel().fromJson(jsonStr)
    printAndExit("Unknown input file extension: {fileExt}!")
    return DNKMaudeModel()


def main() -> None:
    (options, args) = buildArgsParser().parse_args()
    katchPath, inputFilePath = validateArgs(args, options.debug)  # type: ignore

    createDir(OUTPUT_DIR_PATH)
    config = TracerConfig(
        outputDirPath=OUTPUT_DIR_PATH,
        katchPath=katchPath,
        maudeFilesDirPath=MAUDE_FILES_DIR_PATH,
        threads=10,  # TODO: make this an option for the CLI
    )

    try:
        dnkModel = readDNKModelFromFile(inputFilePath)

        currTime = time.localtime()
        inputFileName = getFileName(inputFilePath)
        tracesFilePath = getOutputFilePath(currTime, inputFileName)

        with open(tracesFilePath, "a") as file:
            tracer = Tracer(config, file)
            tracer.run(dnkModel, options.depth)  # type: ignore

        execStats = tracer.getStats()
        print(execStats)
        logRunStats(currTime, inputFileName, options.depth, execStats, dnkModel.getBranchCounts())  # type: ignore

        if execStats.collectedTraces == 0:
            if os.path.exists(tracesFilePath):
                os.remove(tracesFilePath)
            printAndExit(
                "Could not collect any traces for the given network and depth!"
            )

        print("Concurrent behavior detected!")
        print(f"Trace(s) written to: {tracesFilePath}.")

    except MaudeError as e:
        print(f"Error encountered while executing Maude:\n\t{e}")
    except ValidationError as e:
        print(f"Invalid JSON file!\n{e}")


if __name__ == "__main__":
    main()
