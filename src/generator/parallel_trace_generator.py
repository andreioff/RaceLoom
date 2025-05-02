# mypy: disable-error-code="import-untyped,no-any-unimported,misc"
from dataclasses import dataclass, field
from typing import Hashable, List, Tuple

import maude
from src.decorators.cache_stats import CacheStats
from src.generator.trace_generator import TraceGenerator
from src.generator.trace_tree import TraceTree
from src.generator.util import extractListTerms, extractTransData, getSort
from src.maude_encoder import MaudeEncoder, MaudeModules
from src.maude_encoder import MaudeOps as mo
from src.maude_encoder import MaudeSorts as ms
from src.model.dnk_maude_model import DNKMaudeModel
from src.trace.node import TraceNode
from src.trace.transition import newTraceTransition
from src.trace.vector_clocks import newVectorClocks
from src.tracer_config import TracerConfig
from src.util import uniformSplit

_HOOK_MAUDE_NAME = "storeOutputGetNextInput"
_ENTRY_MAUDE_EQUATION = "entry"


@dataclass
class GeneratorState:
    depth: int = 0
    currLayer: dict[TraceNode, Tuple[str, str]] = field(default_factory=lambda: {})
    results: List[Tuple[List[Tuple[str, str, str]], bool]] = field(
        default_factory=lambda: []
    )
    nodeToIndex: dict[TraceNode, int] = field(default_factory=lambda: {})
    uniqueDNKData: List[Tuple[str, str]] = field(default_factory=lambda: [])


