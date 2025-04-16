import os
import sys
import time
from test.util import DNKTestModel

from pydantic import ValidationError

from src.analyzer.traces_analyzer import TracesAnalyzer
from src.cli import CLIError, getCLIArgs
from src.errors import MaudeError
from src.KATch_comm import KATchComm
from src.model.dnk_maude_model import DNKMaudeModel
from src.otf.trace_generator import newTraceGenerator
from src.otf.tracer import Tracer, TracerConfig
from src.stats import StatsCollector, StatsEntry
from src.util import createDir, exportFile, getFileName, readFile, removeFile

PROJECT_DIR_PATH = os.path.dirname(os.path.realpath(__file__))
OUTPUT_DIR_PATH = os.path.join(PROJECT_DIR_PATH, "output")
MAUDE_FILES_DIR_PATH = os.path.join(PROJECT_DIR_PATH, "src", "maude")
RUN_DIR_NAME = "run"
TRACES_FILE_NAME = "traces"
HARMFUL_TRACES_DIR_NAME = "harmful_traces"
HARMFUL_TRACES_RAW_DIR_NAME = "harmful_traces_raw"
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
            outputDirPath=runOutputDir,
            katchPath=args.katchPath,
            maudeFilesDirPath=MAUDE_FILES_DIR_PATH,
            threads=args.threads,
            verbose=args.verbose,
        )

        inputFileName = getFileName(args.inputFilePath)
        tracesFilePath = os.path.join(
            runOutputDir, f"{TRACES_FILE_NAME}_{inputFileName}.txt"
        )
        tracer = Tracer(config, newTraceGenerator(args.strategy))
        print("Generating traces...")
        generatedTraces = tracer.run(dnkModel, args.depth)

        exportFile(tracesFilePath, os.linesep.join([str(t) for t in generatedTraces]))

        stats = StatsCollector()
        stats.addEntries([StatsEntry("date", "Date", fmtTime)])
        stats.addEntries(args.getStats())
        stats.addEntries(dnkModel.getStats())
        stats.addEntries(tracer.getStats())

        print()
        print(stats.toPrettyStr())
        print()
        logRunStats(stats, TRACES_GEN_STATS_FILE_NAME)

        if not generatedTraces:
            removeFile(tracesFilePath)
            printAndExit(
                "Could not generate any traces for the given network and depth!"
            )

        print("Analyzing traces...")
        outputDirRaw = os.path.join(runOutputDir, HARMFUL_TRACES_RAW_DIR_NAME)
        outputDirDOT = os.path.join(runOutputDir, HARMFUL_TRACES_DIR_NAME)
        createDir(outputDirRaw)
        createDir(outputDirDOT)

        katchComm = KATchComm(args.katchPath, runOutputDir)
        ta = TracesAnalyzer(katchComm, outputDirRaw, outputDirDOT)
        ta.analyzeFile(generatedTraces, dnkModel.elTypeDict)

        stats.addEntries(katchComm.getStats())
        stats.addEntries(ta.getStats())
        stats.addEntries(
            [
                StatsEntry(
                    "totalExecTime",
                    "Total execution time",
                    tracer.getTotalExecTime() + ta.getTotalExecTime(),
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
