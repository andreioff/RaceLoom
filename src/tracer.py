# mypy: disable-error-code="import-untyped,no-any-unimported,misc"

import os
from math import fsum
from time import perf_counter
from typing import Tuple

import maude
from src.KATch_comm import KATchComm
from src.KATch_hook import KATCH_HOOK_MAUDE_NAME, KATchHook, KATchStats
from src.model.dnk_maude_model import DNKMaudeModel

DNK_MODEL_MODULE_NAME = "DNK_MODEL"


class MaudeError(Exception):
    pass


class TracerStats:
    def __init__(self) -> None:
        self.execTime = 0.0
        self.katchCacheHits = 0
        self.katchCacheQueryTime = 0.0
        self.katchCalls = 0
        self.katchExecTime = 0.0

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
        )


class TracerConfig:
    def __init__(
        self,
        outputDirPath: str,
        katchPath: str,
        maudeFilesDirPath: str,
    ) -> None:
        self.outputDirPath = outputDirPath
        self.katchPath = katchPath
        self.maudeFilesDirPath = maudeFilesDirPath


class Tracer:
    maudeInitialized: bool = False

    def __init__(self, config: TracerConfig) -> None:
        self.config = config
        self.stats = TracerStats()

        katchComm = KATchComm(self.config.katchPath, self.config.outputDirPath)
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

        filePath = os.path.join(self.config.maudeFilesDirPath, "tracer.maude")
        success = maude.load(filePath)
        if not success:
            raise MaudeError(f"Failed to load Maude file: {filePath}.")
        Tracer.maudeInitialized = True

    def run(
        self, model: DNKMaudeModel, depth: int, allTraces: bool
    ) -> Tuple[str, bool]:
        """Returns a Maude term containing a trace tree"""
        self.reset()
        mod = self.__declareModelMaudeModule(model)
        term = self.__buildTracerMaudeEntryPoint(model, mod, depth, allTraces)

        startTime = perf_counter()
        term.reduce()
        endTime = perf_counter()
        self.stats.execTime = endTime - startTime

        prettyTerm = str(term.prettyPrint(maude.PRINT_FORMAT))
        return prettyTerm, prettyTerm == "TEmpty"

    def __declareModelMaudeModule(self, model: DNKMaudeModel) -> maude.Module:
        modContentStr = model.toMaudeModuleContent()
        maude.input(
            f"""
            fmod {DNK_MODEL_MODULE_NAME} is
            protecting TRACER .

            {modContentStr}
            endfm
            """
        )
        mod = maude.getModule(DNK_MODEL_MODULE_NAME)
        if mod is None:
            raise MaudeError("Failed to declare module for given DyNetKAT model!")
        return mod

    def __buildTracerMaudeEntryPoint(
        self, model: DNKMaudeModel, mod: maude.Module, depth: int, allTraces: bool
    ) -> maude.Term:
        sws = model.getBigSwitchTerm()
        cs = model.getControllersMaudeMap()
        allTracesFlag = "true" if allTraces else "false"

        term = mod.parseTerm(f"tracer{{{depth}, {allTracesFlag}}}({sws}, {cs})")

        if term is None:
            raise MaudeError("Failed to declare Tracer entry point.")
        return term

    def convertTraceToDOT(self, termContent: str) -> str:
        """Takes a string containing a Maude trace tree and returns
        its representation in DOT format"""
        modName = "TRACE_TREE_TO_DOT"
        mod = maude.getModule(modName)
        if mod is None:
            raise MaudeError(f"Failed to get module {modName}!")

        term2 = "TraceToDOT(" + termContent + ")"
        t2 = mod.parseTerm(term2)
        if t2 is None:
            raise MaudeError("Failed to parse given term!")

        t2.reduce()
        return str(t2)[1:-1].replace("\\n", "\n").replace('\\"', '"')

    def getExecTimeStats(self) -> TracerStats:
        self.stats.setKATchStats(self.katchHook.execStats)
        return self.stats

    def reset(self) -> None:
        self.stats = TracerStats()
        self.katchHook.reset()
