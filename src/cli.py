import argparse
import os
from dataclasses import dataclass
from typing import List

from src.generator.trace_generator_factory import TraceGenOption
from src.stats import StatsEntry, StatsGenerator


class CLIError(Exception):
    pass


@dataclass
class CLIArguments(StatsGenerator):
    sdnModelFilePath: str
    forwardingPropsFilePath: str
    depth: int
    threads: int
    verbose: bool
    strategy: TraceGenOption

    def getStats(self) -> List[StatsEntry]:
        return [
            StatsEntry(
                "sdnModelFile",
                "SDN model file",
                os.path.basename(self.sdnModelFilePath),
            ),
            StatsEntry(
                "forwardingPropsFilePath",
                "Forwarding properties file",
                os.path.basename(self.forwardingPropsFilePath),
            ),
            StatsEntry("strategy", "Trace generation strategy", self.strategy),
            StatsEntry("depth", "Depth", self.depth),
        ]


def buildArgsParser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser()
    parser.add_argument("sdnModelFilePath")
    parser.add_argument("forwardingPropsFilePath")
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
        help="Number of threads to use when generating traces "
        + f"(only used for the '{TraceGenOption.PBFS}' generation strategy)",
    )
    parser.add_argument(
        "-v",
        "--verbose",
        dest="verbose",
        default=False,
        action="store_true",
        help="Print log messages during execution "
        + "(only supported by some generation strategies)",
    )
    parser.add_argument(
        "-s",
        "--strategy",
        type=TraceGenOption,
        choices=list(TraceGenOption),
        dest="strategy",
        default=TraceGenOption.BFS,
        help="Strategy used to generate the traces (default is "
        + f"'{TraceGenOption.BFS}')",
    )
    return parser


def validateArgs(args: CLIArguments) -> None:
    """Validates the command line arguments"""
    if not args.sdnModelFilePath or not args.forwardingPropsFilePath:
        raise CLIError(
            "Error: provide the arguments <sdn_model_file> "
            + "<forwarding_properties_file>."
        )

    fileExt = args.sdnModelFilePath.split(".")[-1]
    if not os.path.isfile(args.sdnModelFilePath) or fileExt != "json":
        raise CLIError("Please provide a .json sdn model file!")
    if not os.path.isfile(args.forwardingPropsFilePath) or fileExt != "json":
        raise CLIError("Please provide a .json forwarding properties file!")
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
