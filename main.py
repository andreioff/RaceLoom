import argparse
import os
import sys
import time
from dataclasses import dataclass
from test.util import DNKTestModel

from pydantic import ValidationError

from src.model.dnk_maude_model import DNKMaudeModel
from src.tracer import MaudeError, Tracer, TracerConfig
from src.util import createDir, getFileName, isExe, readFile, removeFile
from src.stats import StatsCollector, StatsEntry

PROJECT_DIR_PATH = os.path.dirname(os.path.realpath(__file__))
OUTPUT_DIR_PATH = os.path.join(PROJECT_DIR_PATH, "output")
MAUDE_FILES_DIR_PATH = os.path.join(PROJECT_DIR_PATH, "src", "maude")
OUTPUT_FILE_NAME = "traces"
EXEC_STATS_FILE_NAME = "execution_stats"


def printAndExit(msg: str) -> None:
    print(msg)
    sys.exit()


@dataclass
class CLIArguments:
    katchPath: str
    inputFilePath: str
    depth: int
    threads: int
    debug: bool
    verbose: bool


def buildArgsParser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser()
    parser.add_argument("katchPath")
    parser.add_argument("inputFilePath")
    parser.add_argument(
        "-d",
        "--depth",
        type=int,
        dest="depth",
        default=5,
        help="Depth of search (default is 5)",
    )
    parser.add_argument(
        "-t",
        "--threads",
        type=int,
        dest="threads",
        default=1,
        help="Number of threads to use when generating traces",
    )
    parser.add_argument(
        "-g",
        "--debug",
        dest="debug",
        default=False,
        action="store_true",
        help="Passing this option enables the tool to accept specifically formated "
        + ".maude files containing DNK network models for testing or debugging",
    )
    parser.add_argument(
        "-v",
        "--verbose",
        dest="verbose",
        default=False,
        action="store_true",
        help="Print log messages during execution",
    )
    return parser


def validateArgs(args: CLIArguments) -> None:
    """Validates the command line arguments and returns the paths to the KATch
    executable and the input JSON file."""
    if not args.katchPath or not args.inputFilePath:
        printAndExit(
            "Error: provide the arguments <path_to_katch> <input_file>.")

    if not os.path.exists(args.katchPath) or not isExe(args.katchPath):
        printAndExit("KATch tool could not be found in the given path!")

    fileExt = args.inputFilePath.split(".")[-1]
    if (
        not os.path.isfile(args.inputFilePath)
        or fileExt not in ["json", "maude"]
        or (fileExt == "maude" and not args.debug)
    ):
        printAndExit("Please provide a .json input file!")
    if args.depth < 0:
        printAndExit("Depth cannot be negative")
    if args.threads < 1:
        printAndExit("Number of threads must be a positive integer")


def getOutputFilePath(currTime: time.struct_time, inputFileName: str) -> str:
    currTimeStr = time.strftime("%Y_%m_%dT%H_%M_%S", currTime)
    return os.path.join(
        OUTPUT_DIR_PATH, f"{OUTPUT_FILE_NAME}_{
            currTimeStr}_{inputFileName}.txt"
    )


def logRunStats(stats: StatsCollector) -> None:
    logFilePath = os.path.join(OUTPUT_DIR_PATH, f"{EXEC_STATS_FILE_NAME}.csv")
    sep = ","
    if not os.path.exists(logFilePath):
        with open(logFilePath, "w") as f:
            f.write(stats.keys(sep))
            f.write(os.linesep)

    with open(logFilePath, "a") as f:
        f.write(stats.values(sep))
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
    args = CLIArguments(**vars(buildArgsParser().parse_args()))  # type: ignore
    validateArgs(args)

    createDir(OUTPUT_DIR_PATH)
    config = TracerConfig(
        outputDirPath=OUTPUT_DIR_PATH,
        katchPath=args.katchPath,
        maudeFilesDirPath=MAUDE_FILES_DIR_PATH,
        threads=args.threads,
        verbose=args.verbose,
    )

    try:
        dnkModel = readDNKModelFromFile(args.inputFilePath)

        currTime = time.localtime()
        fmtTime = time.strftime("%Y-%m-%d;%H:%M:%S", currTime)
        inputFileName = getFileName(args.inputFilePath)
        tracesFilePath = getOutputFilePath(currTime, inputFileName)

        with open(tracesFilePath, "a") as file:
            tracer = Tracer(config, file)
            collectedTraces = tracer.run(dnkModel, args.depth)

        stats = StatsCollector()
        stats.addEntries([
            StatsEntry("date", "Date", fmtTime),
            StatsEntry("inputFile", "Input file",
                       os.path.basename(args.inputFilePath)),
            StatsEntry("depth", "Depth", args.depth),
            StatsEntry("modelBranchCounts",
                       "Network model branches", dnkModel.getBranchCounts()),
        ])
        stats.addEntries(tracer.getStats())

        print()
        print(stats.toPrettyStr())
        print()
        logRunStats(stats)

        if collectedTraces == 0:
            removeFile(tracesFilePath)
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
