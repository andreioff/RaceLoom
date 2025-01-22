# mypy: disable-error-code="import-untyped,no-any-unimported,misc"

from time import perf_counter
from typing import List, Tuple

import maude
from src.KATch_comm import KATchComm

CACHE_HIT = "KATch cache hits"
KATCH_CALL = "KATch command calls"
KATCH_HOOK_MAUDE_NAME = "NetKATToNF"


class KATchError(Exception):
    pass


class KATchHook(maude.Hook):  # type: ignore
    def __init__(self, katchComm: KATchComm) -> None:
        super().__init__()
        self.katchComm = katchComm
        self.cache: dict[str, str] = {}
        self.execStats: dict[str, List[float]] = {}

    def run(self, term: maude.Term, data: maude.HookData) -> maude.Term:
        # Reduce arguments first
        for arg in term.arguments():
            arg.reduce()

        # assumes the first arg is the netkat encoding to be used
        netkatEncoding = str(term.arguments().argument())

        # process the netkat expression
        startTime = perf_counter()
        procType, result = self.__processNetKATExpr(netkatEncoding)
        endTime = perf_counter()
        self.__addExecStatsEntry(procType, endTime - startTime)

        module = term.symbol().getModule()
        return module.parseTerm(result)

    def __addExecStatsEntry(self, key: str, value: float) -> None:
        if key in self.execStats:
            self.execStats[key].append(value)
        else:
            self.execStats[key] = [value]

    def __processNetKATExpr(self, expr: str) -> Tuple[str, str]:
        if expr in self.cache:
            return CACHE_HIT, self.cache[expr]

        output, error = self.katchComm.execute(expr)
        if error is not None:
            print(f"An error occured when running KATch:\n{error}")
            raise KATchError(error)

        self.cache[expr] = output
        return KATCH_CALL, output

    def reset(self) -> None:
        self.cache = {}
        self.execStats = {}
