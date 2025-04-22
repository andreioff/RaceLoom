import argparse
import os
from dataclasses import dataclass
from typing import List

from src.generator.trace_generator_factory import TraceGenOption
from src.stats import StatsEntry, StatsGenerator
from src.util import isExe


class CLIError(Exception):
    pass


@dataclass
class CLIArguments(StatsGenerator):
    katchPath: str
    inputFilePath: str
    depth: int
    threads: int
    debug: bool
    verbose: bool
    strategy: TraceGenOption

    def getStats(self) -> List[StatsEntry]:
        return [
            StatsEntry("inputFile", "Input file", os.path.basename(self.inputFilePath)),
            StatsEntry("strategy", "Trace generation strategy", self.strategy),
            StatsEntry("depth", "Depth", self.depth),
        ]


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
    parser.add_argument(
        "-s",
        "--strategy",
        type=TraceGenOption,
        choices=list(TraceGenOption),
        dest="strategy",
        default=TraceGenOption.BFS,
        help=f"Strategy used to generate the traces (default is '{TraceGenOption.BFS}')",
    )
    return parser


def validateArgs(args: CLIArguments) -> None:
    """Validates the command line arguments and returns the paths to the KATch
    executable and the input JSON file."""
    if not args.katchPath or not args.inputFilePath:
        raise CLIError("Error: provide the arguments <path_to_katch> <input_file>.")

    if not os.path.exists(args.katchPath) or not isExe(args.katchPath):
        raise CLIError("KATch tool could not be found in the given path!")

    fileExt = args.inputFilePath.split(".")[-1]
    if (
        not os.path.isfile(args.inputFilePath)
        or fileExt not in ["json", "maude"]
        or (fileExt == "maude" and not args.debug)
    ):
        raise CLIError("Please provide a .json input file!")
    if args.depth < 0:
        raise CLIError("Depth cannot be negative")
    if args.threads < 1:
        raise CLIError("Number of threads must be a positive integer")
    if args.strategy not in TraceGenOption:
        raise CLIError(f"Unknown strategy: '{args.strategy}'")


def getCLIArgs() -> CLIArguments:
    args = CLIArguments(**vars(buildArgsParser().parse_args()))  # type: ignore
    validateArgs(args)
    return args
