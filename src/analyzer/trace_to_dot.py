from src.util import splitIntoLines
from os import linesep
from src.analyzer.trace_parser import TraceNode
from typing import List
from enum import StrEnum
from src.model.dnk_maude_model import ElementType


class ColorScheme(StrEnum):
    ERR_PRIMARY = "#FF2400"
    ERR_SECONDARY = "#FF9280"
    ACCENT = "#F2F4FB"
    NODE_BG = "#F2F4FB"
    EDGE = "#000000"


def traceToDOT(nodes: List[TraceNode], elDict: dict[int, ElementType]) -> str:
    sb: List[str] = ["digraph g {"]
    nodeId: int = -1
    for node in nodes:
        nodeId += 1
        sb.append(f'n{nodeId} [label=<{__getNodeLabel(node, elDict)}>, '
                  + f'shape=rectangle, style=filled, fillcolor="{__getNodeColor(node)}"];')
        if nodeId == 0:  # first node does not have a transition
            continue
        label = splitIntoLines(str(node.trans), 50, 10)
        edgeColor = ColorScheme.ERR_PRIMARY if node.trans.causesHarmfulRace else ColorScheme.EDGE
        penwidth = 2.0 if node.trans.causesHarmfulRace else 1.0
        sb.append(
            f'n{nodeId-1} -> n{nodeId} [label="{label}", color="{edgeColor}", penwidth={penwidth}];')
    sb.append("}")  # close digraph
    return linesep.join(sb)


def __getNodeColor(node: TraceNode) -> str:
    if node.racingElements is not None:
        return ColorScheme.ERR_PRIMARY
    if len(node.getIncmpPosPairs()) > 0:
        return ColorScheme.ERR_SECONDARY
    return ColorScheme.NODE_BG


def __getNodeLabel(node: TraceNode, elDict: dict[int, ElementType]) -> str:
    typeLabel = ""
    vcLabel = ""
    re = (-1, -1) if node.racingElements is None else node.racingElements
    prefix = ""
    for i, vc in enumerate(node.vectorClocks):
        typeLabel += (prefix + elDict[i])
        vcLabel += prefix
        if i == re[0] or i == re[1]:
            vcLabel += f'<font color="{ColorScheme.ACCENT}">{vc}</font>'
        else:
            vcLabel += f"{vc}"
        prefix = ", "
    return typeLabel + "<br/>[" + vcLabel + "]"
