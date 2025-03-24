# mypy: disable-error-code="import-untyped,no-any-unimported,misc"

import os
from math import fsum
from time import perf_counter
from typing import IO

import maude
from src.KATch_comm import KATchComm
from src.KATch_hook import KATCH_HOOK_MAUDE_NAME, KATchHook, KATchStats
from src.maude_encoder import MaudeEncoder
from src.maude_encoder import MaudeModules as mm
from src.maude_encoder import MaudeSorts as ms
from src.model.dnk_maude_model import DNKMaudeModel
from src.trace_collector_hook import TRACE_COLLECTOR_HOOK_MAUDE_NAME, TraceCollectorHook

ENTRY_POINT_NAME = "init"


class MaudeError(Exception):
    pass


class TracerStats:
    def __init__(self) -> None:
        self.execTime = 0.0
        self.katchCacheHits = 0
        self.katchCacheQueryTime = 0.0
        self.katchCalls = 0
        self.katchExecTime = 0.0
        self.collectedTraces = 0

    def setKATchStats(self, katchStats: KATchStats) -> None:
        self.katchCacheHits = len(katchStats.cacheHitTimes)
        self.katchCacheQueryTime = fsum(katchStats.cacheHitTimes)
        self.katchCalls = len(katchStats.katchExecTimes)
        self.katchExecTime = fsum(katchStats.katchExecTimes)

    def __repr__(self) -> str:
        return (
            f"Computing trace(s) time: {self.execTime} seconds\n"
            + f"KATch cache hits: {self.katchCacheHits}\n"
            + f"KATch cache query time: {self.katchCacheQueryTime}\n"
            + f"KATch calls: {self.katchCalls}\n"
            + f"KATch execution time: {self.katchExecTime}\n"
            + f"No. of collected traces: {self.collectedTraces}\n"
        )


class TracerConfig:
    def __init__(
        self,
        outputDirPath: str,
        katchPath: str,
        maudeFilesDirPath: str,
        threads: int,
        verbose: bool,
    ) -> None:
        self.outputDirPath = outputDirPath
        self.katchPath = katchPath
        self.maudeFilesDirPath = maudeFilesDirPath
        self.threads = threads
        self.verbose = verbose


class Tracer:
    maudeInitialized: bool = False

    def __init__(self, config: TracerConfig, traceCollectFile: IO[str]) -> None:
        self.config = config
        self.stats = TracerStats()

        katchComm = KATchComm(self.config.katchPath, self.config.outputDirPath)
        self.traceCollector = TraceCollectorHook(traceCollectFile)
        self.katchHook = KATchHook(katchComm)
        self.__initMaude()

    def __initMaude(self) -> None:
        if Tracer.maudeInitialized:
            return

        success = maude.init(advise=False)
        if not success:
            raise MaudeError(
                "Failed to initialize Maude library! "
                + "Initialization should happen once, maybe it is done multiple times?"
            )
        maude.connectEqHook(KATCH_HOOK_MAUDE_NAME, self.katchHook)
        maude.connectEqHook(TRACE_COLLECTOR_HOOK_MAUDE_NAME, self.traceCollector)

        filePath = os.path.join(self.config.maudeFilesDirPath, "tracer.maude")
        success = maude.load(filePath)
        if not success:
            raise MaudeError(f"Failed to load Maude file: {filePath}.")
        if self.config.verbose:
            maude.input("set print attribute on .")
        Tracer.maudeInitialized = True

    def run(self, model: DNKMaudeModel, depth: int) -> int:
        """Returns the number of traces collected during the run"""
        self.reset()
        self.__declareModelMaudeModule(model)
        mod = self.__declareEntryMaudeModule(model, depth)

        term = mod.parseTerm(f"{ENTRY_POINT_NAME}")
        if term is None:
            raise MaudeError("Failed to declare Tracer entry point.")

        startTime = perf_counter()
        term.erewrite()
        endTime = perf_counter()
        self.stats.execTime = endTime - startTime
        return self.traceCollector.calls

    def __declareModelMaudeModule(self, model: DNKMaudeModel) -> None:
        maude.input(model.toMaudeModule())
        mod = maude.getModule(model.getMaudeModuleName())
        if mod is None:
            raise MaudeError("Failed to declare module for given DyNetKAT model!")

    def __declareEntryMaudeModule(
        self, model: DNKMaudeModel, depth: int
    ) -> maude.Module:
        me = MaudeEncoder()
        me.addProtImport(mm.TRACER)
        me.addProtImport(mm.DNK_MODEL)
        me.addOp(ENTRY_POINT_NAME, ms.STRING_SORT, [])

        sws = model.getBigSwitchTerm()
        cs = model.getControllersMaudeMap()
        me.addEq(
            ENTRY_POINT_NAME,
            f"tracer{{<> p-init({self.config.threads})}}{{{depth}}}({sws}, {cs})",
        )

        maude.input(me.buildAsModule(mm.ENTRY))
        mod = maude.getModule(mm.ENTRY)
        if mod is None:
            raise MaudeError("Failed to declare entry module!")
        return mod

    def getStats(self) -> TracerStats:
        self.stats.setKATchStats(self.katchHook.execStats)
        self.stats.collectedTraces = self.traceCollector.calls
        return self.stats

    def reset(self) -> None:
        self.stats = TracerStats()
        self.katchHook.reset()
        self.traceCollector.reset()
