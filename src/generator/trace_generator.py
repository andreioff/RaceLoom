# mypy: disable-error-code="import-untyped,no-any-unimported,misc"

import os
from abc import ABC, abstractmethod
from typing import Dict, Hashable, List, Tuple

import maude
from src.decorators.cache_stats import CacheStats
from src.decorators.exec_time import PExecTimes, with_time_execution
from src.errors import MaudeError
from src.generator.trace_tree import TraceTree
from src.maude_encoder import MaudeModules as mm
from src.model.dnk_maude_model import DNKMaudeModel
from src.stats import StatsEntry, StatsGenerator
from src.tracer_config import TracerConfig


class TraceGenerator(PExecTimes, StatsGenerator, ABC):
    maudeInitialized: bool = False

    def __init__(self, config: TracerConfig) -> None:
        self.config = config
        self.cache: Dict[Tuple[Hashable, ...], List[Tuple[str, str, str]]] = {}
        self.cacheStats = CacheStats(0, 0)
        self.execTimes: dict[str, float] = {}
        self.generatedTraces = 0
        self.__initMaude()

    @abstractmethod
    def _generateTraces(
        self, model: DNKMaudeModel, mod: maude.Module, depth: int
    ) -> TraceTree: ...

    @abstractmethod
    def _getEntryMaudeModule(self, name: str) -> maude.Module: ...

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
        """Returns the number of traces collected during the run"""
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
        maude.input(model.toMaudeModule())
        mod = maude.getModule(mm.DNK_MODEL)
        if mod is None:
            raise MaudeError("Failed to declare module for given DyNetKAT model!")

    def reset(self) -> None:
        self.cache = {}
        self.cacheStats = CacheStats(0, 0)
        self.execTimes = {}
        self.generatedTraces = 0

    def getStats(self) -> List[StatsEntry]:
        return [
            StatsEntry(
                "tracesGenTime",
                "Trace(s) generation time",
                self.getTotalExecTime(),
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
