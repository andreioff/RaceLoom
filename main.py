import os
import sys
import time

from pydantic import ValidationError

from src.cli import CLIError, getCLIArgs
from src.errors import MaudeError
from src.model.dnk_maude_model import DNKMaudeModel
from src.stats import StatsCollector, StatsEntry
from src.tracer import Tracer
from src.tracer_config import TracerConfig
from src.util import createDir, getFileName, readFile
from test.src.test_utils.util import DNKTestModel

PROJECT_DIR_PATH = os.path.dirname(os.path.realpath(__file__))
OUTPUT_DIR_PATH = os.path.join(PROJECT_DIR_PATH, "output")
MAUDE_FILES_DIR_PATH = os.path.join(PROJECT_DIR_PATH, "src", "maude")
RUN_DIR_NAME = "run"

TRACES_GEN_STATS_FILE_NAME = "trace_generation_stats"
STATS_FILE_NAME = "final_stats"


def printAndExit(msg: str) -> None:
    print(msg)
    sys.exit()


def createRunOutputDir(currTime: time.struct_time) -> str:
    createDir(OUTPUT_DIR_PATH)
    currTimeStr = time.strftime("%Y_%m_%dT%H_%M_%S", currTime)
    dirPath = os.path.join(
        OUTPUT_DIR_PATH,
        f"{RUN_DIR_NAME}_{currTimeStr}",
    )
    createDir(dirPath)
    return dirPath


def logRunStats(stats: StatsCollector, fileName: str) -> None:
    logFilePath = os.path.join(OUTPUT_DIR_PATH, f"{fileName}.csv")
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
        return DNKMaudeModel.fromJson(fileContent)
    printAndExit(f"Unknown input file extension: '{fileExt}'!")
    return DNKMaudeModel()


def main() -> None:
    try:
        args = getCLIArgs()
        dnkModel = readDNKModelFromFile(args.inputFilePath)

        currTime = time.localtime()
        fmtTime = time.strftime("%Y-%m-%d;%H:%M:%S", currTime)
        runOutputDir = createRunOutputDir(currTime)

        config = TracerConfig(
            runOutputDir,
            args.katchPath,
            MAUDE_FILES_DIR_PATH,
            args.threads,
            args.verbose,
            getFileName(args.inputFilePath),
        )

        tracer = Tracer(config, args.strategy, dnkModel)
        print("Generating traces...")
        ok = tracer.generateTraces(args.depth)

        stats = StatsCollector()
        stats.addEntries([StatsEntry("date", "Date", fmtTime)])
        stats.addEntries(args.getStats())
        stats.addEntries(dnkModel.getStats())
        stats.addEntries(tracer.getTraceGenerationStats())

        if not ok:
            printAndExit(
                "Could not generate any traces for the given network and depth!"
            )

        print()
        print(stats.toPrettyStr())
        print()
        logRunStats(stats, TRACES_GEN_STATS_FILE_NAME)

        print("Analyzing traces...")
        tracer.analyzeTraces()

        stats.addEntries(tracer.getTraceAnalysisStats())
        stats.addEntries(
            [
                StatsEntry(
                    "totalExecTime",
                    "Total execution time",
                    tracer.getTotalExecTime(),
                )
            ]
        )

        print()
        print("========== Final Stats ==========")
        print(stats.toPrettyStr())
        print("=================================")
        logRunStats(stats, STATS_FILE_NAME)
        print(f"Output written to: {runOutputDir}")

    except CLIError as e:
        printAndExit(e.__str__())
    except MaudeError as e:
        print(f"Error encountered while executing Maude:\n\t{e}")
    except ValidationError as e:
        print(f"Invalid JSON file!\n{e}")


if __name__ == "__main__":
    main()
