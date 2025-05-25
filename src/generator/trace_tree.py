from __future__ import annotations

from collections.abc import Iterator
from typing import List, Tuple

from src.model.dnk_maude_model import DNKMaudeModel
from src.trace.node import TraceNode
from src.util import indexInBounds


class TracesBuilderError(Exception):
    pass


class TraceTree:
    def __init__(self, dnkModel: DNKMaudeModel) -> None:
        self.dnkModel = dnkModel
        self._nodes: List[Tuple[TraceNode, int]] = []
        self._nodeIdToIndex: dict[int, int] = {}
        self._isLeaf: List[bool] = []

    def addNode(self, node: TraceNode, parentId: int | None = None) -> None:
        if node.id in self._nodeIdToIndex:
            # required for trace analysis when skipping
            # branches already analyzed
            raise TracesBuilderError(
                "Nodes added to the trace tree must have unique IDs"
            )
        # restore any netkat policies replaced when loading the DNK model
        node.trans.policy = self.dnkModel.netkatRepl.restore(node.trans.policy)
        parentIndex = -1
        if parentId is not None:
            parentIndex = self._nodeIdToIndex.get(parentId, -1)
            if parentIndex == -1:
                raise TracesBuilderError("Parent id not found")
        self._nodes.append((node, parentIndex))
        self._isLeaf.append(True)
        index = len(self._nodes) - 1
        if parentIndex >= 0:
            self._isLeaf[parentIndex] = False
        self._nodeIdToIndex[node.id] = index

    def traceCount(self) -> int:
        count: int = 0
        for v in self._isLeaf:
            if not v:
                continue
            count += 1
        return count

    def getTraceIterator(self) -> TraceIterator:
        return TraceIterator(self)


class TraceIterator(Iterator[List[TraceNode]]):
    def __init__(self, traceTree: TraceTree) -> None:
        self.__traceTree = traceTree
        self.__head = self.__getNextLeafPos(0)

    def __next__(self) -> List[TraceNode]:
        if not indexInBounds(self.__head, len(self.__traceTree._isLeaf)):
            raise StopIteration()
        i = self.__head
        trace: List[TraceNode] = []
        while i >= 0:
            node, i = self.__traceTree._nodes[i]
            trace.append(node)
        trace.reverse()
        self.__head = self.__getNextLeafPos(self.__head + 1)
        return trace

    def __getNextLeafPos(self, start: int) -> int:
        n = len(self.__traceTree._isLeaf)
        if not indexInBounds(start, n):
            return -1
        for i in range(n - start):
            if self.__traceTree._isLeaf[start + i]:
                return start + i
        return -1
