from enum import StrEnum

from src.generator.parallel_trace_generator import ParallelBFSTraceGenerator
from src.generator.sequential_trace_generator import (BFSTraceGenerator,
                                                      DFSTraceGenerator)
from src.generator.trace_generator import TraceGenerator


class TraceGenOption(StrEnum):
    DFS = "dfs"
    BFS = "bfs"
    PBFS = "pbfs"


def newTraceGenerator(option: TraceGenOption, threads: int) -> TraceGenerator:
    if option == TraceGenOption.DFS:
        return DFSTraceGenerator()
    if option == TraceGenOption.PBFS:
        return ParallelBFSTraceGenerator(threads)
    return BFSTraceGenerator()
