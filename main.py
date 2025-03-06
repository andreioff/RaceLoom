import optparse
import os
import sys
import time
from typing import List, Tuple

from pydantic import ValidationError

from src.model.dnk_maude_model import DNKMaudeModel
from src.tracer import MaudeError, Tracer, TracerConfig, TracerStats
from src.util import createDir, exportFile, getFileName, isExe, isJson, readFile

PROJECT_DIR_PATH = os.path.dirname(os.path.realpath(__file__))
OUTPUT_DIR_PATH = os.path.join(PROJECT_DIR_PATH, "output")
MAUDE_FILES_DIR_PATH = os.path.join(PROJECT_DIR_PATH, "src", "maude")
RESULT_FILE_NAME = "result"
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
        "--to-dot",
        dest="toDot",
        default=False,
        action="store_true",
        help="Passing this option converts the traces into DOT format",
    )
    return parser


def validateArgs(args: List[str]) -> Tuple[str, str]:
    """Validates the command line arguments and returns the paths to the KATch
    executable and the input JSON file."""
    if len(args) < 2:
        printAndExit("Error: provide the arguments <path_to_katch> <input_file>.")

    if not os.path.exists(args[0]) or not isExe(args[0]):
        printAndExit("KATch tool could not be found in the given path!")

    if not isJson(args[1]) or not os.path.isfile(args[1]):
        printAndExit("Please provide a .json input file!")
    return args[0], args[1]


def writeTracesToFile(
    currTime: time.struct_time, fileContent: str, inputFileName: str, fileExt: str
) -> None:
    currTimeStr = time.strftime("%Y_%m_%dT%H_%M_%S", currTime)
    exportFilePath = os.path.join(
        OUTPUT_DIR_PATH, f"{RESULT_FILE_NAME}_{currTimeStr}_{inputFileName}.{fileExt}"
    )
    exportFile(exportFilePath, fileContent)
    print(f"Trace(s) written to: {exportFilePath}.")


def logRunStats(
    currTime: time.struct_time, inputFileName: str, depth: int, stats: TracerStats
) -> None:
    logFilePath = os.path.join(OUTPUT_DIR_PATH, f"{EXEC_STATS_FILE_NAME}.csv")

    statsVarNames: List[str] = [str(k) for k in vars(stats).keys()]  # type: ignore
    statsVarValues: List[str] = [str(v) for v in vars(stats).values()]  # type: ignore
    if not os.path.exists(logFilePath):
        with open(logFilePath, "w") as f:
            f.write(",".join(["date", "input_file", "depth"] + statsVarNames))
            f.write(os.linesep)

    fmtTime = time.strftime("%Y-%m-%d;%H:%M:%S", currTime)
    with open(logFilePath, "a") as f:
        f.write(",".join([fmtTime, inputFileName, f"{depth}"] + statsVarValues))
        f.write(os.linesep)


def main() -> None:
    (options, args) = buildArgsParser().parse_args()
    katchPath, inputFilePath = validateArgs(args)

    createDir(OUTPUT_DIR_PATH)
    config = TracerConfig(
        outputDirPath=OUTPUT_DIR_PATH,
        katchPath=katchPath,
        maudeFilesDirPath=MAUDE_FILES_DIR_PATH,
        toDot=options.toDot,  # type: ignore
    )

    try:
        jsonStr = readFile(inputFilePath)
        tracer = Tracer(config)

        traceTreeStr, isEmpty = tracer.run(
            DNKMaudeModel().fromJson(jsonStr), options.depth  # type: ignore
        )
        execStats = tracer.getExecTimeStats()
        print(execStats)

        currTime = time.localtime()
        inputFileName = getFileName(inputFilePath)
        logRunStats(currTime, inputFileName, options.depth, execStats)  # type: ignore

        if isEmpty:
            printAndExit(
                "Could not find any concurrent behavior "
                + "for the given network and depth!"
            )

        fileExt = "maude"
        if options.toDot:  # type: ignore
            fileExt = "gv"

        print("Concurrent behavior detected!")
        writeTracesToFile(currTime, traceTreeStr, inputFileName, fileExt)

    except MaudeError as e:
        print(f"Error encountered while executing Maude:\n\t{e}")
    except ValidationError as e:
        print(f"Invalid JSON file!\n{e}")


if __name__ == "__main__":
    main()
