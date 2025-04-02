import os
import sys
import time
from test.util import DNKTestModel

from pydantic import ValidationError

from src.model.dnk_maude_model import DNKMaudeModel
from src.tracer import MaudeError, Tracer, TracerConfig
from src.util import createDir, getFileName, readFile, removeFile
from src.stats import StatsCollector, StatsEntry
from src.cli import getCLIArgs, CLIError

PROJECT_DIR_PATH = os.path.dirname(os.path.realpath(__file__))
OUTPUT_DIR_PATH = os.path.join(PROJECT_DIR_PATH, "output")
MAUDE_FILES_DIR_PATH = os.path.join(PROJECT_DIR_PATH, "src", "maude")
OUTPUT_FILE_NAME = "traces"
EXEC_STATS_FILE_NAME = "execution_stats"


def printAndExit(msg: str) -> None:
    print(msg)
    sys.exit()


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
    fileContent = readFile(filePath)
    if fileExt == "maude":
        return DNKTestModel.fromDebugMaudeFile(fileContent)
    if fileExt == "json":
        return DNKMaudeModel().fromJson(fileContent)
    printAndExit(f"Unknown input file extension: '{fileExt}'!")
    return DNKMaudeModel()


def main() -> None:
    try:
        args = getCLIArgs()

        createDir(OUTPUT_DIR_PATH)
        config = TracerConfig(
            outputDirPath=OUTPUT_DIR_PATH,
            katchPath=args.katchPath,
            maudeFilesDirPath=MAUDE_FILES_DIR_PATH,
            threads=args.threads,
            verbose=args.verbose,
        )

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

    except CLIError as e:
        printAndExit(e.__str__())
    except MaudeError as e:
        print(f"Error encountered while executing Maude:\n\t{e}")
    except ValidationError as e:
        print(f"Invalid JSON file!\n{e}")


if __name__ == "__main__":
    main()
