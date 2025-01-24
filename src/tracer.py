# mypy: disable-error-code="import-untyped,no-any-unimported,misc"

from time import perf_counter

import maude
from src.dnk_model import DNKModel
from src.KATch_comm import KATchComm
from src.KATch_hook import KATCH_HOOK_MAUDE_NAME, KATchHook

DNK_MODEL_MODULE_NAME = "DNK_MODEL"


class MaudeError(Exception):
    pass


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
        self.runExecTime = -1.0

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

        filePath = f"{self.config.maudeFilesDirPath}/tracer.maude"
        success = maude.load(filePath)
        if not success:
            raise MaudeError(f"Failed to load Maude file: {filePath}.")
        Tracer.maudeInitialized = True

    def run(self, model: DNKModel, depth: int, allTraces: bool) -> str:
        self.reset()
        mod = self.__declareModelMaudeModule(model)
        term = self.__buildTracerMaudeEntryPoint(model, mod, depth, allTraces)

        startTime = perf_counter()
        term.reduce()
        endTime = perf_counter()
        self.runExecTime = endTime - startTime

        return self.__convertTraceToDOT(term)

    def __declareModelMaudeModule(self, model: DNKModel) -> maude.Module:
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
        self, model: DNKModel, mod: maude.Module, depth: int, allTraces: bool
    ) -> maude.Term:
        sws = model.getBigSwitchTerm()
        cs = model.getControllersMaudeMap()
        allTracesFlag = "true" if allTraces else "false"

        term = mod.parseTerm(f"tracer{{{depth}, {allTracesFlag}}}({sws}, {cs})")

        if term is None:
            raise MaudeError("Failed to declare Tracer entry point.")
        return term

    def __convertTraceToDOT(self, term: maude.Term) -> str:
        modName = "TRACE_TREE_TO_DOT"
        mod = maude.getModule(modName)
        if mod is None:
            raise MaudeError(f"Failed to get module {modName}!")

        term2 = "TraceToDOT(" + term.prettyPrint(maude.PRINT_FORMAT) + ")"
        t2 = mod.parseTerm(term2)
        t2.reduce()
        return str(t2)[1:-1].replace("\\n", "\n").replace('\\"', '"')

    def getExecTimeStats(self) -> dict[str, str]:
        hookStats = self.katchHook.execStats
        stats: dict[str, str] = {
            "Computing trace(s) time": f"{self.runExecTime} seconds",
        }
        for key, times in hookStats.items():
            stats[key] = f"{len(times)}"
            stats[key + " total processing time"] = f"{sum(times)} seconds"
        return stats

    def reset(self) -> None:
        self.runExecTime = -1.0
        self.katchHook.reset()
