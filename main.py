import optparse
import os
import string
import sys

from pydantic import ValidationError

from src.model.dnk_maude_model import DNKMaudeModel
from src.tracer import MaudeError, Tracer, TracerConfig
from src.util import createDir, exportFile, isExe, isJson, readFile

PROJECT_DIR_PATH = os.path.dirname(os.path.realpath(__file__))
OUTPUT_DIR_PATH = os.path.join(PROJECT_DIR_PATH, "output")
MAUDE_FILES_DIR_PATH = os.path.join(PROJECT_DIR_PATH, "src", "maude")
RESULT_FILE_NAME = "result"


def main() -> None:
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
        "-a",
        "--all-traces",
        dest="allTraces",
        default=False,
        action="store_true",
        help="Passing this option instructs the tool to extract \
                all traces that lead to concurrent behavior \
                instead of only the first one (impacts performance)",
    )

    (options, args) = parser.parse_args()

    if len(args) < 2:
        print("Error: provide the arguments <path_to_katch> <input_file>.")
        sys.exit()

    if not os.path.exists(args[0]) or not isExe(args[0]):
        print("KATch tool could not be found in the given path!")
        sys.exit()

    if not isJson(args[1]) or not os.path.isfile(args[1]):
        print("Please provide a .json input file!")
        sys.exit()

    createDir(OUTPUT_DIR_PATH)
    config = TracerConfig(
        outputDirPath=OUTPUT_DIR_PATH,
        katchPath=args[0],
        maudeFilesDirPath=MAUDE_FILES_DIR_PATH,
    )

    try:
        jsonStr = readFile(args[1])

        tracer = Tracer(config)

        dotTrace = tracer.run(
            DNKMaudeModel().fromJson(jsonStr), options.depth, options.allTraces  # type: ignore
        )
        execStats = tracer.getExecTimeStats()
        for key in execStats:
            print(f"{key}: {execStats[key]}")

        if dotTrace.translate(str.maketrans("", "", string.whitespace)) == "digraphG{}":
            print(
                "Could not find any concurrent behavior \
                        for the given network and depth!"
            )
            sys.exit()

        exportFilePath = os.path.join(OUTPUT_DIR_PATH, f"{RESULT_FILE_NAME}.gv")
        exportFile(exportFilePath, dotTrace)
        print(f"Concurrent behavior detected! Trace(s) written to: {exportFilePath}.")

    except MaudeError as e:
        print(f"Error encountered while executing Maude:\n\t{e}")
    except ValidationError as e:
        print(f"Invalid JSON file!\n{e}")


if __name__ == "__main__":
    main()
