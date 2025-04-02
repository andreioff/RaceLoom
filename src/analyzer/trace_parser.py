import re
from typing import List, Self, Tuple, cast


class ParseError(Exception):
    pass


class TraceTransition:
    def __init__(self) -> None:
        self.policy = ""
        self.causesHarmfulRace = False

    def isModifyingVCPos(self, pos: int) -> bool:
        return False

    def __str__(self) -> str:
        return ""


class PktProcTrans(TraceTransition):
    def __init__(self, policy: str, swPos: int) -> None:
        super().__init__()
        self.policy = policy
        self.swPos = swPos

    def isModifyingVCPos(self, pos: int) -> bool:
        return self.swPos == pos

    @classmethod
    def fromStr(cls, s: str) -> Self:
        res = re.search(r"proc\('([^']*)',([0-9]+)\)", s)
        if res is None:
            raise ParseError(
                f"'{s}' is not a valid packet processing transition")

        t = cls(str(res.group(1)), int(res.group(2)))
        return t

    def __str__(self) -> str:
        return f"proc('{self.policy}', {self.swPos})"


class RcfgTrans(TraceTransition):
    def __init__(self, policy: str, srcPos: int, dstPos: int, channel: str) -> None:
        super().__init__()
        self.policy = policy
        self.srcPos: int = srcPos
        self.dstPos: int = dstPos
        self.channel: str = channel

    def isModifyingVCPos(self, pos: int) -> bool:
        return self.srcPos == pos or self.dstPos == pos

    @classmethod
    def fromStr(cls, s: str) -> Self:
        res = re.search(r"rcfg\(([^,]*), '([^']*)', ([0-9]+), ([0-9]+)\)", s)
        if res is None:
            raise ParseError(
                f"'{s}' is not a valid reconfiguration transition")

        t = cls(
            str(res.group(2)),
            int(res.group(3)),
            int(res.group(4)),
            str(res.group(1)),
        )
        return t

    def __str__(self) -> str:
        return f"rcfg({self.channel}, '{self.policy}', {self.srcPos}, {self.dstPos})"


class TraceNode:
    def __init__(self) -> None:
        self.trans = TraceTransition()
        self.vectorClocks: List[List[int]] = []
        self.racingElements: Tuple[int, int] | None = None

    def fromTuple(self, t: Tuple) -> Self:  # type: ignore
        el = self.__validateTupleType(t)  # type: ignore
        self.vectorClocks = el[1]
        if not el[0]:
            self.trans = TraceTransition()
        elif el[0][:4] == "rcfg":
            self.trans = RcfgTrans.fromStr(el[0])
        else:
            self.trans = PktProcTrans.fromStr(el[0])

        return self

    def __validateTupleType(self, t: Tuple  # type: ignore
                            ) -> Tuple[str, List[List[int]]]:
        err = ParseError(
            "Trace element must be of type Tuple[str, List[List[int]]]")
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


class TraceParser:
    @staticmethod
    def parse(traceStr: str) -> List[TraceNode]:
        """Raises SyntaxError if the given argument does not use valid Python3 syntax.
        Raises ParseError if the given argument is not a valid trace"""
        pTrace = eval(traceStr)  # type: ignore
        if not isinstance(pTrace, list):  # type: ignore
            raise ParseError("Resulting trace is not a Python list")

        trace: List[TraceNode] = []
        for el in pTrace:
            if not isinstance(el, tuple):
                raise ParseError("Trace elements must be tuples")
            trace.append(TraceNode().fromTuple(el))
        return trace
