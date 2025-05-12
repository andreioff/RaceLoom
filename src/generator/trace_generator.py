# mypy: disable-error-code="import-untyped,no-any-unimported,misc"

import os
from abc import ABC, abstractmethod
from time import perf_counter
from typing import Dict, Hashable, List, Tuple

import maude
from src.decorators.cache_stats import CacheStats
from src.decorators.exec_time import ExecTimes, with_time_execution
from src.errors import MaudeError
from src.generator.trace_tree import TraceTree
from src.maude_encoder import MaudeModules as mm
from src.model.dnk_maude_model import DNKMaudeModel
from src.stats import StatsEntry, StatsGenerator
from src.tracer_config import TracerConfig

_MAUDE_EXEC_TIME_KEY = "maudeExecTime"


class TraceGenerator(ExecTimes, StatsGenerator, ABC):
    maudeInitialized: bool = False

    def __init__(self, config: TracerConfig) -> None:
        ExecTimes.__init__(self)
        StatsGenerator.__init__(self)
        self.config = config
        self.cache: Dict[Tuple[Hashable, ...], List[Tuple[str, str, str]]] = {}
        self.cacheStats = CacheStats(0, 0)
        self.generatedTraces = 0
        self.__initMaude()

    @abstractmethod
    def _generateTraces(
        self, model: DNKMaudeModel, mod: maude.Module, depth: int
    ) -> TraceTree: ...

    @abstractmethod
    def _getEntryMaudeModule(self, name: str) -> str: ...

    def __initMaude(self) -> None:
        if TraceGenerator.maudeInitialized:
            return

        success = maude.init(advise=False)
        if not success:
            raise MaudeError(
                "Failed to initialize Maude library! "
                + "Initialization should happen once, maybe it is done multiple times?"
            )

        filePath = os.path.join(
            self.config.maudeFilesDirPath, "parallel_head_normal_form.maude"
        )
        success = maude.load(filePath)
        if not success:
            raise MaudeError(f"Failed to load Maude file: {filePath}.")
        if self.config.verbose:
            maude.input("set print attribute on .")
        TraceGenerator.maudeInitialized = True

    @with_time_execution
    def run(self, model: DNKMaudeModel, depth: int) -> TraceTree:
        """Returns the trace tree collected during the run"""
        self.reset()
        self.__declareModelMaudeModule(model)
        mod = self.__declareEntryMaudeModule()
        traceTree = self._generateTraces(model, mod, depth)
        self.generatedTraces = traceTree.traceCount()
        return traceTree

    def __declareEntryMaudeModule(self) -> maude.Module:
        maude.input(self._getEntryMaudeModule(mm.ENTRY))
        mod = maude.getModule(mm.ENTRY)
        if mod is None:
            raise MaudeError("Failed to declare entry module!")
        return mod

    def __declareModelMaudeModule(self, model: DNKMaudeModel) -> None:
        startTime = perf_counter()
        maude.input(model.toMaudeModule())
        mod = maude.getModule(mm.DNK_MODEL)
        if mod is None:
            raise MaudeError("Failed to declare module for given DyNetKAT model!")
        endTime = perf_counter()
        self.addExecTime(_MAUDE_EXEC_TIME_KEY, endTime - startTime)

    def reset(self) -> None:
        self.cache = {}
        self.cacheStats = CacheStats(0, 0)
        self.generatedTraces = 0
        self.resetExecTimes()

    def getStats(self) -> List[StatsEntry]:
        return [
            StatsEntry(
                "tracesGenTime",
                "Trace(s) generation time",
                self.getWrapperTotalExecTime(),
            ),
            StatsEntry(
                _MAUDE_EXEC_TIME_KEY,
                "Maude execution time",
                self.getExecTime(_MAUDE_EXEC_TIME_KEY),
            ),
            StatsEntry(
                "traceGenCacheHits",
                "Trace generation cache hits",
                self.cacheStats.hits,
            ),
            StatsEntry(
                "traceGenCacheMisses",
                "Trace generation cache misses",
                self.cacheStats.misses,
            ),
            StatsEntry("generatedTraces", "Generated traces", self.generatedTraces),
        ]
