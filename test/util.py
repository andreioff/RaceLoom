import inspect
import os
import test.src
from typing import List, Self

import networkx
import networkx.algorithms as ga
from networkx.classes.coreviews import AdjacencyView, AtlasView

import src
from src.maude_encoder import MaudeModules as mm
from src.model.dnk_maude_model import (DNKMaudeModel, ElementMetadata,
                                       ElementType)

PROJECT_DIR = os.path.dirname(inspect.getabsfile(src))
TEST_DIR = os.path.dirname(inspect.getabsfile(test.src))


class DNKTestModel(DNKMaudeModel):
    def __init__(self, maudeModuleContent: str, parallelExpr: str):
        """Initializes a DNKModel object from a Maude module content
        and an expression of shape 'T1 || T2 || ...'. Considers any term in
        the expression to be a switch if it contains 'SW' in its name"""
        super().__init__()
        self.maudeModuleContent = maudeModuleContent
        self.elementTerms: List[str] = []
        self.elMetadata: List[ElementMetadata] = []

        for i, term in enumerate(parallelExpr.split("||")):
            self.elementTerms.append(term.strip())
            if "SW" in term:
                self.elMetadata.append(ElementMetadata(i, ElementType.SW))
                continue
            self.elMetadata.append(ElementMetadata(i, ElementType.CT))

    @classmethod
    def fromJson(cls, jsonStr: str) -> Self:
        raise Exception("Not implemented")

    def toMaudeModule(self) -> str:
        return f"""
            mod {mm.DNK_MODEL} is
            protecting {mm.DNK_MODEL_UTIL} .
            {self.maudeModuleContent}
            endm
        """

    def getElementTerms(self) -> List[str]:
        return self.elementTerms

    def getBranchCounts(self) -> str:
        return "unknown"

    def getElementsMetadata(self) -> List[ElementMetadata]:
        return self.elMetadata

    @classmethod
    def fromDebugMaudeFile(cls, fileContent: str) -> DNKMaudeModel:
        # Only for debugging purposes
        fileContentLines = fileContent.split("\n")
        maudeStr = "\n".join(fileContentLines[:-2])
        elsMap = fileContentLines[-2]
        return cls(maudeStr, elsMap)


def assertEqualTrees(t1: networkx.MultiGraph, t2: networkx.MultiGraph) -> None:
    assert ga.is_tree(t1)
    assert ga.is_tree(t2)
    assert t1.number_of_nodes() == t2.number_of_nodes()
    assert t1.number_of_edges() == t2.number_of_edges()

    t1 = t1.to_undirected()
    t2 = t2.to_undirected()
    centersT1 = ga.center(t1)
    centersT2 = ga.center(t2)
    visitedNodes1: dict[str, bool] = {}
    visitedNodes2: dict[str, bool] = {}
    assert areEqualTrees(t1, t2, centersT1, centersT2, visitedNodes1, visitedNodes2)
    assert (
        len(visitedNodes1) == t1.number_of_nodes()
    ), f"Not all nodes were visited! Expected: {t1.number_of_nodes()}, actual: {len(visitedNodes1)}."
    assert (
        len(visitedNodes2) == t2.number_of_nodes()
    ), f"Not all nodes were visited! Expected: {t2.number_of_nodes()}, actual: {len(visitedNodes2)}."


def areEqualTrees(
    t1: networkx.MultiGraph,
    t2: networkx.MultiGraph,
    nodeIds1: List[str],
    nodeIds2: List[str],
    visitedNodes1: dict[str, bool],
    visitedNodes2: dict[str, bool],
) -> bool:
    if not nodeIds1 and not nodeIds2:
        return True
    if not nodeIds1 or not nodeIds2:
        return False

    for nodeId in nodeIds1:
        visitedNodes1[nodeId] = True
    for nodeId in nodeIds2:
        visitedNodes2[nodeId] = True

    if not areSameNodes(t1, t2, nodeIds1, nodeIds2):
        return False

    nodes1: List[AdjacencyView] = list(map(lambda x: t1[x], nodeIds1))
    nodes2: List[AdjacencyView] = list(map(lambda x: t2[x], nodeIds2))
    newNodeIds1: List[str] = extractAllKeysNotInDict(nodes1, visitedNodes1)
    newNodeIds2: List[str] = extractAllKeysNotInDict(nodes2, visitedNodes2)
    return areEqualTrees(t1, t2, newNodeIds1, newNodeIds2, visitedNodes1, visitedNodes2)


def areSameNodes(
    t1: networkx.MultiGraph,
    t2: networkx.MultiGraph,
    nodeIds1: List[str],
    nodeIds2: List[str],
) -> bool:
    if len(nodeIds1) != len(nodeIds2):
        return False

    data1 = t1.nodes.data()
    data2 = t2.nodes.data()
    usedNodes: List[str] = []
    for n1 in nodeIds1:
        hasPair = False
        for n2 in nodeIds2:
            if (
                n2 not in usedNodes
                and data1[n1]["label"] == data2[n2]["label"]
                and areSameNeighborhoods(t1[n1], t2[n2])
            ):
                hasPair = True
                usedNodes.append(n2)
                break
        if not hasPair:
            return False

    return True


def areSameNeighborhoods(a1: AdjacencyView, a2: AdjacencyView) -> bool:
    """Neighborhoods are equal if they have the same number of nodes and each node
    has a matching pair with the same number of edges and edge lables"""
    if len(a1.keys()) != len(a2.keys()):
        return False

    usedNodes: List[str] = []
    for _n1, edges1 in a1.items():
        hasPair = False
        for n2, edges2 in a2.items():
            if n2 not in usedNodes and areSameEdges(edges1, edges2):
                hasPair = True
                usedNodes.append(n2)
                break
        if not hasPair:
            return False
    return True


def areSameEdges(edges1: AtlasView, edges2: AtlasView) -> bool:
    """2 sets of edges are equal if they have the same number of edges
    and each edge has a matching pair with the same label."""
    if len(edges1.keys()) != len(edges2.keys()):
        return False

    edgeLabels1: List[str] = getEdgesLabels(edges1)
    if len(edgeLabels1) != len(edges1.keys()):
        return False  # all edges must have labels

    edgeLabels2: List[str] = getEdgesLabels(edges2)
    if len(edgeLabels2) != len(edges2.keys()):
        return False  # all edges must have labels

    edgeLabels1.sort()
    edgeLabels2.sort()
    return edgeLabels1 == edgeLabels2


def getEdgesLabels(edges: AtlasView) -> List[str]:
    edgeLabels: List[str] = []
    for edgeAttributes in edges.values():
        edgeLabels.append(edgeAttributes["label"])
    return edgeLabels


def extractAllKeysNotInDict(
    adjViews: List[AdjacencyView], usedKeys: dict[str, bool]
) -> List[str]:
    keys: List[str] = []
    for a in adjViews:
        for key in a.keys():
            if key not in usedKeys:
                keys.append(key)
    return keys
