from enum import StrEnum
from typing import Dict

from src.generator.parallel_trace_generator import ParallelBFSTraceGenerator
from src.generator.sequential_trace_generator import (BFSTraceGenerator,
                                                      DFSTraceGenerator)
from src.generator.trace_generator import TraceGenerator
from src.tracer_config import TracerConfig


class TraceGenOption(StrEnum):
    DFS = "dfs"
    BFS = "bfs"
    PBFS = "pbfs"


_generators: Dict[TraceGenOption, type[TraceGenerator]] = {
    TraceGenOption.DFS: DFSTraceGenerator,
    TraceGenOption.BFS: BFSTraceGenerator,
    TraceGenOption.PBFS: ParallelBFSTraceGenerator,
}


def newTraceGenerator(option: TraceGenOption, config: TracerConfig) -> TraceGenerator:
    return _generators[option](config)
