# mypy: disable-error-code="import-untyped,no-any-unimported,misc"

import os
from typing import List

import maude
from src.decorators.exec_time import PExecTimes, with_time_execution
from src.errors import MaudeError
from src.generator.trace_generator import TraceGenerator
from src.maude_encoder import MaudeEncoder
from src.maude_encoder import MaudeModules as mm
from src.model.dnk_maude_model import DNKMaudeModel
from src.stats import StatsEntry, StatsGenerator
from src.trace.node import TraceNode


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
        generator: TraceGenerator,
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

        filePath = os.path.join(
            self.config.maudeFilesDirPath, "parallel_head_normal_form.maude"
        )
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
        mod = self.__declareEntryMaudeModule(self.generator.getRequiredImports())
        traces = self.generator.run(model, mod, depth)
        self.generatedTraces = len(traces)
        return traces

    def __declareModelMaudeModule(self, model: DNKMaudeModel) -> None:
        maude.input(model.toMaudeModule())
        mod = maude.getModule(model.getMaudeModuleName())
        if mod is None:
            raise MaudeError("Failed to declare module for given DyNetKAT model!")

    def __declareEntryMaudeModule(self, imports: List[mm]) -> maude.Module:
        me = MaudeEncoder()
        for imp in imports:
            me.addProtImport(imp)
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
        return self.generator.getStats() + [
            StatsEntry(
                "tracesGenTime",
                "Trace(s) generation time",
                self.getTotalExecTime(),
            ),
            StatsEntry("generatedTraces", "Generated traces", self.generatedTraces),
        ]
