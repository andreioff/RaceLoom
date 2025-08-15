import argparse
import os
from dataclasses import dataclass
from enum import StrEnum


class CLIError(Exception):
    pass


class ScenarioType(StrEnum):
    S1 = "scenario1"
    S2 = "scenario2"
    S2_SUBSET = "scenario2-subset"


@dataclass
class CLIArguments:
    statsFile: str
    scenarioType: str
    outputDir: str


def buildArgsParser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser()
    parser.add_argument("statsFile")
    parser.add_argument("outputDir")
    parser.add_argument(
        "-t",
        "--scenario-type",
        type=str,
        dest="scenarioType",
        default="scenario1",
        help=f"The scenario type that the plots should be about. Accepted values: {', '.join([s for s in ScenarioType])}",
    )
    return parser


def validateArgs(args: CLIArguments) -> None:
    """Validates the command line arguments"""
    if not args.statsFile:
        raise CLIError("Error: provide the arguments <stats_file>.")

    fileExt = args.statsFile.split(".")[-1]
    if not os.path.isfile(args.statsFile) or fileExt != "csv":
        raise CLIError("Please provide a .csv statistics file!")
    if args.scenarioType not in ScenarioType:
        raise CLIError("Unknown scenario type: {args.scenarioType}")
    if not os.path.exists(args.outputDir) or not os.path.isdir(args.outputDir):
        raise CLIError("Please provide a valid output directory!")


def getCLIArgs() -> CLIArguments:
    args = CLIArguments(**vars(buildArgsParser().parse_args()))  # type: ignore
    validateArgs(args)
    return args
