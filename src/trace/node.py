from dataclasses import dataclass
from typing import List, Self, Tuple, cast

from src.errors import ParseError
from src.trace.transition import ITransition, newTraceTransition


@dataclass(frozen=True)
class TraceNode:
    trans: ITransition
    vectorClocks: List[List[int]]

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

    def getIncmpPosPairs(self) -> List[Tuple[int, int]]:
        posPairs: List[Tuple[int, int]] = []
        for i in range(len(self.vectorClocks)):
            for j in range(len(self.vectorClocks)):
                if i >= j:
                    continue
                vc1, vc2 = self.vectorClocks[i], self.vectorClocks[j]
                if (vc1[i] < vc2[i] and vc1[j] > vc2[j]) or (
                    vc1[i] > vc2[i] and vc1[j] < vc2[j]
                ):
                    posPairs.append((i, j))
        return posPairs

    def __repr__(self) -> str:
        return f'(\\"{self.trans}\\",{self.vectorClocks})'

    def __str__(self) -> str:
        return f'(\\"{self.trans}\\",{self.vectorClocks})'
