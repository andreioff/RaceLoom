# mypy: disable-error-code="import-untyped,no-any-unimported,misc"

from time import perf_counter
from typing import List

import maude
from src.KATch_comm import KATchComm

KATCH_HOOK_MAUDE_NAME = "NetKATToNF"


class KATchError(Exception):
    pass


class KATchStats:
    def __init__(self) -> None:
        self.cacheHitTimes: List[float] = []
        self.katchExecTimes: List[float] = []


class KATchHook(maude.Hook):  # type: ignore
    def __init__(self, katchComm: KATchComm) -> None:
        super().__init__()
        self.katchComm = katchComm
        self.cache: dict[str, str] = {}
        self.execStats: KATchStats = KATchStats()

    def run(self, term: maude.Term, data: maude.HookData) -> maude.Term:
        # Reduce arguments first
        for arg in term.arguments():
            arg.reduce()

        # assumes the first arg is the netkat encoding to be used
        netkatEncoding = str(term.arguments().argument())

        # process the netkat expression
        result = self.__processNetKATExpr(netkatEncoding)

        module = term.symbol().getModule()
        return module.parseTerm(result)

    def __processNetKATExpr(self, expr: str) -> str:
        startTime = perf_counter()
        if expr in self.cache:
            self.execStats.cacheHitTimes.append(perf_counter() - startTime)
            return self.cache[expr]

        output, error = self.katchComm.execute(expr)
        if error is not None:
            print(f"An error occured when running KATch:\n{error}")
            raise KATchError(error)

        self.execStats.katchExecTimes.append(perf_counter() - startTime)
        self.cache[expr] = output
        return output

    def reset(self) -> None:
        self.cache = {}
        self.execStats = KATchStats()
