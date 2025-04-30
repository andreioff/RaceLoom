from typing import List, Self, Tuple, cast

from src.errors import ParseError
from src.trace.transition import ITransition, newTraceTransition


class TraceNode:
    __nextId = 0

    def __init__(self, trans: ITransition, vectorClocks: List[List[int]]) -> None:
        self.__id = TraceNode.__nextId
        TraceNode.__nextId += 1
        self.__trans = trans
        self.__vectorClocks = vectorClocks
        # ids of other nodes having transitions racing with this node's transition
        self.__racingNodes: List[int] = []

    @property
    def id(self) -> int:
        return self.__id

    @property
    def trans(self) -> ITransition:
        return self.__trans

    @property
    def vectorClocks(self) -> List[List[int]]:
        return self.__vectorClocks

    def addRacingNode(self, otherNodeId: int) -> None:
        self.__racingNodes.append(otherNodeId)

    def isRacingWith(self, otherNodeId: int) -> bool:
        return otherNodeId in self.__racingNodes

    def isPartOfRace(self) -> bool:
        return len(self.__racingNodes) > 0

    @classmethod
    def fromTuple(cls, t: Tuple) -> Self:  # type: ignore
        el = cls.__validateTupleType(t)  # type: ignore
        return cls(newTraceTransition(el[0]), el[1])

    @staticmethod
    def __validateTupleType(t: Tuple) -> Tuple[str, List[List[int]]]:  # type: ignore
        err = ParseError("Trace element must be of type Tuple[str, List[List[int]]]")
        if not isinstance(t[0], str) or not isinstance(t[1], list):  # type: ignore
            raise err
        for vc in t[1]:  # type: ignore
            if not isinstance(vc, list):
                raise err
            for v in vc:
                if not isinstance(v, int):
                    raise err
        return cast(Tuple[str, List[List[int]]], t)

    def __repr__(self) -> str:
        return f'(\\"{self.trans}\\",{self.vectorClocks})'

    def __str__(self) -> str:
        return f'(\\"{self.trans}\\",{self.vectorClocks})'

    def __hash__(self) -> int:
        return self.__id
