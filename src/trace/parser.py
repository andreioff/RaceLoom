from typing import List

from src.errors import ParseError
from src.trace.node import TraceNode


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
            trace.append(TraceNode.fromTuple(el))
        return trace
