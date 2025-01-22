import inspect
import os

import src
from src.dnk_model import DNKModel
from src.tracer import MaudeError, Tracer, TracerConfig
from src.util import export_file

KATCH_PATH = (
    "/home/andrei/Desktop/Master/_Final_Project" + "/NetKAT_Tests/KATch_forked/katch"
)
OUTPUT_DIR_PATH = "/home/andrei/Desktop/Master/_Final_Project/Tracer/output"


def main() -> None:
    # load src module directory
    srcDir = os.path.dirname(inspect.getfile(src))

    config = TracerConfig(
        outputDirPath=OUTPUT_DIR_PATH,
        katchPath=KATCH_PATH,
        maudeFilesDirPath=f"{srcDir}/maude",
        depth=5,
        allTraces=True,
    )

    try:
        tracer = Tracer(config)

        dotTrace = tracer.run(DNKModel())
        execStats = tracer.getExecTimeStats()
        for key in execStats:
            print(f"{key}: {execStats[key]}")
        export_file(f"{OUTPUT_DIR_PATH}/tracerOutput.gv", dotTrace)
    except MaudeError as e:
        print(f"Error encountered while executing Maude:\n\t{e}")


if __name__ == "__main__":
    main()
