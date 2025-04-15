# mypy: disable-error-code="import-untyped,no-any-unimported,misc"

import os
from typing import IO, List

import maude
from src.analyzer.trace_parser import TraceNode
from src.decorators.exec_time import PExecTimes, with_time_execution
from src.errors import MaudeError
from src.maude_encoder import MaudeEncoder
from src.maude_encoder import MaudeModules as mm
from src.model.dnk_maude_model import DNKMaudeModel
from src.otf.trace_generator import SequentialTraceGenerator
from src.stats import StatsEntry, StatsGenerator


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


class Tracer(PExecTimes, StatsGenerator):
    maudeInitialized: bool = False

    def __init__(
        self,
        config: TracerConfig,
        generator: SequentialTraceGenerator,
    ) -> None:
        self.config = config
        self.execTimes: dict[str, float] = {}
        self.generator = generator
        self.generatedTraces = 0
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

        filePath = os.path.join(self.config.maudeFilesDirPath, "head_normal_form.maude")
        success = maude.load(filePath)
        if not success:
            raise MaudeError(f"Failed to load Maude file: {filePath}.")
        if self.config.verbose:
            maude.input("set print attribute on .")
        Tracer.maudeInitialized = True

    @with_time_execution
    def run(self, model: DNKMaudeModel, depth: int) -> List[List[TraceNode]]:
        """Returns the number of traces collected during the run"""
        self.reset()
        self.__declareModelMaudeModule(model)
        mod = self.__declareEntryMaudeModule(model, depth)
        traces = self.generator.run(model, mod, depth)
        self.generatedTraces = len(traces)
        return traces

    def __declareModelMaudeModule(self, model: DNKMaudeModel) -> None:
        maude.input(model.toMaudeModule())
        mod = maude.getModule(model.getMaudeModuleName())
        if mod is None:
            raise MaudeError("Failed to declare module for given DyNetKAT model!")

    def __declareEntryMaudeModule(
        self, model: DNKMaudeModel, depth: int
    ) -> maude.Module:
        me = MaudeEncoder()
        me.addProtImport(mm.HEAD_NORMAL_FORM)
        me.addProtImport(mm.DNK_MODEL)

        maude.input(me.buildAsModule(mm.ENTRY))
        mod = maude.getModule(mm.ENTRY)
        if mod is None:
            raise MaudeError("Failed to declare entry module!")
        return mod

    def reset(self) -> None:
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
                self.generator.cacheStats.hits,
            ),
            StatsEntry(
                "traceGenCacheMisses",
                "Trace generation cache misses",
                self.generator.cacheStats.misses,
            ),
            StatsEntry("generatedTraces", "Generated traces", self.generatedTraces),
        ]
