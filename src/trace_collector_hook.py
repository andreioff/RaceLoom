# mypy: disable-error-code="import-untyped,no-any-unimported,misc"

from os import linesep
from time import perf_counter
from typing import IO, List

import maude

TRACE_COLLECTOR_HOOK_MAUDE_NAME = "CollectTrace"


class TraceCollectorHook(maude.Hook):  # type: ignore
    def __init__(self, file: IO[str]) -> None:
        super().__init__()
        self.file = file
        self.calls = 0

    def run(self, term: maude.Term, data: maude.HookData) -> maude.Term:
        self.calls += 1
        # Reduce arguments first
        for arg in term.arguments():
            arg.reduce()

        # assumes the first arg is the extracted trace string
        self.file.write(str(term.arguments().argument()))
        self.file.write(linesep)

        # assuming that all traces are stored as strings in Maude,
        # return an empty Maude string for easier branching
        # after a trace is collected
        module = term.symbol().getModule()
        return module.parseTerm('""')

    def reset(self) -> None:
        self.calls = 0