class ProcessHook(maude.Hook):  # type: ignore
    def __init__(
        self,
        cache: dict[Tuple[Hashable, ...], List[Tuple[str, str, str]]],
        cacheStats: CacheStats,
        threads: int,
    ) -> None:
        super().__init__()
        self.__threads = threads
        self.cache = cache
        self.cacheStats = cacheStats
        self.__init = False
        self.traceTree = TraceTree()
        self.__model = DNKMaudeModel()
        self.__state = GeneratorState()

    def setModel(self, newModel: DNKMaudeModel) -> None:
        self.__model = newModel

    def setDepth(self, newDepth: int) -> None:
        self.__state.depth = newDepth

    def __initGen(self) -> None:
        startDnkExpr = MaudeEncoder.parallelSeq(self.__model.getElementTerms())
        startVC = newVectorClocks(len(self.__model.getElementTerms()))
        startNode = TraceNode.fromTuple(("", startVC))
        self.traceTree.addNode(startNode)

        # currNode to (dnkExpr, previous transition type)
        self.__state.currLayer = {startNode: (startDnkExpr, mo.TRANS_TYPE_NONE)}

    def reset(self) -> None:
        self.__init = False
        self.traceTree = TraceTree()
        self.__model = DNKMaudeModel()
        self.__state = GeneratorState()

    def run(self, term: maude.Term, data: maude.HookData) -> maude.Term:
        s = self.__state
        # Reduce arguments first
        for arg in term.arguments():
            arg.reduce()
        module = term.symbol().getModule()
        # we assume that the first argument to the operator is the
        # result list calculated by Maude
        resultListTerm = term.arguments().argument()

        if not self.__init:
            self.__initGen()
            self.__init = True
        else:
            s.currLayer = self.__processMaudeResult(module, resultListTerm)
            s.depth -= 1
            if s.depth <= 0:
                return module.parseTerm(MaudeEncoder.emptyTermList())

        self.__setUniqueDNKData()

        # list of (results, is computed)
        s.results = [([], False) for _ in range(len(s.uniqueDNKData))]
        self.__addCachedResults()

        inputTerms = self.__makeMaudeInput()
        inputTerm = module.parseTerm(MaudeEncoder.toTermList(inputTerms))
        if inputTerm is None:
            return MaudeEncoder.emptyTermList()
        return inputTerm

    def __processMaudeResult(
        self, module: maude.Module, term: maude.Term
    ) -> dict[TraceNode, Tuple[str, str]]:
        self.__addNextTransitions(module, term)
        nextLayer: dict[TraceNode, Tuple[str, str]] = {}
        for parentNode, index in self.__state.nodeToIndex.items():
            res = self.__state.results[index][0]
            for prevTransType, transLabel, dnkExpr in res:
                node = self.__addNewNode(transLabel, parentNode)
                nextLayer[node] = (dnkExpr, prevTransType)
        return nextLayer

    def __addNewNode(self, transLabel: str, parentNode: TraceNode) -> TraceNode:
        trans = newTraceTransition(transLabel)
        vc = trans.updateVC(parentNode.vectorClocks)
        node = TraceNode(trans, vc)
        self.traceTree.addNode(node, parentNode.id)
        return node

    def __addCachedResults(self) -> None:
        for i, entry in enumerate(self.__state.uniqueDNKData):
            cachedNeighbors = self.cache.get(entry, [])
            if not cachedNeighbors:
                self.cacheStats.misses += 1
                continue
            self.cacheStats.hits += 1
            self.__state.results[i] = (cachedNeighbors, True)

    def __setUniqueDNKData(self) -> None:
        s = self.__state
        s.nodeToIndex = {}
        s.uniqueDNKData = []
        if not s.currLayer:
            return

        dnkDataToIndex: dict[Tuple[str, str], int] = {}
        nextIndex = 0
        for node, dnkTup in s.currLayer.items():
            i = dnkDataToIndex.get(dnkTup, -1)
            if i == -1:
                dnkDataToIndex[dnkTup] = nextIndex
                s.nodeToIndex[node] = nextIndex
                nextIndex += 1
                continue
            s.nodeToIndex[node] = i
        s.uniqueDNKData = list(dnkDataToIndex.keys())

    def __addNextTransitions(
        self,
        mod: maude.Module,
        result: maude.Term,
    ) -> None:
        neighbors = extractListTerms(result, getSort(mod, ms.TDATA))
        for n in neighbors:
            (index, transType, transLabel, dnkExpr) = extractTransData(n, mod)
            self.__state.results[index][0].append((transType, transLabel, dnkExpr))
        for i, entry in enumerate(self.__state.uniqueDNKData):
            self.cache.setdefault(entry, self.__state.results[i][0])
            self.__state.results[i] = (self.__state.results[i][0], True)

    def __makeMaudeInput(self) -> List[str]:
        if not self.__state.uniqueDNKData:
            return []
        inputs: List[str] = []
        for i, t in enumerate(self.__state.uniqueDNKData):
            if self.__state.results[i][1]:
                continue
            inputs.append(MaudeEncoder.hnfInput(i, t[1], t[0]))
        splitInputs = uniformSplit(inputs, self.__threads)
        return [MaudeEncoder.parallelHnfWorkerInputTerm(li) for li in splitInputs]


class ParallelBFSTraceGenerator(TraceGenerator):
    def __init__(self, config: TracerConfig) -> None:
        super().__init__(config)
        self.maudeHook = ProcessHook(self.cache, self.cacheStats, self.config.threads)
        maude.connectEqHook(_HOOK_MAUDE_NAME, self.maudeHook)

    def reset(self) -> None:
        super().reset()

    def _generateTraces(
        self, model: DNKMaudeModel, mod: maude.Module, depth: int
    ) -> TraceTree:
        self.maudeHook.reset()
        self.maudeHook.setModel(model)
        self.maudeHook.setDepth(depth)

        term = mod.parseTerm(_ENTRY_MAUDE_EQUATION)
        (res, _) = term.erewrite()
        return self.maudeHook.traceTree

    def _getEntryMaudeModule(self, name: str) -> maude.Module:
        me = MaudeEncoder()
        me.addProtImport(MaudeModules.DNK_MODEL)
        me.addProtImport(MaudeModules.PARALLEL_HEAD_NORMAL_FORM)

        workersConfig = MaudeEncoder.metaInterpretersInitCall(self.config.threads)
        me.addOp(_ENTRY_MAUDE_EQUATION, ms.NAT, [])
        me.addEq(
            _ENTRY_MAUDE_EQUATION,
            MaudeEncoder.parallelGeneratorEntryCall(workersConfig),
        )

        return me.buildAsModule(name)
